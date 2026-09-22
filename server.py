from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi_pagination import add_pagination
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.config.db.session import close_db, init_db
from src.config.hashers import hasher
from src.config.middlewares import MIDDLEWARES
from src.config.settings import settings
from src.knowledge_base.api.v1.routes import router as knowledge_base_router
from src.projects.api.v1.routes import router as project_router
from src.users.api.v1.routes import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

    app.state.limiter = settings.LIMITER
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    for middleware in MIDDLEWARES:
        app.add_middleware(middleware["middleware"], **middleware["options"])

    app.state.hashing = hasher

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/health", tags=["Health Check"], summary="Health Check Endpoint", response_model=dict[str, str])
    async def health() -> dict[str, str]:
        return {"message": "health check ok"}

    app.include_router(user_router)
    app.include_router(project_router)
    app.include_router(knowledge_base_router)
    add_pagination(app)
    return app


app = create_app()
