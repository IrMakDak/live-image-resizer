import os

from flask import Flask
from pathlib import Path
from dotenv import load_dotenv
from api.routes import setup_routes
from utils.logger_setup import setup_logger


ORIGINALS_PATH = os.getenv("ORIGINALS_PATH")
OUTPUT_PATH = os.getenv("OUTPUT_PATH")

load_dotenv()


class Config:
    ORIGINALS_PATH = os.getenv("ORIGINALS_PATH")
    OUTPUT_PATH = os.getenv("OUTPUT_PATH")
    SERVER_HOST = os.getenv("SERVER_HOST")
    SERVER_PORT = int(os.getenv("SERVER_PORT", 5001))


def create_app():
    app = Flask(__name__)

    # Инициализация конфигурации
    app.config.from_object(Config)

    # Настройка логгера
    logger = setup_logger()

    # Создаем необходимые директории
    Path(app.config["OUTPUT_PATH"]).mkdir(exist_ok=True)

    # Настройка маршрутов
    setup_routes(app, logger, app.config)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=Config.SERVER_PORT, host="0.0.0.0", debug=True)
