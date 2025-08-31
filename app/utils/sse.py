import asyncio
import json
import re
import uuid
from typing import Optional

import unicodedata


async def stream_tokens(text: str, chunk=3, delay=0.08):
    for i in range(0, len(text), chunk):
        yield text[i:i+chunk]
        await asyncio.sleep(delay)


def preprocess_text(text: str) -> str:
    if not text:
        return text
    text = unicodedata.normalize('NFKC', text)
    text = text.lower()
    text = re.sub(r'[\u200B-\u200F\uFEFF]', '', text)
    text = re.sub(r'\s+', ' ', text)

    return text


def format_sse_chunk(content: str, finish_reason: Optional[str] = None) -> str:
    """Форматирование сообщения в SSE-формат"""
    chunk_data = {
        "id": str(uuid.uuid4()),
        "object": "chat.completion.chunk",
        "choices": [{
            "delta": {"content": content} if content else {},
            "index": 0,
            "finish_reason": finish_reason
        }]
    }
    return f"data: {json.dumps(chunk_data)}\n\n"