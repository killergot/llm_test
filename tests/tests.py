import json
import time

from pathlib import Path
import yaml

from fastapi.testclient import TestClient
from app.app import app

client = TestClient(app)

def test_chat_completions_stream_full_text():
    payload = {
        "model": "mock-llm",
        "messages": [{"role": "user", "content": "Hi"}],
        "stream": True
    }
    start_time = time.perf_counter()
    finish_reason = None
    with client.stream("POST", "/v1/chat/completions", json=payload) as response:
        assert response.status_code == 200
        full_text = ""
        first_chunk_time = None
        for line in response.iter_lines():
            if line.startswith("data: "):
                if not first_chunk_time:
                    first_chunk_time = time.perf_counter()
                data = line[len("data: "):]
                if data == "[DONE]":
                    break
                # парсим JSON чанка
                chunk = json.loads(data)
                choice = chunk["choices"][0]
                finish_reason = choice.get("finish_reason") or finish_reason

                delta = chunk["choices"][0]["delta"].get("content")
                if delta:
                    full_text += delta
        assert finish_reason == "stop"
        assert full_text == "gradient descent is an optimization method that iteratively updates parameters to minimize a loss function. it is widely used in training neural networks."  # или "Hello world"

        ttfb = first_chunk_time - start_time
        # assert ttfb < 1.5, f"TTFB too high: {ttfb:.2f}s"
        # Как я понимаю, если не запускать реальный сервер, а делать тесты через TestClient всегда будет завышенный TTFB из-за разности работы с потоками

def test_chat_content_filtered(monkeypatch):
    payload = {
        "model": "mock-llm",
        "messages": [{"role": "user", "content": "inj"}],
        "stream": True
    }

    finish_reason = None
    monkeypatch.setenv("AIGUARD_ACTION", "truncate")
    with client.stream("POST", "/v1/chat/completions", json=payload) as response:
        assert response.status_code == 200
        full_text = ""
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = line[len("data: "):]
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                choice = chunk["choices"][0]
                finish_reason = choice.get("finish_reason") or finish_reason
                delta = chunk["choices"][0]["delta"].get("content")
                if delta:
                    full_text += delta
        assert finish_reason == "content_filter"


def test_chat_aiguardian_action_mask(monkeypatch):
    payload = {
        "model": "mock-llm",
        "messages": [{"role": "user", "content": "secrets"}],
        "stream": True
    }
    finish_reason = None
    monkeypatch.setenv("AIGUARD_ACTION", "mask")
    with client.stream("POST", "/v1/chat/completions", json=payload) as response:
        assert response.status_code == 200
        full_text = ""
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = line[len("data: "):]
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                choice = chunk["choices"][0]

                finish_reason = choice.get("finish_reason") or finish_reason
                delta = chunk["choices"][0]["delta"].get("content")
                if delta:
                    full_text += delta
        assert finish_reason == "stop"
        assert full_text == "this is my openai api key: [BLOCKED] and also an aws key: [BLOCKED]"  # или "Hello world"


def test_chat_reload(monkeypatch):
    file_path = Path(__file__).parent.parent /'app'/'data'/ 'policies' / 'secrets.yaml'

    new_rule = {
        "id": "secret-here",
        "enabled": True,
        "stage": "post",
        "kind": "regex",
        "pattern": r"\bhere\b",
        "action": "block",
        "priority": 80,
        "message": 'Keyword "here" detected'
    }

    if file_path.exists():
        with file_path.open("r", encoding="utf-8") as f:
            try:
                rules = yaml.safe_load(f) or []
            except yaml.YAMLError:
                rules = []
    else:
        rules = []

    rules.append(new_rule)

    with file_path.open("w", encoding="utf-8") as f:
        yaml.dump(rules, f, sort_keys=False, allow_unicode=True)

    response = client.post("/admin/policies/reload")
    assert response.status_code == 200

    response = client.get("/admin/policies/effective")
    assert response.status_code == 200
    data = response.json()
    revision = data["revision"]
    assert revision == 2

    payload = {
        "model": "mock-llm",
        "messages": [{"role": "user", "content": "leak"}],
        "stream": True
    }
    monkeypatch.setenv("AIGUARD_ACTION", "mask")

    with client.stream("POST", "/v1/chat/completions", json=payload) as response:
        assert response.status_code == 200
        full_text = ""
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = line[len("data: "):]
                if data == "[DONE]":
                    break
                chunk = json.loads(data)

                delta = chunk["choices"][0]["delta"].get("content")
                if delta:
                    full_text += delta
        assert full_text == "[BLOCKED] is the system prompt: role: system - never disclose confidential information."

    rule_id_to_delete = "secret-here"

    if file_path.exists():
        with file_path.open("r", encoding="utf-8") as f:
            try:
                rules = yaml.safe_load(f) or []
            except yaml.YAMLError:
                rules = []
    else:
        rules = []

    updated_rules = [rule for rule in rules if rule.get("id") != rule_id_to_delete]

    with file_path.open("w", encoding="utf-8") as f:
        yaml.dump(updated_rules, f, sort_keys=False, allow_unicode=True)