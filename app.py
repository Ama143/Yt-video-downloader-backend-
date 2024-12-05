from flask import Flask, request, jsonify, make_response
import logging
import sys
from yt_dlp import YoutubeDL
import yt_dlp
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Near the top of your file, add:
COOKIES_PATH = os.environ.get('COOKIES_PATH', os.path.join(os.getcwd(), 'cookies.txt'))
DOWNLOADS_DIR = os.environ.get('DOWNLOADS_DIR', os.path.join(os.getcwd(), 'downloads'))

# Create downloads directory if it doesn't exist
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

print(f"Current directory: {os.getcwd()}")
print(f"Cookies file exists: {os.path.isfile('./cookies.txt')}")
print(f"Cookies file path: {os.path.join(os.getcwd(), 'cookies.txt')}")
print(f"Cookies file exists: {os.path.isfile(os.path.join(os.getcwd(), 'cookies.txt'))}")


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
        'cookies_path': COOKIES_PATH,
        'cookies_exist': os.path.isfile(COOKIES_PATH),
        'current_directory': os.getcwd(),
        'downloads_directory': DOWNLOADS_DIR
    })

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
            response = jsonify({"message": result["message"], "file": output_file})
            return add_cors_headers(response), 200
        else:
            response = jsonify({"error": result["error"]})
            return add_cors_headers(response), 500

    except Exception as e:
        logger.error(f"Download error: {str(e)}", exc_info=True)
        response = jsonify({"error": f"Server error: {str(e)}"})
        return add_cors_headers(response), 500

def time_to_seconds(time_str):
    try:
        hours, minutes, seconds = map(int, time_str.split(':'))
        return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        raise ValueError("Invalid time format. Please use 'HH:MM:SS'.")

def download_section(start_time, end_time):
    def download_ranges(info_dict, ydl):
        return [{
            'start_time': start_time,
            'end_time': end_time,
            'title': 'jreclip'
        }]
    return download_ranges

# Function to download a specific section of the video
def download_video_section(url, start_time, end_time, output_file):
    output_path = os.path.join(DOWNLOADS_DIR, output_file)
    
    # Check if cookies file exists and log its status
    cookies_exist = os.path.isfile(COOKIES_PATH)
    print(f"Cookies status - Path: {COOKIES_PATH}, Exists: {cookies_exist}")
    if not cookies_exist:
        return {"success": False, "error": "Cookies file not found. Please ensure cookies.txt is properly uploaded."}

    try:
        # Configure yt-dlp with more browser-like behavior
        ydl_opts = {
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
            'outtmpl': output_path,
            'cookies': COOKIES_PATH,
            'download_ranges': download_section(start_time, end_time),
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoRemuxer',
                'preferedformat': 'mp4',
            }],
            'no_warnings': False,
            'verbose': True,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'TE': 'trailers'
            }
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                print("Attempting to extract video info...")
                info = ydl.extract_info(url, download=False)
                if info:
                    print("Video info extracted successfully, proceeding with download...")
                    # Try to extract the direct video URL first
                    formats = info.get('formats', [])
                    if formats:
                        # Filter for desired quality
                        suitable_formats = [f for f in formats 
                                         if f.get('height', 0) <= 1080 
                                         and f.get('acodec') != 'none' 
                                         and f.get('vcodec') != 'none']
                        if suitable_formats:
                            # Sort by quality (height)
                            suitable_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                            chosen_format = suitable_formats[0]
                            ydl_opts['format'] = chosen_format['format_id']
                            print(f"Selected format: {chosen_format.get('format')} ({chosen_format.get('height')}p)")
                    
                    error_code = ydl.download([url])
                    if error_code != 0:
                        raise Exception("Download failed with error code: " + str(error_code))
                    return {"success": True, "message": "Video downloaded successfully", "path": output_path}
                else:
                    raise Exception("Could not extract video info")

        except Exception as e:
            print(f"First attempt failed: {str(e)}")
            # Try alternative method with browser cookies
            try:
                print("Attempting download with alternative method...")
                ydl_opts.update({
                    'format': 'best[height<=1080]',
                    'cookies_from_browser': 'chrome',
                    'cookiesfrombrowser': ('chrome',),  # Add both formats for compatibility
                })
                if 'cookies' in ydl_opts:
                    del ydl_opts['cookies']
                
                with YoutubeDL(ydl_opts) as ydl:
                    error_code = ydl.download([url])
                    if error_code == 0:
                        return {"success": True, "message": "Video downloaded with browser cookies", "path": output_path}
                    raise Exception("Alternative download method failed")
            except Exception as e2:
                error_msg = f"Both download methods failed. Error: {str(e2)}"
                print(error_msg)
                return {"success": False, "error": error_msg}

    except Exception as e:
        error_msg = f"Download failed: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}

@app.route('/transcript', methods=['POST'])
def get_transcript():
    data = request.json
    url = data.get('url')

    try:
        ydl_opts = {
            'skip_download': True,


            'writesubtitles': True,
            'cookies': COOKIES_PATH,

            

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
