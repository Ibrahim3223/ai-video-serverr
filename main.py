from mutagen.mp3 import MP3
from flask import Flask, request, jsonify, send_file
import subprocess, os, requests, glob  # <-- glob eklendi

app = Flask(__name__)

@app.route("/ping")
def ping():
    return "pong"

from flask import Flask, request, jsonify, send_file
import subprocess, os
from mutagen.mp3 import MP3

app = Flask(__name__)

@app.route("/build-video", methods=["POST"])
def build_video():
    try:
        image_files = [f"scene{i+1}.png" for i in range(8)]
        audio_file = "narration.mp3"

        # 1️⃣ Ses süresini al
        audio = MP3(audio_file)
        total_audio_duration = audio.info.length  # saniye olarak float
        per_scene_duration = round(total_audio_duration / len(image_files), 2)

        # 2️⃣ FFmpeg komutunu hazırlamak için inputları diz
        ffmpeg_cmd = ["ffmpeg", "-y"]
        for image in image_files:
            ffmpeg_cmd += ["-loop", "1", "-t", str(per_scene_duration), "-i", image]

        # 3️⃣ filter_complex kısmı
        concat_inputs = ''.join([f'[{i}:v]' for i in range(len(image_files))])
        filter_complex = f"{concat_inputs}concat=n={len(image_files)}:v=1:a=0,format=yuv420p[v]"
        ffmpeg_cmd += ["-filter_complex", filter_complex, "-map", "[v]"]

        # 4️⃣ sesi ekle
        ffmpeg_cmd += ["-i", audio_file, "-c:a", "aac", "-shortest", "final_video.mp4"]

        # 5️⃣ Komutu çalıştır
        subprocess.run(ffmpeg_cmd, check=True)

        # 6️⃣ Kontrol ve yanıt
        if not os.path.exists("final_video.mp4"):
            return jsonify({'error': 'final_video.mp4 bulunamadı'}), 500

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
