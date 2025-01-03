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
import platform
import json

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

def get_browser_cookie_path(browser_name):
    """Get the default cookie path based on OS and browser"""
    system = platform.system().lower()
    home = str(Path.home())
    
    paths = {
        'linux': {
            'chrome': f'{home}/.config/google-chrome/Default/Cookies',
            'firefox': f'{home}/.mozilla/firefox/*.default/cookies.sqlite',
            'chromium': f'{home}/.config/chromium/Default/Cookies',
            'opera': f'{home}/.config/opera/Cookies',
        },
        'darwin': {  # macOS
            'chrome': f'{home}/Library/Application Support/Google/Chrome/Default/Cookies',
            'firefox': f'{home}/Library/Application Support/Firefox/Profiles/*.default/cookies.sqlite',
            'safari': f'{home}/Library/Cookies/Cookies.binarycookies',
            'opera': f'{home}/Library/Application Support/com.operasoftware.Opera/Cookies',
        },
        'windows': {
            'chrome': f'{home}/AppData/Local/Google/Chrome/User Data/Default/Cookies',
            'firefox': f'{home}/AppData/Roaming/Mozilla/Firefox/Profiles/*.default/cookies.sqlite',
            'edge': f'{home}/AppData/Local/Microsoft/Edge/User Data/Default/Cookies',
            'opera': f'{home}/AppData/Roaming/Opera Software/Opera Stable/Cookies',
        }
    }
    
    return paths.get(system, {}).get(browser_name)

def get_youtube_cookies():
    """Get YouTube cookies from all available browsers"""
    all_cookies = {}
    browsers = {
        'chrome': browser_cookie3.chrome,
        'firefox': browser_cookie3.firefox,
        'edge': browser_cookie3.edge,
        'safari': browser_cookie3.safari,
        'opera': browser_cookie3.opera,
        'chromium': browser_cookie3.chromium
    }

    for browser_name, browser_func in browsers.items():
        try:
            cookie_path = get_browser_cookie_path(browser_name)
            if not cookie_path or not Path(cookie_path.split('*')[0]).parent.exists():
                logger.debug(f"Skipping {browser_name} - cookie path not found")
                continue

            try:
                cookies = browser_func(domain_name='.youtube.com')
            except ValueError as ve:
                if "not enough values to unpack" in str(ve):
                    # Try with explicit cookie file path
                    cookies = browser_func(
                        domain_name='.youtube.com',
                        cookie_file=cookie_path
                    )
                else:                    
                    raise

            cookie_count = 0
            for cookie in cookies:
                if cookie.name in ['SAPISID', 'SID', 'SSID', 'APISID', 'HSID', '__Secure-1PSID', '__Secure-3PSID']:
                    all_cookies[cookie.name] = cookie.value
                    cookie_count += 1
            
            if cookie_count > 0:
                logger.info(f"Successfully loaded {cookie_count} cookies from {browser_name}")
                return all_cookies

        except Exception as e:
            error_msg = str(e)
            if "not enough values to unpack" in error_msg:
                logger.warning(f"Cookie parsing error for {browser_name} - invalid cookie format")
            elif "Could not find profile directory" in error_msg:
                logger.warning(f"No profile directory found for {browser_name}")
            else:
                logger.warning(f"Could not load {browser_name} cookies: {error_msg}")

    # If no cookies found, try to create dummy cookies for testing
    if not all_cookies and os.environ.get('RENDER') == 'true':
        logger.info("Running on Render, using environment variable cookies if available")
        env_cookies = os.environ.get('YOUTUBE_COOKIES')
        if env_cookies:
            try:
                all_cookies = json.loads(env_cookies)
                logger.info("Successfully loaded cookies from environment variable")
                return all_cookies
            except json.JSONDecodeError:
                logger.error("Failed to parse environment variable cookies")

    logger.warning("No cookies could be loaded from any browser")
    return None

def get_ydl_opts(attempt=0):
    cookies = get_youtube_cookies()
    if not cookies:
        logger.warning("No YouTube cookies found")

    format_strategies = [
        'best[height<=720]',
        'best[height<=480]',
        'worst'
    ]

    return {
        'format': format_strategies[min(attempt, len(format_strategies)-1)],
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'cookiesfrombrowser': None,  # Don't use browser cookies directly
        'cookies': cookies,  # Use our extracted cookies
        'socket_timeout': 30,
        'retries': 5,
        'sleep_interval': random.randint(1, 3),
        'max_sleep_interval': 5,
        'http_headers': {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
        },
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'nocheckcertificate': True,
    }

@app.route('/check-auth', methods=['GET', 'OPTIONS'])
def check_auth():
    if request.method == 'OPTIONS':
        return '', 204

    try:
        cookies = get_youtube_cookies()
        if cookies:
            # Updated YouTube API request
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Cookie': '; '.join([f"{k}={v}" for k, v in cookies.items()]),
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
                'X-Origin': 'https://www.youtube.com'
            }
            
            # API request body
            payload = {
                'context': {
                    'client': {
                        'clientName': 'WEB',
                        'clientVersion': '2.20231219.00.00'
                    }
                }
            }
            
            try:
                test_response = requests.post(
                    'https://www.youtube.com/youtubei/v1/guide',
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                logger.debug(f"YouTube API response status: {test_response.status_code}")
                logger.debug(f"YouTube API response headers: {test_response.headers}")
                
                if test_response.status_code == 200:
                    response_data = test_response.json()
                    # Check if response contains expected data structure
                    if 'responseContext' in response_data:
                        return jsonify({'authenticated': True})
                    else:
                        logger.warning("YouTube API response missing expected data")
                        return jsonify({'authenticated': False, 'error': 'Invalid YouTube API response'})
                else:
                    logger.warning(f"YouTube API returned status code: {test_response.status_code}")
                    return jsonify({'authenticated': False, 'error': f'YouTube API error: {test_response.status_code}'})
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"YouTube API request failed: {str(e)}")
                return jsonify({'authenticated': False, 'error': 'Failed to verify YouTube authentication'})

        return jsonify({'authenticated': False, 'error': 'No valid YouTube cookies found'})
    except Exception as e:
        logger.error(f"Auth check error: {str(e)}")
        return jsonify({'authenticated': False, 'error': str(e)})

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

        # Verify YouTube authentication
        if not verify_youtube_cookies():
            return jsonify({
                'success': False, 
                'error': 'YouTube authentication required. Please sign in to YouTube and try again.'
            }), 401

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