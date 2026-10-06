"""Status of the trained behavioral model (item 2). Requires login."""
from fastapi import APIRouter

from app.detection.behavioral_graph import behavioral_model

router = APIRouter(prefix="/api/behavioral-model", tags=["behavioral"])


@router.get("")
async def get_behavioral_model():
    return behavioral_model.model.describe()