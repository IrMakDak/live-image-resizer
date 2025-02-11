import base64


from PIL import Image
from pathlib import Path
from flask import Flask, request
from database.database_manager import DatabaseManager, ImageStatus
from logging import Logger
from typing import Dict, Any
from utils.exceptions import ImageNotFoundError
from utils.decorators import format_response


class ImageProcessor:
    WIDTH = 500
    HEIGHT = 700
    JPEG_QUALITY = 85  # Баланс между качеством и размером файла

    def __init__(self, output_path: str, db_manager: DatabaseManager, logger: Logger):
        self.output_path = Path(output_path)
        self.db_manager = db_manager
        self.logger = logger

    @staticmethod
    def get_decoded_image(image_path: str) -> str:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

    def process_and_save_image(self, image_path: Path) -> Path:
        new_filename = f"{image_path.stem}.jpg"
        new_path = self.output_path / new_filename

        with Image.open(image_path) as image:
            if image.mode != "RGB":
                image = image.convert("RGB")

            resized_image = image.resize(
                (self.WIDTH, self.HEIGHT), Image.Resampling.LANCZOS
            )
            resized_image.save(
                new_path, "JPEG", quality=self.JPEG_QUALITY, optimize=True
            )

        return new_path


def setup_routes(app: Flask, logger: Logger, config: Dict[str, Any]):
    db_manager = DatabaseManager()
    image_processor = ImageProcessor(config["OUTPUT_PATH"], db_manager, logger)

    # GET

    @app.route("/images/get-image-id", methods=["GET"])
    @format_response(success_code=200, logger=logger)
    def get_image_id():

        file_path = request.args.get("file_path")
        if not file_path:
            logger.error("file_path не указан")
            raise ValueError("file_path is required")

        absolute_path = Path(file_path).resolve()
        file_hash = db_manager.get_file_hash(str(absolute_path))

        if file_hash is None:
            logger.warning(f"Image not found for path: {file_path}")
            raise ImageNotFoundError(f"Image not found for path: {file_path}")

        return {"file_hash": file_hash} 

    @app.route("/random-image", methods=["GET"])
    @format_response(success_code=200, logger=logger)
    def get_random_image():
        if not image_processor.output_path.exists():
            raise FileNotFoundError("Output directory does not exist")

        try:
            random_image = db_manager.get_random_image()
            image = image_processor.get_decoded_image(random_image["original_path"])

            return {"file_hash": random_image["file_hash"], "image": image}

        except Exception as e:
            logger.error(str(e))

    # POST

    @app.route("/images", methods=["POST"])
    @format_response(success_code=201, logger=logger)
    def process_image():
        try:
            data = request.get_json()

            if not data or "file_path" not in data:
                raise ValueError("file_path не указан в JSON")

            file_path = Path(data["file_path"])
            absolute_path = Path(file_path).resolve()

            # Начинаем обработку - сохраняем в БД и получаем hash
            file_hash = db_manager.process_image(Path(absolute_path))

            db_manager.update_status(file_hash, ImageStatus.PROCESSING)

            try:
                # Создаем директорию если не существует
                image_processor.output_path.mkdir(exist_ok=True)

                # Обрабатываем изображение
                new_path = image_processor.process_and_save_image(absolute_path)

                # Успешное завершение
                db_manager.update_status(file_hash, ImageStatus.SUCCESS)
                return {"message": f"Image processed: {new_path.name}"}

            except Image.DecompressionBombError:
                db_manager.update_status(
                    file_hash, ImageStatus.ERROR, "Изображение слишком большое"
                )
                logger.error("Изображение не обработано. Cлишком большое", file_hash)
                raise ValueError("Image is too big")

            except Exception as e:
                db_manager.update_status(
                    file_hash, ImageStatus.ERROR, f"Ошибка обработки: {str(e)}"
                )
                logger.error("Ошибка обработки изображения", str(e))

        except Exception as e:
            # Прочие ошибки
            db_manager.update_status(
                file_hash, ImageStatus.ERROR, f"Неожиданная ошибка: {str(e)}"
            )
            logger.error(f"Ошибка при обработке изображения: {str(e)}")

    # DELETE

    @app.route("/images/<file_hash>", methods=["DELETE"])
    @format_response(success_code=204, logger=logger)
    def delete_image(file_hash: str):
        try:
            file_info = db_manager.get_image_path(file_hash)

            # Удаляем из БД
            db_manager.delete_image(file_hash)

            # Удаляем фото
            original_path = Path(file_info["original_path"])

            original_path = Path(file_info["original_path"])
            if original_path.exists():
                original_path.unlink()
                return {"message": f"Deleted file: {original_path}"}

            return {"message": "File already deleted"}

        except ValueError as e:
            logger.error("ValueError: ", str(e))
        except Exception as e:
            logger.error(f"Error deleting files: {str(e)}")
