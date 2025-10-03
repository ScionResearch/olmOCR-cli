# OLMoCR CLI Tool

A professional command-line interface for AI-powered OCR processing with real-time progress visualization and Docker integration.

## Branch Structure

- **`main`** - Core OLMoCR pipeline and CLI tool
- **`webapp`** - Web application with API and Streamlit interface

## Features

- **Real-time Progress Tracking**: Visual progress bars with document and page-level monitoring
- **Interactive Menu System**: Professional interface with system status monitoring
- **Docker Integration**: Automatic container management with GPU support detection
- **Flexible Output Formats**: JSON (default) or Markdown output options
- **Enterprise Ready**: SSL certificate support and configuration management
- **Error Handling**: Comprehensive error detection with clear feedback

## Interface Preview

### Interactive Menu
```
╭──────────────────────────────── ⚡ POWERED BY OLMOCR ⚡ ─────────────────────────────────╮
│                         🤖 AI-POWERED OCR TOOL - Interactive CLI                         │
╰──────────────────────────────────────────────────────────────────────────────────────────╯

📋 System Status
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component  ┃    Status    ┃ Details                 ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 🐳 Docker  │   ✅ Ready   │ Container orchestration │
│ 🚀 GPU     │ ✅ Available │ NVIDIA acceleration     │
│ 🔒 SSL     │   ✅ Valid   │ Corporate CA            │
│ 📋 Compose │ ✅ Available │ Preferred mode          │
└────────────┴──────────────┴─────────────────────────┘

╭─────────────────────────────────── 📁 Data Directory ────────────────────────────────────╮
│ 📄 2 PDF file(s) ready (3.3 MB total)                                                    │
╰──────────────────────────────────────────────────────────────────────────────────────────╯

╭────────────────────────────────────── 🎯 Main Menu ──────────────────────────────────────╮
│   1.    📄 List PDF files                                                                │
│   2.    🔄 Process PDF files                                                             │
│   3.    📊 Show results                                                                  │
│   4.    ⚙️  Configuration                                                                 │
│   5.    🐳 Docker management                                                             │
│   6.    📺 Toggle display mode (currently: PROGRESS)                                     │
│   7.    ❓ Help                                                                          │
│   0.    🚪 Exit                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────╯

🎲 Select option (0-7): _
```

### Configuration Menu
```
----------------------------------------
⚙️ Configuration Menu
----------------------------------------
Current settings:
  data_directory: ./input
  workspace_directory: ./input/workspace
  docker_image: alleninstituteforai/olmocr:latest
  output_format: markdown
  gpu_enabled: True
  debug_mode: False
  ssl_enabled: True
  ssl_cert_path: /path/to/your/certificate.crt
  show_logs: False

Options:
1. Modify setting
2. Reset to defaults
3. Save configuration
0. Back to main menu

Select option: _
```

### Real-Time Processing
```
╭─────────────────────────────────── 🚀 LAUNCHING ────────────────────────────────────╮
│                           🤖 AI-POWERED OCR ENGINE                                   │
│                        Ready to process 2 document(s)                               │
│                              Output format: MARKDOWN                                │
╰──────────────────────────────────────────────────────────────────────────────────────╯

## Status logging is a work in progress

📊 🗂️  Overall Progress     ━━━━━━━━━━━━━━━━░░░░ 1/2  50.0% • 0:02:15
📊 📃 research_paper.pdf: Page 5/20 ━━━━━━░░░░░░░░░░░░ 25.0% • 0:01:30

✅ Completed: research_paper.pdf
```

## System Requirements

- **Docker**: Required for OCR processing
- **Python 3.6+**: For CLI execution
- **NVIDIA GPU** (optional): For accelerated processing
- **NVIDIA Container Toolkit**: Required for GPU support

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up configuration:**
   ```bash
   cp .env.example .env
   # Edit .env if needed
   ```

3. **Run the CLI:**
   ```bash
   python3 cli.py
   ```

4. **Place PDF files in the data directory and process them through the interactive menu**

## Usage Modes

### Interactive Mode (Default)
```bash
python3 cli.py
```
Provides menu options for file listing, processing, configuration, and Docker management.

### Non-Interactive Mode
```bash
# Process specific files (JSON output by default)
python3 cli.py --non-interactive --process file1.pdf file2.pdf

# Generate Markdown output
python3 cli.py --non-interactive --process file.pdf --format markdown

# Use custom environment variables
DATA_DIRECTORY=./custom python3 cli.py --non-interactive --process document.pdf
```

## Configuration

Configuration is managed through environment variables and `.env` files. Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
# Edit .env with your settings
```

| Setting | Environment Variable | Default |
|---------|---------------------|---------|
| `DATA_DIRECTORY` | PDF input directory | `./data` |
| `WORKSPACE_DIRECTORY` | Output directory | `./data/workspace` |
| `DOCKER_IMAGE` | Docker image | `alleninstituteforai/olmocr:latest` |
| `GPU_ENABLED` | GPU acceleration | `true` |
| `DEBUG_MODE` | Show Docker commands | `false` |
| `SSL_ENABLED` | SSL certificate support | `false` |
| `SSL_CERT_PATH` | Certificate file path | `/path/to/your/certificate.crt` |

**SSL Configuration**: For corporate environments:
1. Set `SSL_ENABLED=true` and `SSL_CERT_PATH=/path/to/cert.crt` in your `.env` file  
2. Copy `docker-compose.ssl.yml.example` to `docker-compose.ssl.yml` and update certificate path
3. The CLI automatically selects the appropriate Docker Compose configuration

## Output Formats

- **JSON** (default): Structured data output with detailed OCR results
- **Markdown**: Human-readable format specified with `--format markdown` flag

## Directory Structure

```
olmocr/
├── cli.py                      # Main CLI application
├── .env.example               # Configuration template
├── .env                       # Your configuration (gitignored)
├── docker-compose.yml          # Docker Compose (SSL disabled)
├── docker-compose.ssl.yml.example  # SSL template
├── docker-compose.ssl.yml      # SSL configuration (gitignored)
├── .gitignore                 # Protects sensitive files
├── data/                     # Input PDF files (gitignored)
└── workspace/                # Processing outputs (gitignored)
    ├── markdown/             # Markdown files (if specified)
    └── results/              # JSON result files
```

## Troubleshooting

**Docker not found**: Install Docker and ensure it's running  
**GPU not detected**: Install NVIDIA drivers and Container Toolkit  
**No PDF files found**: Place PDF files in the configured data directory  
**Permission denied**: Ensure script is executable (`chmod +x cli.py`)

Enable debug mode in configuration for detailed Docker commands and processing information.

## Advanced Usage

### Batch Processing
```bash
# Process all PDFs (JSON output by default)
python3 cli.py --non-interactive --process *.pdf

# Generate Markdown output
python3 cli.py --non-interactive --process *.pdf --format markdown
```

### Custom Configuration
```bash
python3 cli.py --config /path/to/custom-config.json --process document.pdf
```

### Script Integration
```bash
#!/bin/bash
python3 cli.py --non-interactive --process batch/*.pdf --format markdown
if [ $? -eq 0 ]; then
    echo "Processing completed successfully"
fi
```