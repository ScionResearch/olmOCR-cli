#!/usr/bin/env python3
"""
Simple web server for uploading documents to be processed by OLMoCR
"""

import os
from pathlib import Path
from flask import Flask, request, render_template_string, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

# Load environment variables
def load_env_file(env_path: str = ".env") -> None:
    """Load environment variables from .env file if it exists."""
    env_file = Path(env_path)
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    if key not in os.environ:
                        os.environ[key] = value

load_env_file()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration
UPLOAD_FOLDER = os.getenv('DATA_DIRECTORY', './input')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload folder exists
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OLMoCR Document Upload</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .upload-area {
            border: 2px dashed #667eea;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s;
            cursor: pointer;
            background: #f8f9ff;
        }
        .upload-area:hover {
            border-color: #764ba2;
            background: #f0f1ff;
        }
        .upload-area.dragover {
            border-color: #764ba2;
            background: #e8e9ff;
            transform: scale(1.02);
        }
        .upload-icon {
            font-size: 48px;
            margin-bottom: 20px;
        }
        .upload-text {
            color: #666;
            margin-bottom: 20px;
        }
        input[type="file"] {
            display: none;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
            margin-top: 20px;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .file-list {
            margin-top: 20px;
        }
        .file-item {
            background: #f8f9ff;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .file-name {
            color: #333;
            font-weight: 500;
        }
        .file-size {
            color: #666;
            font-size: 12px;
        }
        .remove-btn {
            background: #ff4757;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 15px;
            cursor: pointer;
            font-size: 12px;
        }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #eee;
        }
        .stat-item {
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            font-size: 12px;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 OLMoCR Document Upload</h1>
        <p class="subtitle">Upload documents for OCR processing</p>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" enctype="multipart/form-data" id="uploadForm">
            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📄</div>
                <div class="upload-text">
                    <strong>Click to browse</strong> or drag and drop files here
                    <br>
                    <small>Supported: PDF, PNG, JPG, TIFF (max 100MB)</small>
                </div>
                <input type="file" name="files" id="fileInput" multiple accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif">
            </div>
            <div class="file-list" id="fileList"></div>
            <button type="submit" class="btn" id="uploadBtn" disabled>Upload Documents</button>
        </form>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{{ file_count }}</div>
                <div class="stat-label">Files in Queue</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ total_size }}</div>
                <div class="stat-label">Total Size</div>
            </div>
        </div>
    </div>
    
    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const uploadBtn = document.getElementById('uploadBtn');
        let selectedFiles = [];
        
        uploadArea.addEventListener('click', () => fileInput.click());
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });
        
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });
        
        function handleFiles(files) {
            selectedFiles = Array.from(files);
            updateFileList();
            uploadBtn.disabled = selectedFiles.length === 0;
        }
        
        function updateFileList() {
            fileList.innerHTML = '';
            selectedFiles.forEach((file, index) => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <div>
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${formatFileSize(file.size)}</div>
                    </div>
                    <button type="button" class="remove-btn" onclick="removeFile(${index})">Remove</button>
                `;
                fileList.appendChild(fileItem);
            });
        }
        
        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updateFileList();
            uploadBtn.disabled = selectedFiles.length === 0;
            
            const dt = new DataTransfer();
            selectedFiles.forEach(file => dt.items.add(file));
            fileInput.files = dt.files;
        }
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    """Handle file upload."""
    if request.method == 'POST':
        if 'files' not in request.files:
            flash('No files selected', 'error')
            return redirect(request.url)
        
        files = request.files.getlist('files')
        uploaded_count = 0
        errors = []
        
        for file in files:
            print(f"DEBUG: Processing file: {file.filename if file else 'None'}")
            if file and file.filename:
                print(f"DEBUG: File extension check: {file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'no extension'}")
                print(f"DEBUG: allowed_file result: {allowed_file(file.filename)}")
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    uploaded_count += 1
                    print(f"DEBUG: Saved file to: {filepath}")
                else:
                    errors.append(f"{file.filename}: Invalid file type")
            else:
                errors.append("Empty file or missing filename")
        
        if uploaded_count > 0:
            flash(f'Successfully uploaded {uploaded_count} file(s)! Ready for OCR processing.', 'success')
        else:
            error_msg = 'No valid files uploaded'
            if errors:
                error_msg += ': ' + ', '.join(errors)
            flash(error_msg, 'error')
        
        return redirect(url_for('upload_file'))
    
    # Get statistics
    upload_path = Path(app.config['UPLOAD_FOLDER'])
    files = list(upload_path.glob('*'))
    files = [f for f in files if f.is_file() and allowed_file(f.name)]
    
    file_count = len(files)
    total_bytes = sum(f.stat().st_size for f in files)
    
    # Format total size
    if total_bytes == 0:
        total_size = '0 B'
    else:
        units = ['B', 'KB', 'MB', 'GB']
        i = 0
        size = total_bytes
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        total_size = f'{size:.1f} {units[i]}'
    
    return render_template_string(HTML_TEMPLATE, 
                                  file_count=file_count, 
                                  total_size=total_size)

@app.route('/api/status')
def status():
    """API endpoint for upload folder status."""
    upload_path = Path(app.config['UPLOAD_FOLDER'])
    files = list(upload_path.glob('*'))
    files = [f for f in files if f.is_file() and allowed_file(f.name)]
    
    return jsonify({
        'file_count': len(files),
        'files': [f.name for f in files],
        'upload_folder': str(app.config['UPLOAD_FOLDER'])
    })

if __name__ == '__main__':
    port = int(os.getenv('WEBSERVER_PORT', 5000))
    host = os.getenv('WEBSERVER_HOST', '0.0.0.0')
    print(f"\n🚀 Starting OLMoCR Web Server")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"🌐 Server: http://{host}:{port}")
    print(f"📄 Allowed file types: {', '.join(ALLOWED_EXTENSIONS)}")
    print(f"\nPress Ctrl+C to stop\n")
    app.run(host=host, port=port, debug=False)
