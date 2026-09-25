from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi_pagination import add_pagination
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.config.db.session import close_db, close_vectordb, init_db, init_vectordb
from src.config.hashers import hasher
from src.config.middlewares import MIDDLEWARES
from src.config.settings import settings
from src.knowledge_base.api.v1.routes import router as knowledge_base_router
from src.nlp.api.v1.routes import router as nlp_router
from src.nlp.services.controllers import EmbeddingController, VectorDBController
from src.projects.api.v1.routes import router as project_router
from src.users.api.v1.routes import router as user_router
from src.utils.llm.embedding.factory import EmbeddingLLMProviderFactory


@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialize db
    db_session = await init_db()
    # initialize vectordb provider to app
    vectordb_session = await init_vectordb()
    vectordb = VectorDBController(vectordb_session)
    # initialize embedding provider to app
    embedding_model_id = settings.DEFAULT_EMBEDDING_MODEL_ID
    embedding_backend = settings.EMBEDDING_BACKEND(embedding_model_id)
    embedding_api_key = settings.EMBEDDING_API_KEY(embedding_backend)
    embedding_client = EmbeddingLLMProviderFactory(embedding_backend).create(
        {
            "api_key": embedding_api_key,
            "embedding_model_id": embedding_model_id,
            "embedding_size": settings.EMBEDDING_SIZE,
            "default_input_max_characters": settings.DAFAULT_INPUT_MAX_CHARACTERS,
        }
    )
    embedder = EmbeddingController(embedding_client)
    # assign provider to fastapi app
    app.db_session = db_session
    app.embedder = embedder
    app.vectordb = vectordb

    yield

    await close_db()
    await close_vectordb()


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
    app.include_router(nlp_router)
    add_pagination(app)
    return app


app = create_app()
