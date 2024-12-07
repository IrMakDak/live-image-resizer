import requests
import time
import argparse

from watchdog.observers import Observer
from pathlib import Path
from watchdog.events import FileSystemEventHandler

SERVER_PORT = 5000
PROCESS_IMAGE_HOST = "http://127.0.0.1"
PROCESS_IMAGE_ROUTE = "/process_image"

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".webp",
    ".png",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Изменение размера изображений в папке"
    )
    parser.add_argument("directory_path", help="Путь к папке с изображениями")
    parser.add_argument(
        "--output",
        "-o",
        default="./resized",
        help="Папка для сохранения результатов (по умолчанию: ./resized)",
    )
    return parser.parse_args()


class ImageHandler(FileSystemEventHandler):
    def __init__(self, output_path):
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)

    def on_created(self, event):
        # нам нужно обрабатывать только файлы изображений, а не папки
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                response = requests.post(
                    f"{PROCESS_IMAGE_HOST}:{SERVER_PORT}{PROCESS_IMAGE_ROUTE}",
                    json={"file_path": str(event.src_path)},
                )
                # Проверяем статус-код
                response.raise_for_status()

                print(f"Сервер ответил: {response.json()}")
            except requests.exceptions.RequestException as e:
                print(f"Ошибка при отправке запроса: {str(e)}")
            except Exception as e:
                print(f"Неожиданная ошибка при обработке {file_path.name}: {str(e)}")


def watch_directory(directory_path, output_dir):
    event_handler = ImageHandler(output_dir)
    observer = Observer()
    observer.schedule(event_handler, directory_path, recursive=False)
    observer.start()

    try:
        print(f"Начато отслеживание папки: {directory_path}")
        print(f"Изображения будут сохраняться в: {output_dir}")
        print("Нажмите Ctrl+C для завершения...")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()
        print("\nОтслеживание завершено")

    # чтобы Observer успел корректно остановиться
    observer.join()


if __name__ == "__main__":
    args = parse_args()
    watch_directory(args.directory_path, args.output)
