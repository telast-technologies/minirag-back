from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi_pagination import add_pagination
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.config.db.session import close_db, close_vectordb, init_db
from src.config.hashers import hasher
from src.config.middlewares import MIDDLEWARES
from src.config.settings import settings
from src.knowledge_base.api.v1.routes import router as knowledge_base_router
from src.nlp.api.v1.routes import router as nlp_router
from src.nlp.factory import NLPFactory
from src.projects.api.v1.routes import router as project_router
from src.users.api.v1.routes import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialize db
    db_session = await init_db()
    # initialize nlp controller
    nlp_controller = await NLPFactory.get_controller()
    # assign provider to fastapi app
    app.state.db_session = db_session
    app.state.nlp_controller = nlp_controller
    app.state.hashing = hasher

    yield

    await close_db()
    await close_vectordb()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

    app.state.limiter = settings.LIMITER
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    for middleware in MIDDLEWARES:
        app.add_middleware(middleware["middleware"], **middleware["options"])

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/health", tags=["Health Check"], summary="Health Check Endpoint", response_model=dict[str, str])
    async def health() -> dict[str, str]:
        return {"message": "health check ok"}

    app.include_router(user_router)
    app.include_router(project_router)
    app.include_router(knowledge_base_router)
    app.include_router(nlp_router)
    add_pagination(app)
    return app


app = create_app()
