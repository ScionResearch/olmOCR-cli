"""Database models for OCR job management."""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum
from datetime import datetime, timezone

Base = declarative_base()

class JobStatus(enum.Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class OCRJob(Base):
    """OCR job model for tracking processing tasks."""
    
    __tablename__ = "ocr_jobs"
    
    # Primary key
    job_id = Column(String(36), primary_key=True)
    
    # Job metadata
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer)  # in bytes
    file_path = Column(String(512))  # S3 path or local path
    output_format = Column(String(20), default="markdown")
    
    # Status tracking
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    progress = Column(Float, default=0.0)  # 0.0 to 100.0
    current_page = Column(Integer, default=0)
    total_pages = Column(Integer, default=0)
    
    # Result information
    result_path = Column(String(512))  # Path to output file
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Processing details
    worker_id = Column(String(50))  # Which worker processed this job
    processing_time = Column(Float)  # in seconds
    
    def to_dict(self) -> dict:
        """Convert job to dictionary for API responses."""
        return {
            'job_id': self.job_id,
            'filename': self.filename,
            'file_size': self.file_size,
            'output_format': self.output_format,
            'status': self.status.value,
            'progress': self.progress,
            'current_page': self.current_page,
            'total_pages': self.total_pages,
            'result_path': self.result_path,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'processing_time': self.processing_time
        }
    
    def update_progress(self, progress: float, current_page: int = None, total_pages: int = None):
        """Update job progress."""
        self.progress = min(100.0, max(0.0, progress))
        if current_page is not None:
            self.current_page = current_page
        if total_pages is not None:
            self.total_pages = total_pages
    
    def mark_started(self, worker_id: str = None):
        """Mark job as started."""
        self.status = JobStatus.PROCESSING
        # Use timezone-aware UTC for consistency
        self.started_at = datetime.now(timezone.utc)
        if worker_id:
            self.worker_id = worker_id
    
    def mark_completed(self, result_path: str = None):
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.progress = 100.0
        if result_path:
            self.result_path = result_path
        if self.started_at:
            self.processing_time = (self.completed_at - self.started_at).total_seconds()
    
    def mark_failed(self, error_message: str):
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error_message
        if self.started_at:
            self.processing_time = (self.completed_at - self.started_at).total_seconds()