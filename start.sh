#!/bin/bash
export ENV_VAR=value
chmod 644 /opt/render/project/src/cookies.txt

yt-dlp --cookies opt/render/project/src/cookies.txt
gunicorn app:app
