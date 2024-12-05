#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p downloads

# Copy cookies file to the correct location
if [ -f "cookies.txt" ]; then
    echo "cookies.txt found, ensuring correct permissions"
    chmod 644 cookies.txt
else
    echo "Warning: cookies.txt not found!"
fi
