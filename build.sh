#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process..."

# Install system dependencies
echo "Installing system dependencies..."
apt-get update && apt-get install -y \
    chromium-browser \
    ffmpeg \
    python3-pip \
    python3-venv

# Create and activate virtual environment
echo "Setting up Python virtual environment..."
python -m venv .venv
source .venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p downloads
chmod 755 downloads

# Set up cookies
echo "Setting up cookies..."
if [ -f "cookies.txt" ]; then
    echo "cookies.txt found, ensuring correct permissions"
    chmod 644 cookies.txt
    echo "Cookie file contents (first few lines):"
    head -n 5 cookies.txt
else
    echo "Warning: cookies.txt not found!"
fi

# Print environment information
echo "Environment Setup:"
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "pip version: $(pip --version)"
echo "Cookies file exists: $(test -f cookies.txt && echo "Yes" || echo "No")"
echo "Cookies file path: $(pwd)/cookies.txt"
echo "Downloads directory: $(pwd)/downloads"

# Verify critical components
echo "Verifying components:"
echo "FFmpeg version: $(ffmpeg -version | head -n 1)"
echo "Chrome version: $(chromium-browser --version)"

# Create startup script
echo "Creating startup script..."
cat > start.sh << 'EOF'
#!/bin/bash
source .venv/bin/activate
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --access-logfile - --error-logfile - --log-level info
EOF

chmod +x start.sh

echo "Build completed successfully!"
