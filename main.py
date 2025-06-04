from flask import Flask, request, jsonify, send_file
import subprocess, os, requests

app = Flask(__name__)

@app.route("/ping")
def ping():
    return "pong"

@app.route("/build-video", methods=["POST"])
def build_video():
    try:
        image_files = [f"scene{i+1}.png" for i in range(8)]
        audio_file = "narration.mp3"

        with open("input.txt", "w") as f:
            for image in image_files:
                f.write(f"file '{image}'\n")
                f.write("duration 5\n")
            f.write(f"file '{image_files[-1]}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", "input.txt", "-vsync", "vfr", "-pix_fmt", "yuv420p", "temp.mp4"
        ], check=True)

        if not os.path.exists("temp.mp4") or not os.path.exists("narration.mp3"):
            return jsonify({'error': 'temp.mp4 veya narration.mp3 bulunamadı'}), 500

        subprocess.run([
            "ffmpeg", "-y", "-i", "temp.mp4", "-i", "narration.mp3",
            "-c:v", "copy", "-c:a", "aac", "final_video.mp4"
        ], check=True)

        return jsonify({
            'status': 'success',
            'message': 'Video başarıyla oluşturuldu.',
            'download_url': request.url_root.rstrip("/") + "/download"
        })

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"FFmpeg işlemi başarısız: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Genel hata: {str(e)}"}), 500

@app.route("/download")
def download_video():
    if os.path.exists("final_video.mp4"):
        return send_file("final_video.mp4", as_attachment=True)
    else:
        return jsonify({"error": "final_video.mp4 bulunamadı"}), 404

@app.route("/upload", methods=["POST"])
def upload_files():
    try:
        uploaded = []

        for file_key in request.files:
            file = request.files[file_key]
            file.save(f"./{file.filename}")
            uploaded.append(file.filename)

        for key in request.form:
            if key not in uploaded:
                file_url = request.form[key]
                response = requests.get(file_url)
                if response.status_code == 200:
                    with open(f"./{key}", "wb") as f:
                        f.write(response.content)
                    uploaded.append(key)
                else:
                    return jsonify({"error": f"{key} indirilemedi: {file_url}"}), 400

        return jsonify({"status": "uploaded", "files": uploaded}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
