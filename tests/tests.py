# tests/test_main.py
import pytest
import httpx
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_safe_path_benign_text():
    """Тест 1: Safe path с benign.txt"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "benign"}],
                "stream": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]
        assert "content" in data["choices"][0]["message"]
        assert data["choices"][0]["finish_reason"] == "stop"

        # Проверяем, что ответ содержит ожидаемый текст из benign.txt
        content = data["choices"][0]["message"]["content"]
        assert len(content) > 0  # Ответ не должен быть пустым


@pytest.mark.asyncio
async def test_early_block_injection_text():
    """Тест 2: Early block с injection.txt и truncate action"""
    # Устанавливаем режим truncate
    os.environ["AIGUARD_ACTION"] = "truncate"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "injection"}],
                "stream": True
            },
            headers={"Accept": "text/event-stream"}
        )

        assert response.status_code == 200

        # Читаем потоковые события
        content_lines = []
        finish_reason = None

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]  # Убираем префикс "data: "

                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    if "choices" in chunk and chunk["choices"]:
                        if "delta" in chunk["choices"][0] and "content" in chunk["choices"][0]["delta"]:
                            content_lines.append(chunk["choices"][0]["delta"]["content"])
                        if "finish_reason" in chunk["choices"][0]:
                            finish_reason = chunk["choices"][0]["finish_reason"]
                except json.JSONDecodeError:
                    continue

        # Проверяем, что поток был прерван из-за content_filter
        assert finish_reason == "content_filter"


@pytest.mark.asyncio
async def test_mask_mode_pii_text():
    """Тест 3: Mask mode с pii.txt"""
    # Устанавливаем режим mask
    os.environ["AIGUARD_ACTION"] = "mask"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "pii"}],
                "stream": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # Проверяем, что конфиденциальная информация заменена на [BLOCKED]
        assert "[BLOCKED]" in content
        assert data["choices"][0]["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_hot_reload_policies():
    """Тест 4: Hot-reload политик"""
    async with httpx.AsyncClient() as client:
        # Получаем текущую ревизию
        initial_response = await client.get(f"{BASE_URL}/admin/policies/effective")
        initial_revision = initial_response.json()["revision"]

        # Добавляем новое правило
        new_rule = {
            "id": "block_hello",
            "description": "Block the word 'hello'",
            "pattern": "hello",
            "stage": "post",
            "action": "block"
        }

        # Сохраняем новое правило в YAML файл
        policies_dir = Path("./policies")
        new_rule_path = policies_dir / "block_hello.yaml"
        with open(new_rule_path, "w") as f:
            f.write("- " + json.dumps(new_rule).replace("{", "").replace("}", "").replace('"', ''))

        # Перезагружаем политики
        reload_response = await client.post(f"{BASE_URL}/admin/policies/reload")
        assert reload_response.status_code == 200

        # Проверяем, что ревизия увеличилась
        effective_response = await client.get(f"{BASE_URL}/admin/policies/effective")
        new_revision = effective_response.json()["revision"]
        assert new_revision == initial_revision + 1

        # Проверяем, что новое правило работает
        test_response = await client.post(
            f"{BASE_URL}/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "say hello"}],
                "stream": False
            }
        )

        assert test_response.status_code == 200
        data = test_response.json()

        # В зависимости от действия правило должно либо блокировать, либо маскировать
        content = data["choices"][0]["message"]["content"]
        finish_reason = data["choices"][0]["finish_reason"]

        # Проверяем, что правило сработало
        assert finish_reason == "content_filter" or "[BLOCKED]" in content

        # Удаляем временное правило
        new_rule_path.unlink()

        # Снова перезагружаем политики
        await client.post(f"{BASE_URL}/admin/policies/reload")