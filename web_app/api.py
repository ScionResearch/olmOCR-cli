"""FastAPI application for OCR job management."""

import os
import uuid
import mimetypes
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .database import get_db, create_tables
from .models import OCRJob, JobStatus
from .tasks import ocr_task
from .celery_app import celery_app

# Initialize FastAPI app
app = FastAPI(
    title="AI-Powered OCR API",
    description="REST API for managing OCR processing jobs with real-time progress tracking",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for serving results
app.mount("/static", StaticFiles(directory="data/workspace"), name="static")

# Pydantic models for API requests/responses
class JobCreate(BaseModel):
    filename: str
    output_format: str = "markdown"

class JobResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    progress: float
    current_page: int
    total_pages: int
    result_path: Optional[str]
    error_message: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    processing_time: Optional[float]

class JobList(BaseModel):
    jobs: List[JobResponse]
    total: int

# Startup event to create database tables
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    create_tables()
    # Ensure data directories exist
    Path("data").mkdir(exist_ok=True)
    Path("data/uploads").mkdir(exist_ok=True)
    Path("data/workspace").mkdir(exist_ok=True)

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI-Powered OCR API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "celery_active": celery_app.control.inspect().active() is not None
    }

@app.post("/jobs", response_model=JobResponse, tags=["Jobs"])
async def create_job(
    file: UploadFile = File(...),
    output_format: str = "markdown",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Create a new OCR job by uploading a PDF file."""
    
    # Validate file type
    if not file.content_type == "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_path = Path("data/uploads") / f"{job_id}_{file.filename}"
    
    try:
        with open(upload_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        file_size = len(content)
        
        # Create job record in database
        job = OCRJob(
            job_id=job_id,
            filename=file.filename,
            file_size=file_size,
            file_path=str(upload_path),
            output_format=output_format,
            status=JobStatus.QUEUED
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Queue the task in Celery
        ocr_task.delay(job_id, str(upload_path), output_format)
        
        return JobResponse(**job.to_dict())
        
    except Exception as e:
        # Clean up file if database operation fails
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

@app.get("/jobs", response_model=JobList, tags=["Jobs"])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List OCR jobs with optional filtering."""
    
    query = db.query(OCRJob)
    
    if status:
        try:
            status_enum = JobStatus(status)
            query = query.filter(OCRJob.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    total = query.count()
    jobs = query.offset(offset).limit(limit).all()
    
    return JobList(
        jobs=[JobResponse(**job.to_dict()) for job in jobs],
        total=total
    )

@app.get("/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get details of a specific OCR job."""
    
    job = db.query(OCRJob).filter(OCRJob.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(**job.to_dict())

@app.delete("/jobs/{job_id}", tags=["Jobs"])
async def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Cancel an OCR job."""
    
    job = db.query(OCRJob).filter(OCRJob.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    
    # Cancel the Celery task
    celery_app.control.revoke(job_id, terminate=True)
    
    # Update job status
    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Job cancelled successfully"}

@app.get("/jobs/{job_id}/download", tags=["Jobs"])
async def download_result(job_id: str, db: Session = Depends(get_db)):
    """Download the result file of a completed OCR job."""
    
    job = db.query(OCRJob).filter(OCRJob.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")
    
    if not job.result_path or not Path(job.result_path).exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    # Determine appropriate filename and media type
    result_path = Path(job.result_path)
    filename = f"{job.filename.rsplit('.', 1)[0]}.{result_path.suffix[1:]}"
    media_type = mimetypes.guess_type(result_path)[0] or "application/octet-stream"
    
    return FileResponse(
        result_path,
        filename=filename,
        media_type=media_type
    )

@app.get("/stats", tags=["Stats"])
async def get_stats(db: Session = Depends(get_db)):
    """Get OCR processing statistics."""
    
    total_jobs = db.query(OCRJob).count()
    completed_jobs = db.query(OCRJob).filter(OCRJob.status == JobStatus.COMPLETED).count()
    failed_jobs = db.query(OCRJob).filter(OCRJob.status == JobStatus.FAILED).count()
    processing_jobs = db.query(OCRJob).filter(OCRJob.status == JobStatus.PROCESSING).count()
    queued_jobs = db.query(OCRJob).filter(OCRJob.status == JobStatus.QUEUED).count()
    
    return {
        "total_jobs": total_jobs,
        "completed": completed_jobs,
        "failed": failed_jobs,
        "processing": processing_jobs,
        "queued": queued_jobs,
        "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)