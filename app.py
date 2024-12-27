from flask import Flask, request, jsonify, make_response
import logging
import sys
from yt_dlp import YoutubeDL
import os
import time
import random
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

# Add after other configuration
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
if not YOUTUBE_API_KEY:
    logger.warning("YouTube API key not found in environment variables!")

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


import subprocess







    






def time_to_seconds(time_str):
    try:
        hours, minutes, seconds = map(int, time_str.split(':'))
        return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        raise ValueError("Invalid time format. Please use 'HH:MM:SS'.")


def get_video_info(video_id):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # Get video details
        request = youtube.videos().list(
            part="snippet,contentDetails,status",
            id=video_id
        )
        response = request.execute()

        if not response['items']:
            raise Exception("Video not found or is private")

        video = response['items'][0]
        
        # Check if video is downloadable
        if video['status']['privacyStatus'] == 'private':
            raise Exception("This video is private")
        if video['status'].get('embeddable') is False:
            raise Exception("This video cannot be embedded")

        return {
            'title': video['snippet']['title'],
            'description': video['snippet']['description'],
            'channel': video['snippet']['channelTitle'],
            'duration': video['contentDetails']['duration']
        }
    except HttpError as e:
        logger.error(f"YouTube API error: {str(e)}")
        raise Exception(f"YouTube API error: {str(e)}")

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    import re
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Invalid YouTube URL")

@app.route('/download', methods=['POST'])
def download_section():
    data = request.json
    url = data.get('url')
    startt = data.get('start')
    endd = data.get('end')
    
    if not url or not startt or not endd:
        return jsonify({'error': 'Missing parameters'}), 400

    try:
        # Extract video ID and get info from YouTube API
        video_id = extract_video_id(url)
        video_info = get_video_info(video_id)
        
        start_time = time_to_seconds(startt)
        end_time = time_to_seconds(endd)
        
        timestamp = int(time.time())
        output_file = f"clip_{timestamp}.mp4"
        full_output_path = os.path.join(DOWNLOADS_DIR, output_file)

        # Enhanced yt-dlp options with age verification bypass
        ydl_opts = {
            'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': full_output_path,
            'quiet': False,
            'no_warnings': False,
            'age_limit': 0,  # Bypass age verification
            'extract_flat': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'socket_timeout': 30,
            'retries': 20,
            'fragment_retries': 20,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate'
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['configs', 'webpage'],
                    'skip': ['hls', 'dash', 'translated_subs']
                }
            },
            'postprocessor_args': {
                'ffmpeg': ['-ss', str(start_time), '-t', str(end_time - start_time)]
            }
        }

        with YoutubeDL(ydl_opts) as ydl:
            try:
                logger.info(f"Attempting to download video: {url}")
                # First try with flat extraction
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise Exception("Failed to extract video information")

                # Then download with the best format
                ydl_opts['extract_flat'] = False
                ydl_opts['format'] = 'best[ext=mp4]/best'
                
                with YoutubeDL(ydl_opts) as dl_ydl:
                    dl_info = dl_ydl.extract_info(url, download=True)
                
                return jsonify({
                    'message': 'Download complete',
                    'file': output_file,
                    'path': full_output_path,
                    'quality': f"{dl_info.get('height', 'unknown')}p",
                    'title': video_info['title'],
                    'channel': video_info['channel']
                })

            except Exception as e:
                logger.error(f"Download failed: {str(e)}")
                # Try alternative format if first attempt fails
                ydl_opts['format'] = '(mp4)[height<=720]/best[ext=mp4]/best'
                ydl_opts['extract_flat'] = False
                
                with YoutubeDL(ydl_opts) as alt_ydl:
                    info = alt_ydl.extract_info(url, download=True)
                    if info:
                        return jsonify({
                            'message': 'Download complete (alternative format)',
                            'file': output_file,
                            'path': full_output_path,
                            'quality': f"{info.get('height', 'unknown')}p",
                            'title': video_info['title'],
                            'channel': video_info['channel']
                        })
                    raise

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Download error: {error_msg}")
        return jsonify({'error': f'Download failed: {error_msg}'}), 500

def download_video_section(url, start_time, end_time, output_file, cookie_file):
    try:
        ydl_opts = {
            'format': '(bestvideo+bestaudio/best)[height>=?2160][fps>=?60]/(bestvideo+bestaudio/best)[height>=?1440][fps>=?60]/(bestvideo+bestaudio/best)[height>=?1080][fps>=?60]/bestvideo+bestaudio/best',
            'outtmpl': os.path.join(DOWNLOADS_DIR, output_file),
            'cookies': cookie_file,  # Use the provided cookie file
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

@app.route('/downloads', methods=['POST', 'OPTIONS'])
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
        cookies_data = data.get('cookies')  # Get cookies from request

        if not all([url, start, end, cookies_data]):
            return jsonify({"error": "Missing required parameters (url, start, end, cookies)"}), 400

        # Create a temporary cookies file
        temp_cookie_file = os.path.join(DOWNLOADS_DIR, f'cookies_{int(time.time())}.txt')
        with open(temp_cookie_file, 'w') as f:
            f.write(cookies_data)

        logger.info(f"Processing download - URL: {url}, Start: {start}, End: {end}")
        
        start_time = time_to_seconds(start)
        end_time = time_to_seconds(end)
        output_file = f"clip_{start}_{end}.mp4"

        # Modify ydl_opts in download_video_section to use the temporary cookie file
        result = download_video_section(url, start_time, end_time, output_file, temp_cookie_file)
        
        # Clean up temporary cookie file
        try:
            os.remove(temp_cookie_file)
        except:
            pass

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
