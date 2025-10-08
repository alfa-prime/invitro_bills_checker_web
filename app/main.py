from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core import init_gateway_client, shutdown_gateway_client, global_exception_handler
from app.route import health_router
from app.route import upload_router

tags_metadata = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_gateway_client(app)
    yield
    await shutdown_gateway_client(app)


app = FastAPI(
    tags=tags_metadata,
    title="Шаблон приложения для работы со шлюзом ЕВМИАС API",
    lifespan=lifespan
)

app.add_exception_handler(Exception, global_exception_handler)

app.add_middleware(
    CORSMiddleware,  # noqa
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(upload_router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_root():
    return "static/index.html"
