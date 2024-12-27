#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process..."

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | xargs)
    echo "Loaded environment variables"
fi

# Check for YouTube API key
if [ -z "$YOUTUBE_API_KEY" ]; then
    echo "Warning: YOUTUBE_API_KEY is not set!"
fi

# Install system dependencies
echo "Installing system dependencies..."
apt-get update && apt-get install -y \
    ffmpeg \
    python3-pip \
    python3-venv

# Set up Python environment
echo "Setting up Python virtual environment..."
python -m venv .venv
source .venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create downloads directory
echo "Creating directories..."
mkdir -p downloads
chmod 755 downloads

# Create startup script
echo "Creating startup script..."
cat > start.sh << 'EOF'
#!/bin/bash
source .venv/bin/activate
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
EOF

chmod +x start.sh

echo "Build completed successfully!"
