# 🤖 AI-Powered OCR CLI Tool

A premium, GUI-like command-line interface for the AI-powered OCR tool (OLMoCR) featuring real-time progress visualization, beautiful animations, and an intuitive user experience.

## Features

### 🎨 **Premium Visual Experience**
- **Rich Progress Bars**: Multi-level progress with emojis and real-time updates
- **Animated Spinners**: Smooth loading animations during setup phases  
- **Document Banners**: Beautiful transitions between processing stages
- **Color-Coded Logs**: Intelligent highlighting of errors, warnings, and status
- **Celebration Effects**: Confetti and motivational messages on completion
- **System Dashboard**: Live status monitoring with component health checks

### 🎯 **Interactive Menu System**
- Beautifully styled menu with panels and tables
- Real-time system status (Docker, GPU, SSL, Compose)
- File summary with size information and counts
- Intuitive navigation with visual feedback

### ⚡ **Enhanced Processing**
- **Non-blocking execution** with real-time log streaming
- **Smart log parsing** that tracks pages, files, and processing stages
- **Progress visualization** showing overall and per-document progress
- **Motivational feedback** with random encouragement messages
- **Error handling** with styled panels and clear messaging

### ⚙️ **Professional Configuration**
- JSON-based configuration with validation
- SSL certificate integration for corporate environments
- Docker Compose preference with fallback support
- Persistent settings with easy modification interface

### 🐳 **Intelligent Docker Integration**
- Automatic container orchestration (prefers docker-compose)
- GPU support detection and optimization
- SSL certificate mounting for secure environments
- Container health monitoring and status reporting

## 🎬 Visual Experience Preview

### Enhanced Main Menu
```
┌─────────────────⚡ POWERED BY OLMOCR ⚡─────────────────┐
│                🤖 AI-POWERED OCR TOOL - Interactive CLI                │
└────────────────────────────────────────────────────────┘

📋 System Status
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component  ┃    Status   ┃ Details              ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ 🐳 Docker  │ ✅ Ready    │ Container orchestration │
│ 🚀 GPU     │ ✅ Available│ NVIDIA acceleration     │
│ 🔒 SSL     │ ✅ Valid    │ Corporate CA            │
└────────────┴─────────────┴──────────────────────┘

┌─────────────────📁 Data Directory──────────────────┐
│            📄 3 PDF file(s) ready (45.2 MB total)            │
└────────────────────────────────────────────────────┘
```

### Real-Time Processing View
```
🚀 Starting OCR processing for 2 file(s)...

┌───────────────📄 New Document────────────────┐
│        📑 Starting OCR: research_paper.pdf        │
└──────────────────────────────────────────────┘

📊 🗂️  Overall Progress     ━━━━━━━━━━━━━━━━░░░░ 1/2  50.0% • 0:02:15
📊 📃 research_paper.pdf: Page 5/20 ━━━━━━░░░░░░░░░░░░ 25.0% • 0:01:30

✅ Completed: research_paper.pdf - ⚡ Lightning fast results!
```

### Celebration on Completion
```
┌─────────────🏆 SUCCESS 🏆──────────────┐
│             🎉 MISSION ACCOMPLISHED! 🎉              │
│                                                      │
│         Successfully processed 2 file(s)            │
│               Total time: 45.3 seconds               │
└────────────────────────────────────────┘

🎊 🎉 ✨ 🌟 💫 ⭐ 🎈 🎆 🎊 🎉 ✨ 🌟 💫 ⭐ 🎈
All files are ready in your workspace directory!
🎊 🎉 ✨ 🌟 💫 ⭐ 🎈 🎆 🎊 🎉 ✨ 🌟 💫 ⭐ 🎈
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the premium CLI:**
   ```bash
   python3 cli.py
   ```

3. **Place PDF files in the data directory and enjoy the experience!**

## Demo
```bash
# Try the test demo
python3 test_cli.py
```

## Usage Modes

### Interactive Mode (Default)
```bash
python3 cli.py
```
Launches the interactive menu system with the following options:
- 📄 List PDF files
- 🔄 Process PDF files  
- 📊 Show results
- ⚙️ Configuration
- 🐳 Docker management
- ❓ Help

### Non-Interactive Mode
```bash
# Process specific files
python3 cli.py --non-interactive --process file1.pdf file2.pdf

# Change output format
python3 cli.py --non-interactive --process *.pdf --format json

# Use custom config
python3 cli.py --config my-config.json --process document.pdf
```

## Configuration

The CLI uses a `config.json` file to store settings:

```json
{
  "data_directory": "./data",
  "workspace_directory": "./data/workspace", 
  "docker_image": "alleninstituteforai/olmocr:latest",
  "output_format": "markdown",
  "gpu_enabled": true,
  "batch_size": 1,
  "parallel_workers": 1,
  "debug_mode": false,
  "auto_cleanup": true,
  "container_name": "olmocr",
  "ssl_cert_path": "/path/to/your/certificate.crt",
  "ssl_enabled": true
}
```

### Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `data_directory` | Directory containing PDF files | `./data` |
| `workspace_directory` | Output directory for results | `./data/workspace` |
| `docker_image` | Docker image to use | `alleninstituteforai/olmocr:latest` |
| `output_format` | Default output format | `markdown` |
| `gpu_enabled` | Enable GPU acceleration | `true` |
| `batch_size` | Number of files to process together | `1` |
| `debug_mode` | Show detailed Docker commands | `false` |
| `container_name` | Docker container name | `olmocr` |
| `ssl_cert_path` | Path to SSL certificate file | `/path/to/your/certificate.crt` |
| `ssl_enabled` | Enable SSL certificate mounting | `true` |

## System Requirements

- **Docker**: Required for running the OCR processing
- **Python 3.6+**: For running the CLI script
- **NVIDIA GPU** (optional): For accelerated processing
- **NVIDIA Container Toolkit**: Required if using GPU

## Directory Structure

```
olmocr/
├── cli.py              # Main CLI application
├── config.json         # Configuration file (auto-created)
├── data/              # Input PDF files
│   ├── document1.pdf
│   └── document2.pdf
└── workspace/         # Processing outputs
    ├── markdown/      # Converted markdown files
    └── results/       # JSON result files
```

## Menu System Details

### 📄 List PDF Files
- Shows all PDF files in the data directory
- Displays file sizes for reference
- Helps identify files available for processing

### 🔄 Process PDF Files
- Interactive file selection (individual or all)
- Output format selection (Markdown/JSON)
- Real-time processing with progress indicators
- Automatic results display upon completion

### 📊 Show Results
- Lists generated markdown files
- Shows JSONL result files
- Provides file counts and locations

### ⚙️ Configuration
- View current settings
- Modify individual configuration values
- Reset to default settings
- Save configuration changes

### 🐳 Docker Management
- Pull latest OCR Docker image
- Check Docker installation status
- Verify GPU support availability
- Container management utilities

## Error Handling

The CLI includes robust error handling for:
- Missing Docker installation
- GPU availability issues
- File system permissions
- Configuration file corruption
- Processing interruptions (Ctrl+C)

## Advanced Usage

### Custom Configuration File
```bash
python3 cli.py --config /path/to/custom-config.json
```

### Batch Processing
```bash
# Process all PDFs in data directory
python3 cli.py --non-interactive --process *.pdf

# Process with JSON output
python3 cli.py --non-interactive --process *.pdf --format json
```

### Integration with Scripts
The CLI can be integrated into automated workflows:

```bash
#!/bin/bash
# Automated OCR processing script
python3 cli.py --non-interactive --process batch/*.pdf --format markdown
if [ $? -eq 0 ]; then
    echo "Processing completed successfully"
    # Post-processing steps...
fi
```

## Troubleshooting

### Common Issues

1. **Docker not found**: Install Docker and ensure it's running
2. **Permission denied**: Make sure the script is executable (`chmod +x cli.py`)
3. **GPU not detected**: Install NVIDIA drivers and Container Toolkit
4. **No PDF files found**: Place PDF files in the configured data directory

### Debug Mode
Enable debug mode in configuration to see detailed Docker commands and processing information.

## Support

For issues and feature requests, please refer to the main OLMoCR documentation or check the Docker container logs for detailed error information.