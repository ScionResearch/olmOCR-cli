"""Celery configuration and app initialization."""

import os
from celery import Celery

# Redis configuration from environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Create Celery app
celery_app = Celery(
    "ocr_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["web_app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "web_app.tasks.ocr_task": {"queue": "ocr_queue"}
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # Process one task at a time (for GPU resources)
    task_acks_late=True,
    worker_hijack_root_logger=False,
    
    # Task configuration
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result backend configuration
    result_expires=3600,  # Results expire after 1 hour
    
    # Task time limits (adjust based on your typical processing times)
    task_soft_time_limit=1800,  # 30 minutes soft limit
    task_time_limit=3600,       # 1 hour hard limit
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)