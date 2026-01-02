import logging
from fastapi import HTTPException
from celery.result import AsyncResult

from config import settings
from celery_app import app as celery_app
from db import get_db

logger = logging.getLogger(__name__)


async def initiate_generation(request):
    """
    Initiate content generation workflow.
    """
    try:
        if not request.reference_keywords.strip():
            raise HTTPException(
                status_code=400,
                detail="reference_keywords cannot be empty"
            )

        provider_tasks = {
            "gemini": "tasks.generate_idea_gemini",
            "gpt": "tasks.generate_idea_gpt",
        }

        task_name = provider_tasks.get(request.provider)
        if not task_name:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider specified: {request.provider}"
            )

        # Start the appropriate idea generation task
        idea_task = celery_app.send_task(
            task_name,
            args=[request.reference_keywords],
            kwargs={'reference_posts': request.reference_posts}
        )

        logger.info(f"Started {request.provider} idea generation task: {idea_task.id}")

        return {
            "task_id": idea_task.id,
            "message": f"Content generation started with {request.provider}",
            "status": "pending"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate generation: {str(e)}"
        )


async def get_task_status(task_id: str):
    """
    Get the status of a generation task.
    """
    try:
        result = AsyncResult(task_id, app=celery_app)

        if result.state == 'PENDING':
            return {
                    "task_id": task_id,
                    "status": "pending"
                    }

        elif result.state == 'PROGRESS':
            return {
                    "task_id": task_id,
                    "status": "in_progress",
                    "result": result.info
                    }

        elif result.state == 'SUCCESS':
            task_result = result.result

            # Handle error status in result
            if task_result.get('status') == 'error':
                return {
                        "task_id": task_id,
                        "status": "failed",
                        "error": task_result.get('error', 'Unknown error')
                        }

            return {
                    "task_id": task_id,
                    "status": "SUCCESS",
                    "result": task_result
                    }

        elif result.state == 'FAILURE':
            return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(result.info)
                    }

        else:
            return {
                    "task_id": task_id,
                    "status": result.state.lower()
                    }

    except Exception as e:
        logger.error(f"Error retrieving task status: {str(e)}")
        raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve task status: {str(e)}"
                )


async def initiate_post_regeneration(request):
    """
    Initiate post regeneration for an existing content entry.
    """
    try:
        db = get_db()
        content = db.get_content(request.content_id)
        
        if not content:
            raise HTTPException(
                status_code=404,
                detail=f"Content with ID {request.content_id} not found"
            )
        
        idea = content.get('idea')
        if not idea:
            raise HTTPException(
                status_code=400,
                detail="No idea found in content. Cannot regenerate post without an idea."
            )
        
        provider_tasks = {
            "gemini": "tasks.regenerate_post_gemini",
            "gpt": "tasks.regenerate_post_gpt",
        }

        task_name = provider_tasks.get(request.provider)
        if not task_name:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider specified: {request.provider}"
            )

        post_task = celery_app.send_task(
            task_name,
            args=[idea],
            kwargs={
                'reference_keywords': content.get('reference_keywords', ''),
                'reference_posts': content.get('reference_posts', []),
                'db_file': request.content_id
            }
        )

        logger.info(f"Started {request.provider} post regeneration task: {post_task.id}")

        return {
            "task_id": post_task.id,
            "message": f"Post regeneration started with {request.provider}",
            "status": "pending"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating post regeneration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate post regeneration: {str(e)}"
        )