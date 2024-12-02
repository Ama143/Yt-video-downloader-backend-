from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL

app = Flask(__name__)
@app.route('/')
def home():
    return "Welcome to the Video Downloader API! Use the endpoints /download or /transcript."


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
