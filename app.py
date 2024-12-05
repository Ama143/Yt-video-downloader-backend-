from flask import Flask, request, jsonify, make_response
import logging
import sys
from yt_dlp import YoutubeDL
import yt_dlp
import os
import time
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Near the top of your file, add:
DOWNLOADS_DIR = os.environ.get('DOWNLOADS_DIR', os.path.join(os.getcwd(), 'downloads'))

# Create downloads directory if it doesn't exist
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

print(f"Current directory: {os.getcwd()}")
print(f"Downloads directory: {DOWNLOADS_DIR}")


def load_and_check_cookies(cookies_path, test_url="https://youtube.com/shorts/zToQkPR4PEg?si=Jf08HN2fzA-goctq"):
    ydl_opts = {
        'cookies': cookies_path,  # Load cookies from the specified file
        #'cookies-from-browser':'chrome',
        'quiet': True,           # Reduce output verbosity
    }
    
    try:
        # Initialize YoutubeDL with cookies
        with YoutubeDL(ydl_opts) as ydl:
            # Test by extracting info about a video or the YouTube homepage
            info = ydl.extract_info(test_url, download=False)
            print("Cookies loaded successfully!")
            print(f"Extracted Info: {info}")
            return True
    except Exception as e:
        print(f"Failed to load cookies: {e}")
        return False

# Example usage
cookies_file = "./cookies.txt"  # Path to your cookies.txt file
#if load_and_check_cookies(cookies_file):
#    print("Cookies are valid and loaded.")
#else:
#    print("Cookies are invalid or not loaded.")
#
app = Flask(__name__)

# Configure CORS
ALLOWED_ORIGINS = ["https://yt-video-downloder.netlify.app", "http://localhost:3000"]

# Basic health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

# Simplified CORS handling
def add_cors_headers(response, methods=['GET', 'POST', 'OPTIONS']):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers.update({
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': ', '.join(methods),
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Max-Age': '3600'  # Cache preflight requests
        })
    return response

@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        response = make_response()
        add_cors_headers(response)
        return response, 200

@app.after_request
def after_request(response):
    return add_cors_headers(response)

# Error handlers
@app.errorhandler(415)
def unsupported_media_type(error):
    response = jsonify({
        "error": "Unsupported Media Type",
        "message": "Content-Type must be application/json"
    })
    return add_cors_headers(response), 415

@app.errorhandler(500)
def internal_server_error(error):
    response = jsonify({
        "error": "Internal Server Error",
        "message": str(error)
    })
    return add_cors_headers(response), 500

@app.route('/')
def home():
    log_request()
    return "Welcome to the Video Downloader API! Use the endpoints /download or /transcript."

@app.before_request
def log_request():
    print(f"Received {request.method} request on {request.url}")
    print(f"Payload: {request.get_json()}")

@app.route('/check-cookies')
def check_cookies():
    return jsonify({
        'current_directory': os.getcwd(),
        'downloads_directory': DOWNLOADS_DIR
    })

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
]

def time_to_seconds(time_str):
    try:
        hours, minutes, seconds = map(int, time_str.split(':'))
        return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        raise ValueError("Invalid time format. Please use 'HH:MM:SS'.")

def download_video_section(url, start_time, end_time, output_file):
    try:
        ydl_opts = {
            'format': '(bestvideo+bestaudio/best)[height>=?2160][fps>=?60]/(bestvideo+bestaudio/best)[height>=?1440][fps>=?60]/(bestvideo+bestaudio/best)[height>=?1080][fps>=?60]/bestvideo+bestaudio/best',
            'outtmpl': os.path.join(DOWNLOADS_DIR, output_file),
            'cookies': './cookies.txt',
            'quiet': False,
            'verbose': True,
            'no_warnings': False,
            'nocheckcertificate': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'no_color': True,
            'noprogress': True,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'extractor_retries': 3,
            'retries': 5,
            'fragment_retries': 5,
            'skip_download_archive': True,
            'rm_cachedir': True,
            'force_generic_extractor': False,
            'sleep_interval': 3,
            'max_sleep_interval': 5,
            'sleep_interval_requests': 1,
            'http_headers': {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'TE': 'trailers'
            },
            'postprocessors': [{
                'key': 'FFmpegVideoRemuxer',
                'preferedformat': 'mp4',
            }]
        }

        # Remove any existing cookie files or settings
        if 'cookiefile' in ydl_opts:
            del ydl_opts['cookiefile']
        if 'cookiesfrombrowser' in ydl_opts:
            del ydl_opts['cookiesfrombrowser']

        def download_ranges(info_dict, ydl):
            return [[start_time, end_time]]

        ydl_opts['download_ranges'] = download_ranges

        with YoutubeDL(ydl_opts) as ydl:
            try:
                print(f"Attempting to download video: {url}")
                print("Attempting to extract video in highest quality (up to 4K 60fps)...")
                
                # Add a small delay before request
                time.sleep(random.uniform(1, 3))
                
                info = ydl.extract_info(url, download=True)
                if info:
                    quality = info.get('height', 'unknown')
                    fps = info.get('fps', 'unknown')
                    format_note = info.get('format_note', '')
                    print(f"Successfully downloaded: {quality}p {fps}fps {format_note}")
                    return {
                        "success": True,
                        "message": f"Successfully downloaded video section in {quality}p {fps}fps {format_note}",
                        "title": info.get('title', 'Unknown'),
                        "quality": f"{quality}p {fps}fps {format_note}"
                    }
                else:
                    raise Exception("Failed to extract video information")
            except Exception as e:
                print(f"First attempt failed: {str(e)}")
                print("Attempting download with alternative method...")
                try:
                    # Try with different format and new user agent
                    ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                    ydl_opts['http_headers']['User-Agent'] = random.choice(USER_AGENTS)
                    
                    time.sleep(random.uniform(2, 4))
                    
                    with YoutubeDL(ydl_opts) as alt_ydl:
                        info = alt_ydl.extract_info(url, download=True)
                        if info:
                            quality = info.get('height', 'unknown')
                            fps = info.get('fps', 'unknown')
                            format_note = info.get('format_note', '')
                            print(f"Successfully downloaded (alternative): {quality}p {fps}fps {format_note}")
                            return {
                                "success": True,
                                "message": f"Successfully downloaded video in {quality}p {fps}fps {format_note} (alternative method)",
                                "title": info.get('title', 'Unknown'),
                                "quality": f"{quality}p {fps}fps {format_note}"
                            }
                        else:
                            raise Exception("Failed to extract video information with alternative method")
                except Exception as alt_e:
                    print(f"Alternative method failed: {str(alt_e)}")
                    # Final attempt with simpler format
                    try:
                        # Final attempt with most compatible format and new user agent
                        ydl_opts['format'] = 'best[ext=mp4]/best'
                        ydl_opts['http_headers']['User-Agent'] = random.choice(USER_AGENTS)
                        
                        time.sleep(random.uniform(2, 4))
                        
                        with YoutubeDL(ydl_opts) as final_ydl:
                            info = final_ydl.extract_info(url, download=True)
                            if info:
                                quality = info.get('height', 'unknown')
                                fps = info.get('fps', 'unknown')
                                format_note = info.get('format_note', '')
                                print(f"Successfully downloaded (final): {quality}p {fps}fps {format_note}")
                                return {
                                    "success": True,
                                    "message": f"Successfully downloaded video in {quality}p {fps}fps {format_note} (final method)",
                                    "title": info.get('title', 'Unknown'),
                                    "quality": f"{quality}p {fps}fps {format_note}"
                                }
                            else:
                                raise Exception("All download methods failed")
                    except Exception as final_e:
                        print(f"Final attempt failed: {str(final_e)}")
                        raise

    except Exception as e:
        error_msg = str(e)
        print(f"Download error: {error_msg}")
        return {
            "success": False,
            "error": f"Failed to download video: {error_msg}"
        }

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    if request.method == 'OPTIONS':
        response = make_response()
        return add_cors_headers(response), 200

    try:
        # Log request details
        logger.info(f"Received download request from: {request.headers.get('Origin')}")
        logger.info(f"Request headers: {dict(request.headers)}")

        if not request.is_json:
            logger.warning(f"Invalid content type: {request.content_type}")
            return jsonify({
                "error": "Content-Type must be application/json",
                "received": request.content_type
            }), 415

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        url = data.get('url')
        start = data.get('start')
        end = data.get('end')

        if not all([url, start, end]):
            return jsonify({"error": "Missing required parameters (url, start, end)"}), 400

        logger.info(f"Processing download - URL: {url}, Start: {start}, End: {end}")
        
        start_time = time_to_seconds(start)
        end_time = time_to_seconds(end)
        output_file = f"clip_{start}_{end}.mp4"

        result = download_video_section(url, start_time, end_time, output_file)
        
        if result["success"]:
            response = jsonify({"message": result["message"], "file": output_file, "quality": result["quality"]})
            return add_cors_headers(response), 200
        else:
            response = jsonify({"error": result["error"]})
            return add_cors_headers(response), 500

    except Exception as e:
        logger.error(f"Download error: {str(e)}", exc_info=True)
        response = jsonify({"error": f"Server error: {str(e)}"})
        return add_cors_headers(response), 500

@app.route('/transcript', methods=['POST'])
def get_transcript():
    data = request.json
    url = data.get('url')

    try:
        ydl_opts = {
            'skip_download': True,


            'writesubtitles': True,


            'subtitleslangs': ['en'],  # Language preference, adjust as needed
            'quiet': True
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            subtitles = info.get('subtitles', {})

            if 'en' in subtitles:
                subtitle_url = subtitles['en'][0]['url']
                return jsonify({"transcript_url": subtitle_url})
            else:
                raise Exception("Transcript not available in English.")

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
