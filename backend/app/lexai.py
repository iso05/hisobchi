import json
import os
from threading import BoundedSemaphore
from typing import Annotated

import httpx
from fastapi import HTTPException
from gradio_client import Client
from pydantic import BaseModel, Field, StringConstraints


class ChatQuestion(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)]


class Source(BaseModel):
    id: str
    reference: str = ''
    text: str = ''


class ChatAnswer(BaseModel):
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    verified: bool = Field(strict=True)
    latency_ms: int = Field(ge=0)
    sources: list[Source]


_slots = BoundedSemaphore(4)


def ask(question: str) -> ChatAnswer:
    url = os.getenv('LEXAI_URL', '').strip().rstrip('/')
    if not url:
        raise HTTPException(503, 'LexAI is not configured.')
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, 'LexAI is busy.')
    client = None
    job = None
    try:
        client = Client(url, verbose=False, download_files=False, httpx_kwargs={'timeout': 20})
        job = client.submit(question=question, api_name='/ask_json')
        raw = job.result(timeout=75)
        return ChatAnswer.model_validate(json.loads(raw) if isinstance(raw, str) else raw)
    except (TimeoutError, httpx.TimeoutException) as exc:
        if job is not None:
            job.cancel()
        raise HTTPException(504, 'LexAI timed out.') from exc
    except Exception as exc:
        raise HTTPException(502, 'LexAI could not return an answer.') from exc
    finally:
        try:
            if client is not None:
                client.close()
        finally:
            _slots.release()
