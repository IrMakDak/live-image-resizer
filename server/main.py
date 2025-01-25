import base64
import os

from flask import Flask, request, jsonify
from PIL import Image
from pathlib import Path
from functools import wraps
from database_manager import DatabaseManager


ORIGINALS_PATH = os.getenv("ORIGINALS_PATH")
OUTPUT_PATH = os.getenv("OUTPUT_PATH")

SERVER_HOST = os.getenv("SERVER_HOST")
SERVER_PORT = int(os.getenv("SERVER_PORT", 5001))


WIDTH = 500
HEIGHT = 700
JPEG_QUALITY = 85  # Баланс между качеством и размером файла


app = Flask(__name__)
db_manager = DatabaseManager()


def get_decoded_image(image_path: str):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def format_response(success_code: int = 200):
    def decorator(f):
        # сохраняет метаданные оригинальной функции
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                return jsonify(result), success_code
            except ValueError as e:
                return jsonify({"status": "error", "message": str(e)}), 404
            except Exception as e:
                return jsonify({"status": "Error", "message": str(e)}), 500

        return wrapper

    return decorator


# GET
@app.route("/images/get-image-id", methods=["GET"])
@format_response(success_code=200)
def get_image_id():
    try:
        file_path = request.args.get("file_path")
        if not file_path:
            raise ValueError("file_path не указан")

        absolute_path = Path(file_path).resolve()

        print(f"Ищу hash для пути: {absolute_path}")
        file_hash = db_manager.get_file_hash(str(absolute_path))  # Передаем строку в БД
        return {"file_hash": file_hash}

    except Exception as e:
        raise ValueError(str(e))


@app.route("/random-image", methods=["GET"])
@format_response(success_code=200)
def get_random_image():
    path = Path(OUTPUT_PATH)

    if not path.exists():
        raise ValueError("Output directory does not exist")

    try:
        random_image = db_manager.get_random_image()
        image = get_decoded_image(random_image["original_path"])

        return {"file_hash": random_image["file_hash"], "image": image}

    except Exception as e:
        raise ValueError(str(e))


# POST


@app.route("/images", methods=["POST"])
@format_response(success_code=201)
def process_image():
    # Получаем данные из запроса
    data = request.get_json()
    file_path = Path(data["file_path"])
    absolute_path = Path(file_path).resolve()

    file_hash = db_manager.create_file_hash(absolute_path)
    is_photo_processed = db_manager.is_photo_processed(file_hash)
    if is_photo_processed:
        absolute_path.unlink()
        return {"message": f"Already processed"}

    db_manager.process_image(Path(absolute_path))

    output_path = Path(OUTPUT_PATH)
    output_path.mkdir(exist_ok=True)

    new_filename = f"{absolute_path.stem}.jpg"

    new_path = output_path / new_filename

    with Image.open(absolute_path) as image:

        if image.mode != "RGB":
            image = image.convert("RGB")

        resized_image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        resized_image.save(new_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

    return {"message": f"Image processed: {new_filename}"}


# DELETE


@app.route("/images/<file_hash>", methods=["DELETE"])
@format_response(success_code=204)
def delete_image(file_hash: str):
    try:
        file_info = db_manager.get_image_path(file_hash)

        # Удаляем из БД
        db_manager.delete_image(file_hash)

        # Удаляем фото
        original_path = Path(file_info["original_path"])

        deleted_files = []
        if original_path.exists():
            original_path.unlink()
            deleted_files.append(str(original_path))

        if deleted_files:
            print(f"Удалены файлы: {', '.join(deleted_files)}")

    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        raise ValueError(f"Error deleting files: {str(e)}")


if __name__ == "__main__":
    app.run(port=SERVER_PORT, host="0.0.0.0", debug=True)
