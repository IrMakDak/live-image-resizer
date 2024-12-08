import random

from flask import Flask, request, jsonify, send_file
from PIL import Image
from pathlib import Path


WIDTH = 500
HEIGHT = 700
JPEG_QUALITY = 85  # Баланс между качеством и размером файла

# TODO: change
OUTPUT_PATH = "../resized"
ORIGINALS_PATH = "../originals"


SERVER_PORT = 5000

app = Flask(__name__)


@app.route("/process_image", methods=["POST"])
def process_image():

    # Получаем данные из JSON запроса
    data = request.get_json()
    file_path = Path(data["file_path"])

    output_path = Path(OUTPUT_PATH)
    output_path.mkdir(exist_ok=True)

    try:
        stem = file_path.stem  # filename

        new_filename = f"{stem}_{WIDTH}x{HEIGHT}.jpg"

        new_path = output_path / new_filename

        with Image.open(file_path) as image:

            if image.mode != "RGB":
                image = image.convert("RGB")

            resized_image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            resized_image.save(new_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

        return {"status": "success", "message": f"Image processed: {new_filename}"}

    except Exception as error:
        return {"status": "Error", "message": str(error)}, 500


@app.route("/random_image", methods=["GET"])
def get_random_image():
    # Возвращает случайное изображение из папки
    try:
        path = Path(ORIGINALS_PATH)

        if not path.exists():
            return (
                jsonify(
                    {"status": "error", "message": "Output directory does not exist"}
                ),
                404,
            )

        # Получаем список всех .jpg файлов
        images = list(path.glob("*.jpg"))

        if not images:
            return jsonify({"status": "error", "message": "No images found"}), 404

        # Выбираем случайное изображение
        random_image = random.choice(images)

        # Возвращаем файл изображения
        return send_file(random_image, mimetype="image/jpeg")

    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500


if __name__ == "__main__":
    app.run(port=SERVER_PORT, debug=True)
