#!/usr/bin/env python3

import subprocess
from pathlib import Path

def check_docker_compose() -> bool:
    """Check if docker-compose is available and docker-compose.yml exists."""
    try:
        # Check for Docker Compose V2 first (docker compose)
        print("Testing Docker Compose V2...")
        result = subprocess.run(['docker', 'compose', 'version'], 
                              capture_output=True, text=True, timeout=10)
        print(f"V2 result: returncode={result.returncode}, stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}'")
        if result.returncode == 0:
            # Check if docker-compose.yml exists
            yml_exists = Path("docker-compose.yml").exists()
            print(f"docker-compose.yml exists: {yml_exists}")
            return yml_exists
        
        # Fallback to Docker Compose V1 (docker-compose)
        print("Testing Docker Compose V1...")
        result = subprocess.run(['docker-compose', '--version'], 
                              capture_output=True, text=True, timeout=10)
        print(f"V1 result: returncode={result.returncode}, stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}'")
        if result.returncode == 0:
            # Check if docker-compose.yml exists
            yml_exists = Path("docker-compose.yml").exists()
            print(f"docker-compose.yml exists: {yml_exists}")
            return yml_exists
        
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    result = check_docker_compose()
    print(f"Final result: {result}")