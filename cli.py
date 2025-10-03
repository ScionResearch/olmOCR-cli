#!/usr/bin/env python3
"""
Interactive CLI for AI-Powered OCR Tool (OLMoCR)
A customizable command-line interface for managing OCR operations with Docker integration.
"""

import os
import sys
import json
import subprocess
import argparse
import re
import time
import select
import termios
import tty
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, MofNCompleteColumn
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from rich.table import Table
from rich.layout import Layout
from rich.align import Align
from rich.columns import Columns
import random

class OCRConfig:
    """Configuration manager for OCR CLI settings."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.default_config = {
            "data_directory": "./data",
            "workspace_directory": "./data/workspace",
            "docker_image": "alleninstituteforai/olmocr:latest",
            "output_format": "markdown",
            "gpu_enabled": True,
            "batch_size": 1,
            "parallel_workers": 1,
            "debug_mode": False,
            "auto_cleanup": True,
            "container_name": "olmocr",
            "ssl_cert_path": "/path/to/your/certificate.crt",
            "ssl_enabled": True,
            "show_logs": False
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**self.default_config, **config}
            except (json.JSONDecodeError, FileNotFoundError):
                print(f"Warning: Could not load config from {self.config_path}, using defaults")
        return self.default_config.copy()
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"Configuration saved to {self.config_path}")
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self.config = self.default_config.copy()

class OCRInterface:
    """Main CLI interface for OCR operations."""
    
    def __init__(self):
        self.config = OCRConfig()
        self.data_dir = Path(self.config.get("data_directory"))
        self.workspace_dir = Path(self.config.get("workspace_directory"))
        self.show_logs_mode = self.config.get("show_logs", False)
    
    def check_keypress(self) -> Optional[str]:
        """Check for keypress in non-blocking mode. Returns key or None."""
        if not sys.stdin.isatty():
            return None
        
        try:
            # Save current terminal settings
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            
            # Set terminal to non-blocking mode
            try:
                tty.cbreak(fd)
            except AttributeError:
                # tty.cbreak not available on this system
                return None
            
            # Check if input is available
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                key = sys.stdin.read(1)
                # Restore terminal settings
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                return key
            
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return None
        except (OSError, termios.error, AttributeError):
            return None
        
    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.data_dir.mkdir(exist_ok=True)
        self.workspace_dir.mkdir(exist_ok=True)
        print(f"Data directory: {self.data_dir.absolute()}")
        print(f"Workspace directory: {self.workspace_dir.absolute()}")
    
    def list_pdfs(self) -> List[Path]:
        """List all PDF files in data directory."""
        pdf_files = list(self.data_dir.glob("*.pdf"))
        return sorted(pdf_files)
    
    def check_docker(self) -> bool:
        """Check if Docker is available and running."""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def check_gpu_support(self) -> bool:
        """Check if NVIDIA GPU support is available."""
        try:
            result = subprocess.run(['nvidia-smi'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def pull_docker_image(self) -> bool:
        """Pull the latest OCR Docker image."""
        image = self.config.get("docker_image")
        print(f"Pulling Docker image: {image}")
        try:
            result = subprocess.run(['docker', 'pull', image], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("Docker image pulled successfully")
                return True
            else:
                print(f"Error pulling image: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def check_docker_compose(self) -> bool:
        """Check if docker-compose is available and docker-compose.yml exists."""
        try:
            # Check for Docker Compose V2 first (docker compose)
            result = subprocess.run(['docker', 'compose', 'version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Check if docker-compose.yml exists
                return Path("docker-compose.yml").exists()
            
            # Fallback to Docker Compose V1 (docker-compose)
            result = subprocess.run(['docker-compose', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Check if docker-compose.yml exists
                return Path("docker-compose.yml").exists()
            
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_docker_compose_cmd(self) -> List[str]:
        """Get the appropriate docker compose command."""
        try:
            # Try Docker Compose V2 first
            result = subprocess.run(['docker', 'compose', 'version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return ['docker', 'compose']
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Fallback to V1
        return ['docker-compose']

    def build_docker_command(self, pdfs: List[str], output_format: str = "markdown") -> List[str]:
        """Build Docker command for OCR processing."""
        # Prefer docker-compose if available (better for model caching)
        if self.check_docker_compose():
            compose_cmd = self.get_docker_compose_cmd()
            cmd = compose_cmd + [
                "exec", "-T", "olmocr",
                "python", "-m", "olmocr.pipeline", 
                str(self.workspace_dir)
            ]
            # Only add --markdown flag if markdown is selected (json is default)
            if output_format == "markdown":
                cmd.append("--markdown")
            cmd.extend(["--pdfs"] + pdfs)
            return cmd
        
        # Fallback to docker run (less efficient, downloads models each time)
        print("Warning: Using docker run - models will be downloaded each time. Consider using docker-compose for better performance.")
        
        gpu_flag = ["--gpus", "all"] if self.config.get("gpu_enabled") and self.check_gpu_support() else []
        
        # SSL certificate mounting and environment variables
        ssl_volume = []
        ssl_env = []
        if self.config.get("ssl_enabled"):
            cert_path = self.config.get("ssl_cert_path")
            if cert_path and Path(cert_path).exists():
                ssl_volume = ["-v", f"{cert_path}:/etc/ssl/certs/corporate_ca.crt:ro"]
                ssl_env = [
                    "-e", "REQUESTS_CA_BUNDLE=/etc/ssl/certs/corporate_ca.crt",
                    "-e", "SSL_CERT_FILE=/etc/ssl/certs/corporate_ca.crt", 
                    "-e", "HF_HUB_CERTIFICATE=/etc/ssl/certs/corporate_ca.crt",
                    "-e", "CURL_CA_BUNDLE=/etc/ssl/certs/corporate_ca.crt"
                ]
            elif self.config.get("debug_mode"):
                print(f"Warning: SSL certificate not found at {cert_path}")
        
        cmd = [
            "docker", "run", "--rm", "-it"
        ] + gpu_flag + [
            "-v", f"{self.data_dir.absolute()}:/app/data",
            "-w", "/app/data"
        ] + ssl_volume + ssl_env + [
            "--name", self.config.get("container_name"),
            self.config.get("docker_image"),
            "python", "-m", "olmocr.pipeline", 
            str(self.workspace_dir)
        ]
        # Only add --markdown flag if markdown is selected (json is default)
        if output_format == "markdown":
            cmd.append("--markdown")
        cmd.extend(["--pdfs"] + pdfs)
        
        return cmd
    
    def ensure_compose_container(self) -> bool:
        """Ensure docker-compose container is running."""
        if not self.check_docker_compose():
            return True  # Skip if not using compose
        
        try:
            # Check if container is running
            compose_cmd = self.get_docker_compose_cmd()
            result = subprocess.run(compose_cmd + ['ps', '-q', 'olmocr'], 
                                  capture_output=True, text=True)
            if not result.stdout.strip():
                print("Starting docker-compose container...")
                start_result = subprocess.run(compose_cmd + ['up', '-d'], 
                                            capture_output=True, text=True)
                if start_result.returncode != 0:
                    print(f"Failed to start container: {start_result.stderr}")
                    return False
                print("Container started successfully")
            return True
        except Exception as e:
            print(f"Error managing container: {e}")
            return False

    def parse_olmocr_log(self, line: str) -> Dict[str, Any]:
        """Parse olmocr pipeline log lines for progress information."""
        progress_info = {}
        
        # File processing start: "Worker 0 processing s3://..."
        if "processing" in line and ".pdf" in line:
            # Extract filename from path
            filename_match = re.search(r'([^/]+\.pdf)', line)
            if filename_match:
                progress_info['current_file'] = filename_match.group(1)
        
        # Page progress: "INFO:olmocr.pipeline:Finished page 5/20 of document.pdf"
        page_match = re.search(r'Finished page (\d+)/(\d+)', line)
        if page_match:
            completed, total = map(int, page_match.groups())
            progress_info['pages_completed'] = completed
            progress_info['pages_total'] = total
            progress_info['page_progress'] = (completed / total) * 100
        
        # Document completion: "Worker 0 finished work item"
        if "finished work item" in line or "completed successfully" in line:
            progress_info['document_completed'] = True
        
        # Error detection
        if "ERROR" in line or "Failed" in line:
            progress_info['error'] = line.strip()
        
        # Status updates
        if "Starting" in line and "processing" in line:
            progress_info['status'] = 'Starting processing'
        elif "Extracting text" in line:
            progress_info['status'] = 'Extracting text'
        elif "Converting to markdown" in line:
            progress_info['status'] = 'Converting to markdown'
        elif "Saving output" in line:
            progress_info['status'] = 'Saving output'
        
        return progress_info

    def get_motivational_message(self) -> str:
        """Get a random motivational message for completed documents."""
        messages = [
            "✨ Another one bites the dust!",
            "🎯 Nailed it!",
            "🚀 One small step for OCR...",
            "💎 Polished to perfection!",
            "🏆 Champion level processing!",
            "⚡ Lightning fast results!",
            "🎪 And the crowd goes wild!",
            "🌟 Pure excellence in motion!"
        ]
        return random.choice(messages)

    def create_status_dashboard(self, processed_files: int, total_files: int, current_file: str, 
                               processed_pages: int, total_pages: int, elapsed_time: float) -> Table:
        """Create a live status dashboard."""
        table = Table.grid(expand=True)
        table.add_column(justify="left", style="cyan", no_wrap=True)
        table.add_column(justify="center", style="magenta", no_wrap=True)  
        table.add_column(justify="right", style="green", no_wrap=True)
        
        # File progress
        files_emoji = "📁" if processed_files == 0 else "📂" if processed_files < total_files else "📋"
        files_status = f"{files_emoji} Files: {processed_files}/{total_files}"
        
        # Current document  
        doc_emoji = "📄" if current_file else "⏳"
        current_doc = f"{doc_emoji} {current_file[:20]}..." if len(current_file) > 20 else f"{doc_emoji} {current_file}"
        
        # Pages and timing
        pages_status = f"📃 Pages: {processed_pages}/{total_pages}" if total_pages > 0 else "📃 Pages: --"
        time_status = f"⏱️  Elapsed: {elapsed_time:.1f}s"
        
        table.add_row(files_status, current_doc, f"{pages_status}  {time_status}")
        return table

    def highlight_log_line(self, line: str, console: Console) -> None:
        """Apply color coding to log lines based on content."""
        line = line.strip()
        if not line:
            return
            
        if "ERROR" in line or "FAILED" in line.upper():
            console.print(f"[red]❌ {line}[/]")
        elif "WARNING" in line or "WARN" in line:
            console.print(f"[yellow]⚠️  {line}[/]")
        elif "SUCCESS" in line.upper() or "COMPLETED" in line.upper():
            console.print(f"[green]✅ {line}[/]")
        elif "INFO" in line:
            console.print(f"[dim cyan]{line}[/]")
        elif "DEBUG" in line:
            console.print(f"[dim]{line}[/]")
        else:
            console.print(f"[dim white]{line}[/]")

    def show_completion_celebration(self, console: Console, processed_files: int, total_time: float) -> None:
        """Show a celebration animation when all processing is complete."""
        # Celebration panel
        celebration_text = Text.assemble(
            ("🎉 ", "bold yellow"),
            ("MISSION ACCOMPLISHED!", "bold green"),
            (" 🎉\n", "bold yellow"),
            (f"Successfully processed {processed_files} file(s)\n", "green"),
            (f"Total time: {total_time:.1f} seconds", "cyan")
        )
        
        celebration_panel = Panel(
            Align.center(celebration_text),
            border_style="green",
            title="[bold green]🏆 SUCCESS 🏆[/]",
            title_align="center"
        )
        
        console.print("\n")
        console.print(celebration_panel)
        
        # ASCII confetti effect
        confetti = ["🎊", "🎉", "✨", "🌟", "💫", "⭐", "🎈", "🎆"]
        confetti_line = " ".join([random.choice(confetti) for _ in range(15)])
        console.print(f"\n[bold yellow]{confetti_line}[/]")
        console.print(f"[bold green]All files are ready in your workspace directory![/]")
        console.print(f"[bold yellow]{confetti_line}[/]\n")

    def process_pdfs_with_progress(self, pdf_files: List[str], output_format: str = "markdown") -> bool:
        """Process PDF files with toggle between progress visualization and logs."""
        if not pdf_files:
            print("No PDF files specified")
            return False
        
        console = Console()
        start_time = time.time()
        show_logs = self.show_logs_mode
        
        # Initial setup with spinner
        with console.status("[bold green]🔧 Preparing OCR engine...") as status:
            status.update("[bold cyan]🐳 Checking Docker containers...")
            time.sleep(0.5)  # Brief pause for visual effect
            
            if not self.ensure_compose_container():
                console.print("❌ [bold red]Failed to start containers[/]")
                return False
            
            status.update("[bold magenta]⚙️  Building processing pipeline...")
            cmd = self.build_docker_command(pdf_files, output_format)
            time.sleep(0.3)
            
            if self.config.get("debug_mode"):
                console.print("Docker command:", style="dim")
                console.print(" ".join(cmd), style="dim")

        # Welcome banner
        welcome_panel = Panel(
            Text.assemble(
                ("🤖 AI-POWERED OCR ENGINE\n", "bold blue"),
                (f"Ready to process {len(pdf_files)} document(s)\n", "green"),
                (f"Output format: {output_format.upper()}", "cyan")
            ),
            border_style="blue",
            title="[bold white]🚀 LAUNCHING[/]",
            title_align="center"
        )
        console.print(welcome_panel)
        
        # Show initial instructions
        instructions_text = Text.assemble(
            ("💡 Press ", "dim cyan"),
            ("'l'", "bold yellow"),
            (" to toggle between progress bars and logs", "dim cyan")
        )
        instructions_panel = Panel(
            instructions_text,
            border_style="dim blue",
            title="[dim]Controls[/]"
        )
        console.print(instructions_panel)
        
        # Enhanced progress bars with emojis and styling
        progress_manager = Progress(
            TextColumn("📊 [bold blue]{task.description}", justify="left"),
            BarColumn(bar_width=35, complete_style="green", finished_style="bold green"),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
            "•",
            TimeRemainingColumn(),
            console=console,
        )
        
        # Start progress context manager
        with progress_manager as progress:
            
            # Overall progress across all files
            overall_task = progress.add_task(
                "🗂️  Overall Progress", 
                total=len(pdf_files),
                visible=not show_logs
            )
            
            # Current document progress  
            doc_task = progress.add_task(
                "📄 Current Document", 
                total=100,
                visible=False
            )
            
            processed_files = 0
            current_file = ""
            processed_pages = 0
            total_pages = 0
            
            try:
                # Start processing
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                if process.stdout:
                    for line in iter(process.stdout.readline, ''):
                        if not line:
                            break
                        
                        # Check for toggle keypress
                        key = self.check_keypress()
                        if key and key.lower() == 'l':
                            show_logs = not show_logs
                            mode_text = "LOG MODE" if show_logs else "PROGRESS BAR MODE"
                            mode_color = "yellow" if show_logs else "green"
                            console.print(f"\n[bold {mode_color}]📺 Switched to {mode_text}[/]\n")
                            
                            # Toggle progress bar visibility
                            progress.update(overall_task, visible=not show_logs)
                            progress.update(doc_task, visible=not show_logs and current_file)
                            
                        # Parse the log line for progress information
                        log_info = self.parse_olmocr_log(line)
                        
                        # New document started
                        if 'current_file' in log_info:
                            current_file = log_info['current_file']
                            
                            if not show_logs:
                                # Show document transition banner
                                doc_banner = Panel.fit(
                                    f"📑 Starting OCR: [bold yellow]{current_file}[/]",
                                    border_style="magenta",
                                    title="[bold white]📄 New Document[/]"
                                )
                                console.print(doc_banner)
                                
                                progress.update(
                                    doc_task,
                                    description=f"📑 Processing: [yellow]{current_file}[/]",
                                    completed=0,
                                    total=100,
                                    visible=True
                                )
                        
                        # Update page progress within current document
                        if 'page_progress' in log_info and not show_logs:
                            processed_pages = log_info.get('pages_completed', processed_pages)
                            total_pages = log_info.get('pages_total', total_pages)
                            progress.update(
                                doc_task,
                                completed=log_info['page_progress'],
                                description=f"📃 {current_file}: [cyan]Page {processed_pages}/{total_pages}[/]"
                            )
                        
                        # Document completed
                        if log_info.get('document_completed'):
                            processed_files += 1
                            motivational_msg = self.get_motivational_message()
                            
                            if not show_logs:
                                progress.update(overall_task, completed=processed_files)
                                progress.update(
                                    doc_task,
                                    completed=100,
                                    description=f"✅ [bold green]Completed: {current_file}[/] [dim]- {motivational_msg}[/]"
                                )
                                
                                # Brief celebration pause
                                time.sleep(0.8)
                        
                        # Show status updates with enhanced descriptions
                        if 'status' in log_info and not show_logs:
                            status_emoji = {
                                'Starting processing': '🏁',
                                'Extracting text': '🔤', 
                                'Converting to markdown': '📝',
                                'Saving output': '💾'
                            }
                            emoji = status_emoji.get(log_info['status'], '⚙️')
                            progress.update(
                                doc_task,
                                description=f"{emoji} [cyan]{current_file}: {log_info['status']}[/]"
                            )
                        
                        # Enhanced log highlighting
                        if 'error' in log_info:
                            self.highlight_log_line(f"ERROR: {log_info['error']}", console)
                        elif show_logs:
                            # In log mode, show all log lines
                            self.highlight_log_line(line, console)
                        elif not any(key in log_info for key in ['current_file', 'page_progress', 'status', 'document_completed']):
                            # In progress mode, only show debug/error/warning lines
                            if self.config.get("debug_mode") or "ERROR" in line or "WARNING" in line:
                                self.highlight_log_line(line, console)
                
                # Wait for process completion
                return_code = process.wait()
                total_time = time.time() - start_time
                
                # Ensure progress bars show completion
                if not show_logs:
                    progress.update(overall_task, completed=len(pdf_files))
                    progress.update(doc_task, completed=100, visible=False)
                
                if return_code == 0:
                    self.show_completion_celebration(console, len(pdf_files), total_time)
                    return True
                else:
                    console.print(Panel(
                        f"❌ [bold red]Processing failed with exit code {return_code}[/]\n"
                        f"Check the logs above for details.",
                        border_style="red",
                        title="[bold red]⚠️  PROCESSING FAILED[/]"
                    ))
                    return False
                    
            except KeyboardInterrupt:
                console.print(Panel(
                    "⚠️ [bold yellow]Operation cancelled by user[/]\n"
                    "Partial results may be available in workspace directory.",
                    border_style="yellow",
                    title="[bold yellow]🛑 CANCELLED[/]"
                ))
                if 'process' in locals() and process.poll() is None:
                    process.terminate()
                    process.wait()
                return False
            except Exception as e:
                console.print(Panel(
                    f"💥 [bold red]Unexpected error: {e}[/]\n"
                    f"Please check your configuration and try again.",
                    border_style="red", 
                    title="[bold red]❌ ERROR[/]"
                ))
                return False

    def process_pdfs(self, pdf_files: List[str], output_format: str = "markdown") -> bool:
        """Process PDF files using OCR with progress visualization."""
        # Use rich progress visualization if available, fallback to simple version
        try:
            return self.process_pdfs_with_progress(pdf_files, output_format)
        except ImportError:
            # Fallback to simple processing if rich is not available
            return self.process_pdfs_simple(pdf_files, output_format)
    
    def process_pdfs_simple(self, pdf_files: List[str], output_format: str = "markdown") -> bool:
        """Simple PDF processing without rich progress (fallback)."""
        if not pdf_files:
            print("No PDF files specified")
            return False
        
        print(f"Processing {len(pdf_files)} PDF file(s):")
        for pdf in pdf_files:
            print(f"  - {pdf}")
        
        # Ensure container is running if using compose
        if not self.ensure_compose_container():
            return False
        
        cmd = self.build_docker_command(pdf_files, output_format)
        
        if self.config.get("debug_mode"):
            print("Docker command:")
            print(" ".join(cmd))
        
        try:
            print("Starting OCR processing...")
            result = subprocess.run(cmd)
            return result.returncode == 0
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            return False
        except Exception as e:
            print(f"Error during processing: {e}")
            return False
    
    def show_results(self) -> None:
        """Display processing results."""
        markdown_dir = self.workspace_dir / "markdown"
        results_dir = self.workspace_dir / "results"
        
        if markdown_dir.exists():
            markdown_files = list(markdown_dir.glob("*.md"))
            if markdown_files:
                print(f"\nMarkdown output files ({len(markdown_files)}):")
                for md_file in sorted(markdown_files):
                    print(f"  - {md_file.name}")
        
        if results_dir.exists():
            result_files = list(results_dir.glob("*.jsonl"))
            if result_files:
                print(f"\nResult files ({len(result_files)}):")
                for result_file in sorted(result_files):
                    print(f"  - {result_file.name}")
    
    def create_system_status_table(self) -> Table:
        """Create a beautiful system status table."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        
        # Docker status
        docker_ok = self.check_docker()
        docker_status = "✅ Ready" if docker_ok else "❌ Not Available"
        table.add_row("🐳 Docker", docker_status, "Container orchestration")
        
        # GPU support
        if self.config.get("gpu_enabled"):
            gpu_ok = self.check_gpu_support()
            gpu_status = "✅ Available" if gpu_ok else "❌ Not Detected"
            gpu_details = "NVIDIA acceleration" if gpu_ok else "CPU fallback mode"
            table.add_row("🚀 GPU", gpu_status, gpu_details)
        
        # SSL certificate
        if self.config.get("ssl_enabled"):
            cert_path = self.config.get("ssl_cert_path")
            cert_ok = cert_path and Path(cert_path).exists()
            cert_status = "✅ Valid" if cert_ok else "❌ Missing"
            cert_details = f"Corporate CA" if cert_ok else "Certificate not found"
            table.add_row("🔒 SSL", cert_status, cert_details)
        
        # Docker Compose
        compose_ok = self.check_docker_compose()
        compose_status = "✅ Available" if compose_ok else "❌ Missing"
        compose_details = "Preferred mode" if compose_ok else "Will use docker run"
        table.add_row("📋 Compose", compose_status, compose_details)
        
        return table

    def create_file_summary_panel(self) -> Panel:
        """Create a panel showing PDF file summary."""
        pdf_files = self.list_pdfs()
        
        if not pdf_files:
            content = Text("📂 No PDF files found in data directory", style="yellow")
        else:
            total_size = sum(pdf.stat().st_size for pdf in pdf_files) / (1024 * 1024)  # MB
            content = Text.assemble(
                ("📄 ", "blue"),
                (f"{len(pdf_files)} PDF file(s) ready", "green"),
                (f" ({total_size:.1f} MB total)", "cyan")
            )
        
        return Panel(
            content,
            title="[bold blue]📁 Data Directory[/]",
            border_style="blue"
        )

    def interactive_menu(self) -> None:
        """Display enhanced interactive menu with rich styling."""
        console = Console()
        
        while True:
            console.clear()
            
            # Main title
            title = Text.assemble(
                ("🤖 ", "bold blue"),
                ("AI-POWERED OCR TOOL", "bold white"),
                (" - Interactive CLI", "bold cyan")
            )
            
            title_panel = Panel(
                Align.center(title),
                border_style="blue",
                title="[bold white]⚡ POWERED BY OLMOCR ⚡[/]"
            )
            console.print(title_panel)
            
            # System status
            console.print("\n[bold white]📋 System Status[/]")
            status_table = self.create_system_status_table()
            console.print(status_table)
            
            # File summary
            console.print()
            file_panel = self.create_file_summary_panel()
            console.print(file_panel)
            
            # Menu options in a beautiful layout
            menu_table = Table(show_header=False, box=None, padding=(0, 2))
            menu_table.add_column("Option", style="bold cyan", no_wrap=True)
            menu_table.add_column("Description", style="white")
            
            menu_table.add_row("1.", "📄 List PDF files")
            menu_table.add_row("2.", "🔄 Process PDF files")  
            menu_table.add_row("3.", "📊 Show results")
            menu_table.add_row("4.", "⚙️  Configuration")
            menu_table.add_row("5.", "🐳 Docker management")
            menu_table.add_row("6.", "📺 Toggle display mode (currently: " + ("LOGS" if self.show_logs_mode else "PROGRESS") + ")")
            menu_table.add_row("7.", "❓ Help")
            menu_table.add_row("0.", "🚪 Exit")
            
            menu_panel = Panel(
                menu_table,
                title="[bold green]🎯 Main Menu[/]",
                border_style="green"
            )
            console.print(menu_panel)
            
            # Get user choice with enhanced prompt
            choice = console.input("\n[bold yellow]🎲 Select option (0-7): [/]").strip()
            
            if choice == "0":
                # Goodbye message with style
                goodbye = Panel(
                    Align.center(Text.assemble(
                        ("👋 ", "yellow"),
                        ("Thanks for using OCR CLI!", "bold green"),
                        (" See you next time! ", "cyan"),
                        ("🚀", "yellow")
                    )),
                    border_style="yellow"
                )
                console.print(goodbye)
                break
            elif choice == "1":
                self.list_pdfs_menu()
                input("\n[dim]Press Enter to continue...[/]")
            elif choice == "2":
                self.process_pdfs_menu()
                input("\n[dim]Press Enter to continue...[/]")
            elif choice == "3":
                self.show_results()
                input("\n[dim]Press Enter to continue...[/]")
            elif choice == "4":
                self.configuration_menu()
                input("\n[dim]Press Enter to continue...[/]")
            elif choice == "5":
                self.docker_management_menu()
                input("\n[dim]Press Enter to continue...[/]")
            elif choice == "6":
                self.toggle_display_mode()
                input("\n[dim]Press Enter to continue...[/]")
            elif choice == "7":
                self.show_help()
                input("\n[dim]Press Enter to continue...[/]")
            else:
                console.print("[bold red]❌ Invalid option. Please try again.[/]")
                time.sleep(1)
    
    def list_pdfs_menu(self) -> None:
        """Display PDF files menu."""
        pdf_files = self.list_pdfs()
        
        if not pdf_files:
            print(f"\nNo PDF files found in {self.data_dir}")
            print("Please place PDF files in the data directory.")
            return
        
        print(f"\nPDF files in {self.data_dir}:")
        for i, pdf_file in enumerate(pdf_files, 1):
            file_size = pdf_file.stat().st_size / (1024 * 1024)  # MB
            print(f"{i:2}. {pdf_file.name} ({file_size:.1f} MB)")
    
    def process_pdfs_menu(self) -> None:
        """PDF processing menu."""
        pdf_files = self.list_pdfs()
        
        if not pdf_files:
            print(f"\nNo PDF files found in {self.data_dir}")
            return
        
        print(f"\nFound {len(pdf_files)} PDF file(s):")
        print("a. Process all files")
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"{i}. {pdf_file.name}")
        
        choice = input("\nSelect files to process (a for all, or numbers separated by commas): ").strip()
        
        selected_files = []
        if choice.lower() == 'a':
            selected_files = [pdf.name for pdf in pdf_files]
        else:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(',')]
                selected_files = [pdf_files[i].name for i in indices if 0 <= i < len(pdf_files)]
            except ValueError:
                print("Invalid selection")
                return
        
        if not selected_files:
            print("No files selected")
            return
        
        # Output format selection
        format_choice = input("\nOutput format (1=markdown, 2=json): ").strip()
        output_format = "json" if format_choice == "2" else "markdown"
        
        self.ensure_directories()
        success = self.process_pdfs(selected_files, output_format)
        
        if success:
            print("\n✅ Processing completed successfully!")
            self.show_results()
        else:
            print("\n❌ Processing failed")
    
    def configuration_menu(self) -> None:
        """Configuration management menu."""
        while True:
            print("\n" + "-"*40)
            print("⚙️ Configuration Menu")
            print("-"*40)
            
            print("Current settings:")
            for key, value in self.config.config.items():
                print(f"  {key}: {value}")
            
            print("\nOptions:")
            print("1. Modify setting")
            print("2. Reset to defaults")
            print("3. Save configuration")
            print("0. Back to main menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.modify_setting()
            elif choice == "2":
                confirm = input("Reset all settings to defaults? (y/N): ").lower()
                if confirm == 'y':
                    self.config.reset_to_defaults()
                    print("Configuration reset to defaults")
            elif choice == "3":
                self.config.save_config()
    
    def modify_setting(self) -> None:
        """Modify a configuration setting."""
        print("\nAvailable settings:")
        settings = list(self.config.config.keys())
        for i, key in enumerate(settings, 1):
            print(f"{i}. {key}: {self.config.config[key]}")
        
        try:
            choice = int(input("\nSelect setting to modify: ")) - 1
            if 0 <= choice < len(settings):
                key = settings[choice]
                current_value = self.config.config[key]
                print(f"\nCurrent value for '{key}': {current_value}")
                
                new_value = input(f"Enter new value (press Enter to keep current): ").strip()
                if new_value:
                    # Type conversion
                    if isinstance(current_value, bool):
                        new_value = new_value.lower() in ('true', '1', 'yes', 'on')
                    elif isinstance(current_value, int):
                        new_value = int(new_value)
                    
                    self.config.set(key, new_value)
                    print(f"Updated {key} to: {new_value}")
        except (ValueError, IndexError):
            print("Invalid selection")
    
    def docker_management_menu(self) -> None:
        """Docker management menu."""
        print("\n" + "-"*40)
        print("🐳 Docker Management")
        print("-"*40)
        
        print("Options:")
        print("1. Pull latest image")
        print("2. Check Docker status")
        print("3. Check GPU support")
        print("0. Back to main menu")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            self.pull_docker_image()
        elif choice == "2":
            docker_ok = self.check_docker()
            print(f"Docker status: {'✅ Available' if docker_ok else '❌ Not available'}")
        elif choice == "3":
            gpu_ok = self.check_gpu_support()
            print(f"GPU support: {'✅ Available' if gpu_ok else '❌ Not available'}")
    
    def toggle_display_mode(self) -> None:
        """Toggle the default display mode between progress bars and logs."""
        console = Console()
        
        current_mode = "LOGS" if self.show_logs_mode else "PROGRESS BARS"
        new_mode = "PROGRESS BARS" if self.show_logs_mode else "LOGS"
        
        toggle_panel = Panel(
            Text.assemble(
                ("Current display mode: ", "white"),
                (current_mode, "bold yellow"),
                ("\n\nToggle to: ", "white"),
                (new_mode, "bold green"),
                ("\n\nNote: You can also press 'l' during processing to toggle between modes.", "dim cyan")
            ),
            title="[bold blue]📺 Display Mode Toggle[/]",
            border_style="blue"
        )
        console.print(toggle_panel)
        
        confirm = console.input(f"\n[yellow]Switch to {new_mode} mode? (y/N): [/]").strip().lower()
        if confirm == 'y':
            self.show_logs_mode = not self.show_logs_mode
            self.config.set("show_logs", self.show_logs_mode)
            self.config.save_config()
            
            success_text = f"✅ Display mode changed to: [bold green]{new_mode}[/]"
            console.print(f"\n{success_text}")
        else:
            console.print("\n[dim]Display mode unchanged.[/]")

    def show_help(self) -> None:
        """Display help information."""
        print("\n" + "-"*50)
        print("❓ Help - AI-Powered OCR Tool CLI")
        print("-"*50)
        print("""
This CLI provides an interactive interface for the OLMoCR tool.

Getting Started:
1. Place PDF files in the data directory
2. Use option 2 to process files
3. View results with option 3

Requirements:
- Docker installed and running
- NVIDIA GPU and drivers (optional but recommended)
- PDF files to process

Display Modes:
- PROGRESS BARS: Shows visual progress bars (default)
- LOGS: Shows detailed processing logs
- Toggle between modes using menu option 6
- During processing, press 'l' to toggle modes in real-time

Configuration:
- Customize settings via the Configuration menu
- Settings are saved to config.json
- Reset to defaults if needed

Docker:
- The tool runs inside a Docker container
- GPU support is automatically detected
- Images are pulled from Docker Hub

Output:
- Processed files are saved in the workspace directory
- Markdown files: workspace/markdown/
- JSON results: workspace/results/

For more information, visit:
https://github.com/allenai/olmocr
        """)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Interactive CLI for AI-Powered OCR Tool")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    parser.add_argument("--non-interactive", action="store_true", help="Run in non-interactive mode")
    parser.add_argument("--process", nargs="+", help="Process specific PDF files")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    
    args = parser.parse_args()
    
    # Initialize CLI with custom config path if provided
    cli = OCRInterface()
    cli.config = OCRConfig(args.config)
    
    if args.non_interactive:
        if args.process:
            cli.ensure_directories()
            success = cli.process_pdfs(args.process, args.format)
            sys.exit(0 if success else 1)
        else:
            print("Non-interactive mode requires --process argument")
            sys.exit(1)
    else:
        try:
            cli.interactive_menu()
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()