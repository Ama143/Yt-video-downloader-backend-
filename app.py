from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
import yt_dlp
from flask_cors import CORS
import os
import time

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

CORS(app, resources={r"/*": {
    "origins": ["https://yt-video-downloder.netlify.app", "http://localhost:3000"],
    "supports_credentials": True,
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

@app.route('/')
def home():
    log_request()
    return "Welcome to the Video Downloader API! Use the endpoints /download or /transcript."

@app.before_request
def log_request():
    print(f"Received {request.method} request on {request.url}")
    print(f"Payload: {request.get_json()}")

@app.route("/transcript", methods=["OPTIONS"])
def handle_preflight():
    response = jsonify({"message": "CORS preflight successful"})
    response.headers.add("Access-Control-Allow-Origin", "https://yt-video-downloder.netlify.app")
    response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    return response

@app.route('/check-cookies')
def check_cookies():
    return jsonify({
        'cookies_path': COOKIES_PATH,
        'cookies_exist': os.path.isfile(COOKIES_PATH),
        'current_directory': os.getcwd(),
        'downloads_directory': DOWNLOADS_DIR
    })

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        url = data.get('url')
        start = data.get('start')
        end = data.get('end')
        
        if not all([url, start, end]):
            return jsonify({"error": "Missing required parameters (url, start, end)"}), 400

        start_time = time_to_seconds(start)
        end_time = time_to_seconds(end)
        output_file = f"clip_{start}_{end}.mp4"

        result = download_video_section(url, start_time, end_time, output_file)
        
        if result["success"]:
            return jsonify({"message": result["message"], "file": output_file})
        else:
            return jsonify({"error": result["error"]}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        'no_warnings': True,
        'ignoreerrors': True
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            error_code = ydl.download([url])
            if error_code != 0:
                raise Exception("Download failed")
            return {"success": True, "message": f"Video downloaded successfully", "path": output_path}
    except Exception as e:
        print(f"Download error: {str(e)}")
        # Try with simpler format
        try:
            ydl_opts['format'] = 'best'
            with YoutubeDL(ydl_opts) as ydl:
                error_code = ydl.download([url])
                if error_code == 0:
                    return {"success": True, "message": "Video downloaded with fallback quality", "path": output_path}
                raise Exception("Fallback download failed")
        except Exception as e2:
            error_msg = f"Both download attempts failed. First error: {str(e)}, Second error: {str(e2)}"
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
