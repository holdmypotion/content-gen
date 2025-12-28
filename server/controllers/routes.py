import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from controllers.generate import initiate_generation, get_task_status

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# Request/Response models
class GenerateRequest(BaseModel):
    reference_keywords: str
    reference_posts: Optional[list] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


class GenerateResponse(BaseModel):
    task_id: str
    message: str
    status: str


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Initiate content generation workflow."""
    return await initiate_generation(request.reference_keywords, request.reference_posts)


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def task_status(task_id: str):
    """Get the status of a generation task."""
    return await get_task_status(task_id)
