#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p downloads

# Set up Chrome for cookie extraction (if needed)
apt-get update && apt-get install -y chromium-browser

# Copy cookies file to the correct location
if [ -f "cookies.txt" ]; then
    echo "cookies.txt found, ensuring correct permissions"
    chmod 644 cookies.txt
    # Verify cookie file content
    echo "Cookie file contents (first few lines):"
    head -n 5 cookies.txt
else
    echo "Warning: cookies.txt not found!"
fi

# Print environment information
echo "Environment Setup:"
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Cookies file exists: $(test -f cookies.txt && echo "Yes" || echo "No")"
echo "Cookies file path: $(pwd)/cookies.txt"
echo "Downloads directory: $(pwd)/downloads"
