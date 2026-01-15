import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from pydantic import BaseModel, field_validator, ConfigDict, Field
from typing import Optional, List

from controllers.generate import initiate_generation, get_task_status, initiate_post_regeneration
from utils.scraper import process_keywords
from utils.auth import verify_token
from db import get_db

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# Dependency for getting user_id from token
def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Extract and verify user from authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user_id


# Request/Response models
class GenerateRequest(BaseModel):
    reference_keywords: str
    reference_posts: Optional[list] = None
    provider: Optional[str] = "gemini"


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


class GenerateResponse(BaseModel):
    task_id: str
    message: str
    status: str


class ContentResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        ser_json_schema={'by_alias': True}
    )
    
    id: str = Field(alias='_id')
    timestamp: str
    type: str
    provider: str
    reference_keywords: str
    idea: Optional[str] = None
    posts: Optional[List[str]] = None
    reference_posts: Optional[list] = None


class RegeneratePostRequest(BaseModel):
    content_id: str
    provider: Optional[str] = "gemini"


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest, user_id: str = Depends(get_current_user)):
    """Initiate content generation workflow."""
    # Process keywords: detect and scrape URLs if present
    processed_keywords = process_keywords(request.reference_keywords)
    request.reference_keywords = processed_keywords
    return await initiate_generation(request, user_id)



@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def task_status(task_id: str):
    """Get the status of a generation task."""
    return await get_task_status(task_id)


@router.get("/contents", response_model=List[ContentResponse])
async def get_contents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user)
):
    """Get all generated contents for the current user with pagination."""
    try:
        db = get_db()
        contents = db.get_all_contents(user_id=user_id, skip=skip, limit=limit)
        return contents
    except Exception as e:
        logger.error(f"Error fetching contents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch contents: {str(e)}"
        )


@router.get("/content/{content_id}", response_model=ContentResponse)
async def get_content(content_id: str, user_id: str = Depends(get_current_user)):
    """Get a specific content by ID."""
    try:
        db = get_db()
        content = db.get_content(content_id)
        if not content:
            raise HTTPException(
                status_code=404,
                detail=f"Content with ID {content_id} not found"
            )
        # Check if content belongs to user
        if content.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this content"
            )
        return content
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching content: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch content: {str(e)}"
        )


@router.put("/content/{content_id}")
async def update_content(content_id: str, data: dict, user_id: str = Depends(get_current_user)):
    """Update a content document."""
    try:
        db = get_db()
        content = db.get_content(content_id)
        if not content:
            raise HTTPException(
                status_code=404,
                detail=f"Content with ID {content_id} not found"
            )
        # Check if content belongs to user
        if content.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to modify this content"
            )
        success = db.update_content(content_id, data)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Content with ID {content_id} not found"
            )
        updated = db.get_content(content_id)
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating content: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update content: {str(e)}"
        )


@router.delete("/content/{content_id}")
async def delete_content(content_id: str, user_id: str = Depends(get_current_user)):
    """Delete a content document."""
    try:
        db = get_db()
        content = db.get_content(content_id)
        if not content:
            raise HTTPException(
                status_code=404,
                detail=f"Content with ID {content_id} not found"
            )
        # Check if content belongs to user
        if content.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to delete this content"
            )
        success = db.delete_content(content_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Content with ID {content_id} not found"
            )
        return {"message": "Content deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting content: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete content: {str(e)}"
        )


@router.post("/regenerate-post", response_model=GenerateResponse)
async def regenerate_post(request: RegeneratePostRequest, user_id: str = Depends(get_current_user)):
    """Regenerate post for an existing content entry."""
    # Verify user owns this content
    try:
        db = get_db()
        content = db.get_content(request.content_id)
        if not content:
            raise HTTPException(
                status_code=404,
                detail=f"Content with ID {request.content_id} not found"
            )
        if content.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to regenerate this content"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking content ownership: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify content ownership")
    
    return await initiate_post_regeneration(request)