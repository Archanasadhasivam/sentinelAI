from fastapi import APIRouter

from app.config import get_settings
from app.detection.fixtures.seed_payloads import ALL_FIXTURES
from app.groq_client import groq_client

router = APIRouter(prefix="/api", tags=["settings"])
settings = get_settings()


@router.get("/settings/groq-status")
async def groq_status():
    return {
        "configured": groq_client.enabled,
        "degraded": groq_client.degraded,
        "models": {
            "reasoning": settings.groq_reasoning_model,
            "fast": settings.groq_fast_model,
            "safety": settings.groq_safety_model,
        },
    }


@router.get("/fixtures")
async def list_fixtures():
    """Backs the /playground AttackPresetMenu (build spec §5.3/§8)."""
    return {"fixtures": ALL_FIXTURES}
