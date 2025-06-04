from flask import Flask, request, jsonify, send_file
import subprocess, os, requests, glob  # <-- glob eklendi

app = Flask(__name__)

@app.route("/ping")
def ping():
    return "pong"

@app.route("/build-video", methods=["POST"])
def build_video():
    try:
        image_files = [f"scene{i+1}.png" for i in range(8)]

        # 🔥 Esnek mp3 dosya ismi yakalama
        audio_candidates = glob.glob("narration.mp3*")
        if not audio_candidates:
            return jsonify({'error': 'narration.mp3 dosyası bulunamadı'}), 500
        audio_file = audio_candidates[0]

        with open("input.txt", "w") as f:
            for image in image_files:
                f.write(f"file '{image}'\n")
                f.write("duration 5\n")
            f.write(f"file '{image_files[-1]}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", "input.txt", "-vsync", "vfr", "-pix_fmt", "yuv420p", "temp.mp4"
        ], check=True)

        if not os.path.exists("temp.mp4") or not os.path.exists(audio_file):
            return jsonify({'error': 'temp.mp4 veya ses dosyası bulunamadı'}), 500

        subprocess.run([
            "ffmpeg", "-y", "-i", "temp.mp4", "-i", audio_file,
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

            # Ses dosyasını 'narration.mp3' olarak zorla
            if "narration" in file_key and (file_key.endswith(".mp3") or file_key.endswith(".mpga")):
                file.save("narration.mp3")
                uploaded.append("narration.mp3")
            else:
                file.save(file.filename)
                uploaded.append(file.filename)

        for key in request.form:
            if key not in uploaded:
                file_url = request.form[key]
                response = requests.get(file_url)
                if response.status_code == 200:
                    # Eğer ses dosyasıysa yine zorla
                    if "narration" in key and (key.endswith(".mp3") or key.endswith(".mpga")):
                        with open("narration.mp3", "wb") as f:
                            f.write(response.content)
                        uploaded.append("narration.mp3")
                    else:
                        with open(key, "wb") as f:
                            f.write(response.content)
                        uploaded.append(key)
                else:
                    return jsonify({"error": f"{key} indirilemedi: {file_url}"}), 400

        return jsonify({"status": "uploaded", "files": uploaded}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
