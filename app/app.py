import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("app.app:app",port=8000, app_dir='app')