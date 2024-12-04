#!/bin/bash
export ENV_VAR=value
gunicorn app:app
yt-dlp --cookies opt/render/project/src/cookies.txt
