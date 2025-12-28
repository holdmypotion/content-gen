from celery import Celery
from config import settings

# Initialize Celery
app = Celery(
    'content_generator',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Register tasks
from tasks.content import register_tasks  # noqa: F401, E402
register_tasks(app)