"""Celery tasks for OCR processing."""

import os
import re
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from celery import current_task
from .celery_app import celery_app
from .database import get_db_session
from .models import OCRJob, JobStatus

@celery_app.task(bind=True, name="web_app.tasks.ocr_task")
def ocr_task(self, job_id: str, file_path: str, output_format: str = "markdown"):
    """
    Process OCR task using docker-compose.
    
    Args:
        job_id: Unique job identifier
        file_path: Path to the input PDF file
        output_format: Output format (markdown or json)
    """
    
    # Compose a worker identifier (ensure it fits DB column size: String(50))
    worker_id_full = f"{self.request.hostname}-{self.request.id}"
    worker_id = worker_id_full[:50]

    try:
        # Update job status to processing
        with get_db_session() as db:
            job = db.query(OCRJob).filter(OCRJob.job_id == job_id).first()
            if not job:
                raise Exception(f"Job {job_id} not found in database")

            job.mark_started(worker_id)
            db.commit()
        # Ensure input file exists
        input_path = Path(file_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
        
        # Set up workspace directory
        workspace_dir = Path("data/workspace")
        workspace_dir.mkdir(exist_ok=True)
        
        # Copy file to data directory for docker-compose access
        data_dir = Path("data")
        pdf_filename = input_path.name.replace(f"{job_id}_", "")  # Remove job ID prefix
        data_file_path = data_dir / pdf_filename
        
        # Copy file to data directory
        import shutil
        shutil.copy2(input_path, data_file_path)
        
        # Build command to run pipeline inside the GPU-enabled 'olmocr' container.
        # Use docker exec against the named container to avoid compose context issues.
        cmd = [
            "docker", "exec", "-i",
            "-w", "/app/data",
            "olmocr",
            "python", "-m", "olmocr.pipeline",
            "workspace",
            f"--{output_format}",
            "--pdfs", pdf_filename
        ]
        
        # Update job with processing status
        with get_db_session() as db:
            job = db.query(OCRJob).filter(OCRJob.job_id == job_id).first()
            job.update_progress(5.0)  # Starting progress
            db.commit()
        
        # Execute OCR processing with progress tracking
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=Path.cwd()  # Ensure we're in the correct directory
        )
        
        current_file = pdf_filename
        processed_pages = 0
        total_pages = 0
        
        # Process output line by line for progress tracking
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                
                # Parse progress information
                progress_info = parse_ocr_log(line)
                
                # Update database with progress
                if progress_info:
                    with get_db_session() as db:
                        job = db.query(OCRJob).filter(OCRJob.job_id == job_id).first()
                        
                        if 'current_file' in progress_info:
                            current_file = progress_info['current_file']
                        
                        if 'page_progress' in progress_info:
                            job.update_progress(
                                progress_info['page_progress'],
                                progress_info.get('pages_completed', processed_pages),
                                progress_info.get('pages_total', total_pages)
                            )
                            processed_pages = progress_info.get('pages_completed', processed_pages)
                            total_pages = progress_info.get('pages_total', total_pages)
                        
                        # Update task state for Celery monitoring
                        current_task.update_state(
                            state='PROGRESS',
                            meta={
                                'current_file': current_file,
                                'processed_pages': processed_pages,
                                'total_pages': total_pages,
                                'progress': job.progress
                            }
                        )
                        
                        db.commit()
        
        # Wait for process completion
        return_code = process.wait()
        
        if return_code != 0:
            raise Exception(f"OCR process failed with exit code {return_code}")
        
        # Find and verify result file
        result_path = find_result_file(workspace_dir, pdf_filename, output_format)
        if not result_path:
            raise Exception("Result file not found after processing")
        
    # Update job as completed
        with get_db_session() as db:
            job = db.query(OCRJob).filter(OCRJob.job_id == job_id).first()
            job.mark_completed(str(result_path))
            db.commit()
        
        # Clean up temporary files
        try:
            data_file_path.unlink()  # Remove copied file
            input_path.unlink()      # Remove uploaded file
        except Exception as e:
            print(f"Warning: Failed to clean up files: {e}")
        
        return {
            'job_id': job_id,
            'status': 'completed',
            'result_path': str(result_path),
            'processed_pages': processed_pages,
            'total_pages': total_pages
        }
        
    except Exception as e:
        # Mark job as failed
        with get_db_session() as db:
            job = db.query(OCRJob).filter(OCRJob.job_id == job_id).first()
            if job:
                job.mark_failed(str(e))
                db.commit()
        
        # Clean up files on error
        try:
            if 'data_file_path' in locals() and data_file_path.exists():
                data_file_path.unlink()
            if 'input_path' in locals() and input_path.exists():
                input_path.unlink()
        except Exception:
            pass
        
        raise Exception(f"OCR task failed: {str(e)}")

def parse_ocr_log(line: str) -> Dict[str, Any]:
    """Parse olmocr pipeline log lines for progress information."""
    progress_info = {}
    
    # File processing start
    if "processing" in line and ".pdf" in line:
        filename_match = re.search(r'([^/]+\.pdf)', line)
        if filename_match:
            progress_info['current_file'] = filename_match.group(1)
    
    # Page progress: "INFO:olmocr.pipeline:Finished page 5/20 of document.pdf"
    page_match = re.search(r'Finished page (\d+)/(\d+)', line)
    if page_match:
        completed, total = map(int, page_match.groups())
        progress_info['pages_completed'] = completed
        progress_info['pages_total'] = total
        progress_info['page_progress'] = min(95.0, (completed / total) * 90)  # Cap at 95% until completion
    
    # Document completion
    if "finished work item" in line or "completed successfully" in line:
        progress_info['document_completed'] = True
        progress_info['page_progress'] = 100.0
    
    return progress_info

def find_result_file(workspace_dir: Path, filename: str, output_format: str) -> Path:
    """Find the result file after OCR processing."""
    base_name = filename.rsplit('.', 1)[0]  # Remove .pdf extension
    
    if output_format == "markdown":
        result_dir = workspace_dir / "markdown"
        result_file = result_dir / f"{base_name}.md"
    else:  # json
        result_dir = workspace_dir / "results"  
        result_file = result_dir / f"{base_name}.jsonl"
    
    if result_file.exists():
        return result_file
    
    # Fallback: search for any matching file
    if result_dir.exists():
        for file in result_dir.glob(f"*{base_name}*"):
            return file
    
    return None