Based on the provided directory structure and file contents for `allenai-olmocr`, here are a Docker Compose file, a Docker run script, and detailed instructions for using the tool with Docker.

### Prerequisites

Before you begin, ensure you have the following installed on your system:
1.  **Docker Engine**: To run containers.
2.  **Docker Compose**: For an easier way to manage Docker containers (recommended).
3.  **NVIDIA GPU Drivers**: The tool requires a compatible NVIDIA GPU.
4.  **NVIDIA Container Toolkit**: To allow Docker containers to access the GPU.

---

### Option 1: Using Docker Compose (Recommended)

Docker Compose simplifies the process of running the container by defining the configuration in a YAML file.

#### 1. Create a `docker-compose.yml` File

Create a file named `docker-compose.yml` in your project directory with the following content:

```yaml
version: '3.8'

# Docker Compose file for running the olmocr tool.
# This configuration mounts a local './data' directory for processing files
# and ensures the container has access to NVIDIA GPUs.

services:
  olmocr:
    # Use the official olmocr image from Docker Hub.
    image: alleninstituteforai/olmocr:latest
    container_name: olmocr
    
    # Keep STDIN open (-i) and allocate a pseudo-TTY (-t) for interactive use.
    stdin_open: true
    tty: true
    
    # Mount the local './data' directory into '/app/data' inside the container.
    # Place your PDFs inside './data' on your host machine to access them.
    # Output files will also be written back to this directory.
    volumes:
      - ./data:/app/data
      
    # Set the default working directory inside the container.
    working_dir: /app/data
    
    # Configure the container to use NVIDIA GPUs.
    # This requires the NVIDIA Container Toolkit to be installed on the host.
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
              
    # The default command starts an interactive bash shell inside the container.
    # You can override this to run a command directly.
    command: /bin/bash

```

#### 2. Prepare Your Directory

In the same directory where you saved `docker-compose.yml`, create a folder named `data`. This is where you will place your PDF files for processing and where the output will be saved.

```
your-project/
├── docker-compose.yml
└── data/
    └── your_document.pdf
```

#### 3. How to Use

1.  **Start an Interactive Session:**
    Open your terminal in the project directory and run the following command. This will pull the Docker image and drop you into a `bash` shell inside the container.

    ```bash
    docker compose run --rm olmocr
    ```

2.  **Run the Tool:**
    Once inside the container's shell, you are in the `/app/data` directory. You can now run the `olmocr.pipeline` command on your files.

    *   **To convert a single PDF:**
        Place a file (e.g., `sample.pdf`) in your local `data` folder. Then, inside the container shell, run:
        ```bash
        # The output will be saved to a new 'workspace' directory.
        python -m olmocr.pipeline ./workspace --markdown --pdfs sample.pdf
        ```

    *   **To convert multiple PDFs:**
        ```bash
        # This command processes all PDF files in the current directory.
        python -m olmocr.pipeline ./workspace --markdown --pdfs ./*.pdf
        ```

3.  **Access the Output:**
    The generated markdown files will be located in the `data/workspace/markdown/` directory on your host machine, mirroring the structure created inside the container.

---

### Option 2: Using a Docker Run Script

If you prefer not to use Docker Compose, you can use a shell script to simplify the `docker run` command.

#### 1. Create a `run_olmocr.sh` Script

Create a file named `run_olmocr.sh` and make it executable (`chmod +x run_olmocr.sh`).

```bash
#!/bin/bash

# A script to simplify running olmocr with Docker.
# It mounts the './data' directory from your current location into the container at /app/data.

# --- Prerequisites ---
# 1. Docker and NVIDIA Container Toolkit must be installed.
# 2. You must have a compatible NVIDIA GPU.
# ---------------------

# Create a 'data' directory in the current folder if it doesn't already exist.
# This is where you should place your input PDFs.
mkdir -p ./data

# Check if NVIDIA GPU is available on the host system.
if ! [ -x "$(command -v nvidia-smi)" ]; then
  echo 'Error: nvidia-smi is not available. This container requires an NVIDIA GPU.' >&2
  exit 1
fi

# Set the command to run. If no arguments are passed to the script,
# it defaults to an interactive bash shell.
if [ "$#" -eq 0 ]; then
  CMD="/bin/bash"
else
  CMD="$@"
fi

# Execute the docker run command.
# --gpus all: Exposes all available GPUs to the container.
# -it: Runs the container in interactive mode with a TTY.
# --rm: Automatically removes the container when it exits.
# -v "$(pwd)/data:/app/data": Mounts the local './data' directory to '/app/data' in the container.
# -w /app/data: Sets the working directory inside the container to /app/data.
docker run \
  -it \
  --rm \
  --gpus all \
  -v "$(pwd)/data:/app/data" \
  -w /app/data \
  alleninstituteforai/olmocr:latest \
  $CMD
```

#### 2. Prepare Your Directory

Just like with Docker Compose, create a `data` directory in the same location as your `run_olmocr.sh` script to hold your PDF files.

```
your-project/
├── run_olmocr.sh
└── data/
    └── your_document.pdf
```

#### 3. How to Use

1.  **Start an Interactive Session:**
    Run the script without any arguments to get a shell inside the container.

    ```bash
    ./run_olmocr.sh
    ```
    From there, you can execute `python -m olmocr.pipeline ...` as shown in the Docker Compose example.

2.  **Run a Command Directly:**
    You can pass the `olmocr` command directly to the script. The script will execute it inside the container and then exit.

    *   **Example:** To process a file named `sample.pdf` located in your `data` folder:
        ```bash
        ./run_olmocr.sh python -m olmocr.pipeline ./workspace --markdown --pdfs sample.pdf
        ```

3.  **Access the Output:**
    The output files will be saved in the `data/workspace/markdown/` directory on your host machine.