import uvicorn
from fastapi import FastAPI

from app.config import load_config
from app.api.routers import api_router

config = load_config()

app = FastAPI(
    version="1.0.0",
    contact={
        "name": "Rubick",
        "email": "m.rubick@icloud.com1",
    }
)

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("app.app:app", reload=True,port=8002)