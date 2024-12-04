from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from flask_cors import CORS
import os
print(f"Current directory: {os.getcwd()}")
print(f"Cookies file exists: {os.path.isfile('./cookies.txt')}")
print(f"Cookies file path: {os.path.join(os.getcwd(), 'cookies.txt')}")
print(f"Cookies file exists: {os.path.isfile(os.path.join(os.getcwd(), 'cookies.txt'))}")


# Define cookies as a dictionary
cookies = {
"SNID": "AFAt11qWl_H73Ljq6sp8y5GLz0rybgBzXC3tpHjQVbeQ3D1hgVbLoSa668BTHaJCqoC-qqKjTYQKpJeL58TasC0sIQONUPCB2d0", "VISITOR_INFO1_LIVE": "-s84k_h-fTE", "VISITOR_PRIVACY_METADATA": "CgJOUBIEGgAgNQ%3D%3D", "OTZ": "7848643_33_33__33_", "SID": "g.a000qwjxSD_40OJF2BpMrvEJs2V7d_E0PXp8syA1JriuGtte4QgzaTLi8Ir1Ul3SmMTNwAFUXAACgYKAZoSARUSFQHGX2MiGZdSb_8pwhVuxxcNoXv4WRoVAUF8yKorr7hlj3eaLxwADTyFPuc30076", "__Secure-1PSID": "g.a000qwjxSD_40OJF2BpMrvEJs2V7d_E0PXp8syA1JriuGtte4QgzHM_3P4vK5FoCxdUN9jHhSgACgYKASwSARUSFQHGX2MiYS9TkCSIfNUqNWTmwm3oBBoVAUF8yKoej9BIx3CZsv5Ol_puMwtQ0076", "__Secure-3PSID": "g.a000qwjxSD_40OJF2BpMrvEJs2V7d_E0PXp8syA1JriuGtte4QgzRrDnIx2nilIYDFfYeP66CwACgYKASoSARUSFQHGX2MirgmUabNJ0DamN69hgcUzvBoVAUF8yKoXx2cTTwHPB1kSHTh2-c990076", "HSID": "AfHgVLP9f9DoQsYsT", "SSID": "A4BQmgCVI_oed38ms", "APISID": "rjrksyLkMS3VBuMF/Ab9AG668X7N5ORSXt", "SAPISID": "12QjXKxEidIDCwcJ/A7xDSyKumVbDHboc2", "__Secure-1PAPISID": "12QjXKxEidIDCwcJ/A7xDSyKumVbDHboc2", "__Secure-3PAPISID": "12QjXKxEidIDCwcJ/A7xDSyKumVbDHboc2", "__Host-GAPS": "1:U_1TQY3hTcm1COhg8w96_sKQBMUPULHLL7GMmYsQOtSaxNcxRpnS7YI6po7CvlB9_15e6cb7_ewGhlub2deLJzupvHitIw:nu2QRAz-Q1XoZjyy", "ACCOUNT_CHOOSER": "AFx_qI7hAnQGXZ5j8qeOrPodqXuCc3XnkJwtoF28ZrXg9OsjmbfW4631-HjT_qpdeyNVx35aacqp8QakZPGCOOHviW7m-s-tLzy8VOZ7hm2FzzZ5jHpi0Y-FUEKkf3ZiYrqYmFbBZAvM", "OSID": "g.a000qwjxSGyQmRHGHArAqsIxRp3HJQ-RrOTLXvhrCbxbQFaX8KqRCRZy47maLewVDbWPECa_QgACgYKAe0SARUSFQHGX2MirjsyDZZOH0VxMnDx31RDGxoVAUF8yKoLVuoDD7bD8b8pF8H3a-uQ0076", "SEARCH_SAMESITE": "CgQI3JwB", "AEC": "AZ6Zc-VCDKH4nIWYqFa2xE98qUgf-5P1ERdSI-0FocRiy8DtRWH0bnSgxA", "LOGIN_INFO": "AFmmF2swRgIhAKxbk-xbVTIbIWnCf7UNMgb5N461rGYiriPeoD8LFiZnAiEA7nJ-9MPibWhX_9ItCyH4lCIHZgdoqc7R2AhuyQ9Do74:QUQ3MjNmdy01T1I3TG5fSEFOMWdwb09GT2FCcDBxT1VDc2paR01yUTBKTHFjRDZVXy1sNnpYQ2hrY3BYcVN4eERFLWtGdFkzRXVxeERLUzlsaGRoUlE4cEFONXRma1NNeWdxRXdEclZieC1hc1FWMjM3UG9DdmRuTF9EUjFp",
 }



# Convert cookies into a list of cookie strings
cookie_list = [f"{key}={value}" for key, value in cookies.items()]
cookie_string = "; ".join(cookie_list)

def load_and_check_cookies(cookies_path, test_url="https://youtube.com/shorts/zToQkPR4PEg?si=Jf08HN2fzA-goctq"):
    ydl_opts = {
        'cookiesfile': cookies_path,  # Load cookies from the specified file
        'http_headers': {
        'Cookie': cookie_string,  # Pass cookies as HTTP headers
    },
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
if load_and_check_cookies(cookies_file):
    print("Cookies are valid and loaded.")
else:
    print("Cookies are invalid or not loaded.")

app = Flask(__name__)




CORS(app, resources={r"/*": {"origins": "https://yt-video-downloder.netlify.app"}},supports_credentials=True)
CORS(app)
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

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    start = data.get('start')
    end = data.get('end')

    try:
        start_time = time_to_seconds(start)
        end_time = time_to_seconds(end)
        output_file = f"downloads/clip_{start}_{end}.mp4"

        download_video_section(url, start_time, end_time, output_file)

        return jsonify({"message": f"Video section saved as {output_file}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


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
    ydl_opts = {
        'format': '(bestvideo+bestaudio/best)[height>=?2160][fps>=?60]/(bestvideo+bestaudio/best)[height>=?1440][fps>=?60]/(bestvideo+bestaudio/best)[height>=?1080][fps>=?60]/bestvideo+bestaudio/best',
        'outtmpl': output_file,
        #'cookies': os.path.join(os.getcwd(), 'cookies.txt'),

        'cookies-from-browser':'chrome',
        'download_ranges': download_section(start_time, end_time),
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoRemuxer',
            'preferedformat': 'mp4',
        }],
        'no_warnings': True,
        'ignoreerrors': True,
        'format_sort': [
            'res',       # Sort by resolution
            'fps',       # Then by fps
            'codec:h264',# Prefer h264 codec
            'size',      # Then by size
            'br',        # Then by bitrate
            'asr',       # Audio sample rate
            'proto'      # Protocol
        ],
        'format_sort_force': True,
        'keepvideo': True,
        'postprocessor_args': [
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k'
        ],
        'verbose': True  # Add verbose output to see format selection
    }

    def select_best_format(ydl, url):
        info = ydl.extract_info(url, download=False)
        formats = info.get('formats', [])
        # Sort formats by resolution and fps
        video_formats = [f for f in formats if f.get('vcodec') != 'none']
        video_formats.sort(
            key=lambda f: (
                f.get('height', 0),
                f.get('fps', 0),
                f.get('tbr', 0)  # Total bitrate as final tiebreaker
            ),
            reverse=True
        )
        if video_formats:
            best_video = video_formats[0]
            # Update format to use the best found format
            format_id = best_video.get('format_id', '')
            if format_id:
                ydl_opts['format'] = f'{format_id}+bestaudio/best'
                return True
        return False

    try:
        with YoutubeDL(ydl_opts) as ydl:
            # First try to select the best format
            if select_best_format(ydl, url):
                error_code = ydl.download([url])
                if error_code == 0:
                    messagebox.showinfo("Success", f"Video section downloaded successfully in best quality to {output_file}")
                    return
            
            # If format selection fails, try the default approach
            error_code = ydl.download([url])
            if error_code != 0:
                raise Exception("Download failed")
            messagebox.showinfo("Success", f"Video section downloaded successfully to {output_file}")
    except Exception as e:
        error_msg = str(e)
        try:
            # If the first attempt fails, try with a simpler format
            ydl_opts['format'] = 'best'
            ydl_opts['format_sort'] = []
            with YoutubeDL(ydl_opts) as ydl:
                error_code = ydl.download([url])
                if error_code == 0:
                    messagebox.showinfo("Success", f"Video downloaded with fallback quality to {output_file}")
                    return
        except Exception as e2:
            error_msg += f"\nSecond attempt failed: {str(e2)}"
        
        print(f"An error occurred: {error_msg}")


@app.route('/transcript', methods=['POST'])
def get_transcript():
    data = request.json
    url = data.get('url')

    try:
        ydl_opts = {
            'skip_download': True,


            'writesubtitles': True,
            #'cookies': os.path.join(os.getcwd(), 'cookies.txt'),

            'cookies-from-browser':'chrome',

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
