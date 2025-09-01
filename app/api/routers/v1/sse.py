# app.py
import uuid
from pathlib import Path
from typing import AsyncGenerator, Optional, List

from environs import env, Env
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.responses import StreamingResponse
import json
import asyncio
import logging

logging.basicConfig(
    filename="llm.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
from pydantic import BaseModel

from app.config import load_config, Config
from app.utils.sse import preprocess_text, format_sse_chunk
from app.utils.policy import engine, PolicyViolation

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "mock-llm"
    messages: List[Message]
    stream: Optional[bool] = False

conf: Config = load_config()

AIGUARD_BUFFER_TOKENS = conf.aiguard.buffer_tokens
AIGUARD_CHUNK_CHARS = conf.aiguard.chunk_chars
AIGUARD_DELAY = conf.aiguard.ttfb_deadline_ms
AIGUARD_WINDOW_CHARS = conf.aiguard.window_chars
AIGUARD_ACTION = conf.aiguard.action

async def stream_tokens(text: str) -> AsyncGenerator[str, None]:
    for i in range(0, len(text), AIGUARD_CHUNK_CHARS):
        yield text[i:i + AIGUARD_CHUNK_CHARS]
        await asyncio.sleep(AIGUARD_DELAY)


async def generate_response(messages: list, stream: bool) -> AsyncGenerator[str, None]:
    conf = load_config()
    AIGUARD = conf.aiguard.action
    # Это сделано чисто для юнит тестов, чтоб можно было менять режим

    truncate = False if AIGUARD == 'mask' else True
    try:
        msg = engine.apply(messages[0].content, stage = 'pre',truncate=truncate)
    except PolicyViolation as e:
        yield format_sse_chunk("", finish_reason="content_filter")
        return

    print(msg)

    if msg.count('inj'):
        path = 'injection'
    elif msg.count('leak'):
        path = 'leak'
    elif msg.count('pii'):
        path = 'pii'
    elif msg.count('secrets'):
        path = 'secrets'
    else:
        path = 'benign'

    full_path: Path = (Path(__file__).parent.parent.parent.parent.parent
                       / 'fixtures' / (path+'.txt'))

    with open(full_path, "r", encoding="utf-8") as file:
        demo_text = file.read()

    if not stream:
        full_text = ""
        async for chunk in stream_tokens(demo_text):
            full_text += chunk

        full_text = preprocess_text(full_text)
        try:
            full_text = engine.apply(full_text, truncate=truncate)
        except PolicyViolation as e:
            yield format_sse_chunk("", finish_reason="content_filter")
            return

        yield format_sse_chunk(full_text, finish_reason="stop")
        return

    buffer_chunks = []
    total_chars = 0
    async for chunk in stream_tokens(demo_text):
        buffer_chunks.append(chunk)
        total_chars += len(chunk)

        while total_chars >= AIGUARD_WINDOW_CHARS or len(buffer_chunks) >= AIGUARD_BUFFER_TOKENS:
            full_text = ''.join(buffer_chunks)
            current_text = full_text[:AIGUARD_WINDOW_CHARS] if len(full_text) > AIGUARD_WINDOW_CHARS else full_text
            processed_chars = len(current_text)

            preprocessed = preprocess_text(current_text)
            try:
                filtered = engine.apply(preprocessed, truncate=truncate)
            except PolicyViolation as e:
                yield format_sse_chunk("", finish_reason="content_filter")
                return

            yield format_sse_chunk(filtered)

            total_chars -= processed_chars
            new_buffer = []
            remaining = processed_chars
            for c in buffer_chunks:
                if len(c) <= remaining:
                    remaining -= len(c)
                else:
                    new_buffer.append(c[remaining:])
                    remaining = 0
            buffer_chunks = new_buffer

    if buffer_chunks:
        full_text = ''.join(buffer_chunks)
        preprocessed = preprocess_text(full_text)
        try:
            filtered = engine.apply(preprocessed,truncate=truncate)
        except PolicyViolation as e:
            yield format_sse_chunk("", finish_reason="content_filter")
            return

        yield format_sse_chunk(filtered)

    yield format_sse_chunk("", finish_reason="stop")
    yield "data: [DONE]\n\n"


@router.post("/completions")
async def chat_completions(request: ChatCompletionRequest):

    try:
        generator = generate_response(
            messages=request.messages,
            stream=request.stream
        )

        if request.stream:
            return StreamingResponse(
                generator,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
            )

        response_content = await anext(generator)
        return json.loads(response_content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))