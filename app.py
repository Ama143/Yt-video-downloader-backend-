# filepath: app.py
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import subprocess
import os
import logging
import random
import time
from pathlib import Path
from requests.exceptions import RequestException
import requests
import browser_cookie3

app = Flask(__name__)
ALLOWED_ORIGINS = [
    "https://yt-video-downloder.netlify.app",
    "http://localhost:3000",
    "https://yt-video-downloader-backendppy.onrender.com"
]

# Configure CORS
CORS(app, resources={
    r"/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
})

logging.basicConfig(level=logging.DEBUG)
logger = app.logger

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY', 'your_secret_key')

def verify_recaptcha(token):
    try:
        response = requests.post('https://www.google.com/recaptcha/api/siteverify', {
            'secret': RECAPTCHA_SECRET_KEY,
            'response': token
        })
        result = response.json()
        return result.get('success', False)
    except Exception as e:
        logger.error(f"reCAPTCHA verification error: {str(e)}")
        return False

def get_ydl_opts(attempt=0):
    # Get cookies from the most common browsers
    def get_cookies():
        cookies = []
        browsers = [
            ('chrome', browser_cookie3.chrome),
            ('firefox', browser_cookie3.firefox),
            ('edge', browser_cookie3.edge),
        ]
        
        for browser_name, browser_func in browsers:
            try:
                cookies = browser_func(domain_name='.youtube.com')
                logger.info(f"Successfully loaded cookies from {browser_name}")
                return cookies
            except Exception as e:
                logger.warning(f"Could not load {browser_name} cookies: {str(e)}")
        return None

    format_strategies = [
        'best[height<=720]',
        'best[height<=480]',
        'worst'
    ]
    
    return {
        'format': format_strategies[min(attempt, len(format_strategies)-1)],
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'cookiefile': None,  # Don't use cookie file
        'cookiesfrombrowser': ('chrome', 'firefox', 'edge'),  # Try multiple browsers
        'socket_timeout': 30,
        'retries': 5,
        'sleep_interval': random.randint(1, 3),  # Random delay between retries
        'max_sleep_interval': 5,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
        },
        'quiet': False,
        'no_warnings': False,
    }

@app.route('/download', methods=['POST', 'OPTIONS'])
def download_video():
    if request.method == 'OPTIONS':
        return '', 204

    try:
        if not request.is_json:
            logger.error("Request does not contain JSON data")
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400

        data = request.json
        logger.debug(f"Received data: {data}")

        if 'videoUrl' not in data or 'format' not in data:
            logger.error("Missing required fields in request")
            return jsonify({'success': False, 'error': 'videoUrl and format are required'}), 400

        # Remove recaptcha verification since we're using cookies now
        video_url = data['videoUrl']
        format = data['format']
        start_time = data.get('startTime')
        end_time = data.get('endTime')

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                # Add random delay between attempts
                if attempt > 0:
                    time.sleep(random.uniform(2, 5))

                ydl_opts = get_ydl_opts(attempt)
                logger.info(f"Attempt {attempt + 1}/{max_retries} with format: {ydl_opts['format']}")
                
                with YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(video_url, download=True)
                    
                    # If successful, clean up old files
                    cleanup_old_files('downloads', max_files=10)
                    
                    video_id = info_dict.get("id", None)
                    video_ext = info_dict.get("ext", None)
                    break  # Success, exit retry loop
                    
            except DownloadError as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise last_error
                continue

        input_file = f'downloads/{video_id}.{video_ext}'
        output_file = f'downloads/{video_id}.{format}'

        if start_time and end_time:
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_file, '-ss', start_time, '-to', end_time,
                '-c', 'copy', output_file
            ]
        else:
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_file, output_file
            ]

        subprocess.run(ffmpeg_cmd)

        return jsonify({'success': True, 'downloadUrl': f'/downloads/{video_id}.{format}'})
    except DownloadError as e:
        logger.error(f"Download failed after {max_retries} attempts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {str(e)}")
        return jsonify({'success': False, 'error': f"Conversion failed: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error details: {str(e)}", exc_info=True)
        if "Sign in to confirm your age" in str(e):
            return jsonify({'success': False, 'error': 'Please sign in to YouTube first'}), 401
        return jsonify({'success': False, 'error': str(e)}), 400

def cleanup_old_files(directory, max_files=10):
    """Keep only the most recent files to manage disk space"""
    try:
        files = Path(directory).glob('*')
        sorted_files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
        for file in sorted_files[max_files:]:
            file.unlink()
    except Exception as e:
        logger.warning(f"Cleanup error: {str(e)}")

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_file(f'downloads/{filename}', as_attachment=True)

if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    app.run(host='0.0.0.0', port=10000)