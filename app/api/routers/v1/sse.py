# app.py
import uuid
from collections import deque
from typing import AsyncGenerator, Optional, List, Deque

from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.responses import StreamingResponse
import json
import asyncio


from pydantic import BaseModel
from starlette.requests import Request

from app.utils.sse import preprocess_text, format_sse_chunk

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "mock-llm"
    messages: List[Message]
    stream: Optional[bool] = False

AIGUARD_BUFFER_TOKENS = 10
AIGUARD_CHUNK_CHARS = 3
AIGUARD_DELAY = 0.08
AIGUARD_WINDOW_CHARS = 128
AIGUARD_ACTION = 'mask'

async def stream_tokens(text: str) -> AsyncGenerator[str, None]:
    for i in range(0, len(text), AIGUARD_CHUNK_CHARS):
        yield text[i:i + AIGUARD_CHUNK_CHARS]
        await asyncio.sleep(AIGUARD_DELAY)



async def generate_response(messages: list, stream: bool) -> AsyncGenerator[str, None]:
    # Фиксированный текст для демо (в дальнейшем будем выбирать из fixtures/)
    demo_text = ("Это    демонстрационный\u200B текст ответа              от мок-LLM.                  \uFEFFОн будет разбит на чанки.   ")

    if not stream:
        # Для не потокового режима
        full_text = ""
        async for chunk in stream_tokens(demo_text):
            # Обрабатываем каждый чанк
            processed_chunk = preprocess_text(chunk)
            full_text += processed_chunk

        # Финальная обработка полного текста
        full_text = preprocess_text(full_text)

        response_data = {
            "id": str(uuid.uuid4()),
            "object": "chat.completion",
            "choices": [{
                "message": {"content": full_text},
                "index": 0,
                "finish_reason": "stop"
            }]
        }
        yield json.dumps(response_data)
        return


    token_buffer = []  # накапливаем сырые токены/чанки
    sliding_window = ""  # строка последних X символов для регулярок
    prev_ended_with_space = False  # чтобы убирать дубли пробелов на стыке пачек

    async for chunk in stream_tokens(demo_text):
        token_buffer.append(chunk)

        # Когда накопили больше Y токенов — отдаем все, кроме последних Y
        while len(token_buffer) > AIGUARD_BUFFER_TOKENS:
            send_tokens = token_buffer[:-AIGUARD_BUFFER_TOKENS]
            token_buffer = token_buffer[-AIGUARD_BUFFER_TOKENS:]

            # Склеиваем и нормализуем пачку
            send_text = preprocess_text("".join(send_tokens))

            # Убираем ДУБЛИ пробелов на стыке с предыдущей отправленной пачкой
            if prev_ended_with_space and send_text.startswith(' '):
                send_text = send_text.lstrip()  # срежем ведущие пробелы у новой пачки

            # Обновляем окно и отдаем
            if send_text:
                sliding_window = (sliding_window + send_text)[-AIGUARD_WINDOW_CHARS:]
                # тут могла бы быть логика фильтра по sliding_window
                yield format_sse_chunk(send_text)
                prev_ended_with_space = send_text[-1].isspace()
            # если send_text пустая (вся «очистилась») — просто продолжаем

    # Финальный слив буфера
    if token_buffer:
        send_text = preprocess_text("".join(token_buffer))
        if prev_ended_with_space and send_text.startswith(' '):
            send_text = send_text.lstrip()
        if send_text:
            yield format_sse_chunk(send_text)

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

        # Для не потокового режима
        response_content = await anext(generator)
        return json.loads(response_content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))