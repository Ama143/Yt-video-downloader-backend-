from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
from flask_cors import CORS

app = Flask(__name__)


CORS(app)# origins=["https://yt-video-downloder.netlify.app"])

@app.route('/')
def home():
    log_request()
    return "Welcome to the Video Downloader API! Use the endpoints /download or /transcript."
@app.before_request
def log_request():
    print(f"Received {request.method} request on {request.url}")
    print(f"Payload: {request.get_json()}")


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
        'cookies': 'cookies.txt',
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
'cookies':'cookies.txt',

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
