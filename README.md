# Апи для обработки и фильтрации потока, передаваемого через llm с заглушкой
Этот код решает задачу **потоковой фильтрации текста с минимальной задержкой**_

## Как запустить
1. Через docker compose
- docker compose build
- docker compose up
2. Через minikube (kubernetis k8s)
- make up

## Простой способ протестировать поток
Открываем страницу test.html и пишем текст в поле ввода после запуска API

## Примеры curl запросов:

К основной ручке:
```
curl -X POST "http://localhost:8000/v1/chat/completions" \
-H "Content-Type: application/json" \
-d '{
  "model": "mock-llm",
  "messages": [
    {"role": "user", "content": "Привет!"}
  ],
  "stream": false
}'
```
К ручке перезагрузки:
```
curl -X POST "http://localhost:8000/admin/policies/reload"
```
К ручке информации:
```
curl -X GET "http://localhost:8000/admin/policies/effective"
```


Ключевые слова для смены текста выдаваемого заглушкой:
- inj
- leak
- pii
- secrets


## API Endpoints

### 1. Chat Completions
**URL:** `/v1/chat/completions`  
**Method:** `POST`  
**Описание:** _Выполнить запрос_
- content: Сообщение пользователя
- stream: Тип выдаваемого ответа, если true, то выдается в виде стрима

**Request Body (application/json):**
```json
{
  "model": "string (optional, default=mock-llm)",
  "messages": [
    {
      "role": "string",
      "content": "string"
    }
  ],
  "stream": "boolean (optional, default=false)"
}
````

**Responses:**

* `200`: Successful Response
* `422`: Validation Error

---

### 2. Reload Policies

**URL:** `/admin/policies/reload`
**Method:** `POST`
**Описание:** *Перезагружает правила*

**Responses:**

* `200`: Successful Response

---

### 3. Effective Policies

**URL:** `/admin/policies/effective`
**Method:** `GET`
**Описание:** *Получить информацию по правилам и количество перезагрузок правил, также последнее время загрузки правил*

**Responses:**

* `200`: Successful Response

---

### 4. Health

**URL:** `/health`
**Method:** `GET`


**Responses:**

* `200`: Successful Response