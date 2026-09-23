from fastapi import APIRouter, Request, Response

from src.config.loggers import Logger
from src.config.permissions import CurrentUserDep
from src.config.settings import settings

logger = Logger(name=__name__)
router = APIRouter(prefix="/api/v1/nlp", tags=["nlp"])


@router.get("/get_generation_models", response_model=list[str])
@settings.LIMITER.limit("50/minute")
async def get_generation_models(
    request: Request,
    response: Response,
    user: CurrentUserDep,
):
    return settings.GENERATION_MODEL_IDS
