# filepath: app.py
from flask import Flask, request, jsonify, send_file,make_response
import youtube_dl
import subprocess
import os

app = Flask(__name__)
ALLOWED_ORIGINS = ["https://yt-video-downloder.netlify.app", "http://localhost:3000"]
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
@app.route('/download', methods=['POST'])
def download_video():
    response = make_response()
    add_cors_headers(response)
    data = request.json
    video_url = data['videoUrl']
    format = data['format']
    start_time = data.get('startTime')
    end_time = data.get('endTime')

    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            video_id = info_dict.get("id", None)
            video_ext = info_dict.get("ext", None)
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
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_file(f'downloads/{filename}', as_attachment=True)

if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    app.run(host='0.0.0.0', port=10000)