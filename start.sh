#!/bin/bash

# Set environment variable (if needed)
export ENV_VAR=value

# Change file permissions for the cookies file
chmod 644 /opt/render/project/src/cookies.txt

# Download video using yt-dlp with the correct cookies file path
yt-dlp --cookies /opt/render/project/src/cookies.txt https://youtube.com/shorts/zToQkPR4PEg?si=Jf08HN2fzA-goctq

# Start the Gunicorn server for your app
gunicorn app:app
