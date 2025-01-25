import os
import requests
import time

from watchdog.observers import Observer
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

load_dotenv()

SERVER_PORT = int(os.getenv("SERVER_PORT", 5001))
SERVER_HOST = os.getenv("SERVER_HOST")

SERVER_PATH = f"{SERVER_HOST}:{SERVER_PORT}"


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".webp",
    ".png",
}


def request_processing(image_path):
    """Отправляет изображение на обработку серверу"""
    try:
        absolute_path = Path(image_path).resolve()

        response = requests.post(
            f"{SERVER_PATH}/images",
            json={"file_path": str(absolute_path)},
        )
        response.raise_for_status()
        print(f"Сервер ответил: {response.json()}")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке запроса: {str(e)}")
    except Exception as e:
        print(f"Неожиданная ошибка при обработке {image_path.name}: {str(e)}")


def request_deletion(image_path: Path):
    """Отправляет изображение на обработку серверу"""
    try:
        absolute_path = Path(image_path).resolve()
        response = requests.get(
            f"{SERVER_PATH}/images/get-image-id",
            params={"file_path": str(absolute_path)},
        )
        response.raise_for_status()

        response_data = response.json()
        if not response_data or "file_hash" not in response_data:
            print(f"Ошибка: Не получен hash файла от сервера. Ответ: {response_data}")
            return

        file_hash = response_data["file_hash"]
        if not file_hash:  # Проверка на пустое значение
            print("Ошибка: Получен пустой hash файла")
            return

        print(f"Получил hash фотки: {file_hash}. Буду удалять")

        response = requests.delete(
            f"{SERVER_PATH}/images/{file_hash}",
        )
        response.raise_for_status()
        print("Удалил!")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке запроса: {str(e)}")
    except Exception as e:
        print(f"Неожиданная ошибка при обработке {image_path.name}: {str(e)}")


def remove_extra_processed_files(input_dir, output_folder):
    """Проверяем лишние файлы в output папке"""
    input_path = Path(input_dir)
    output_path = Path(output_folder)

    output_files = [
        f
        for f in output_path.glob("*")
        if f.suffix.lower() in SUPPORTED_EXTENSIONS and f.is_file()
    ]

    extra_files = []
    for output_file in output_files:
        input_file = input_path / output_file.name
        if not input_file.exists():
            extra_files.append(output_file)

    if extra_files:
        print(f"\nЯ нашел {len(extra_files)} лишних файлов в output папке:")
        for file_path in extra_files:
            print(f"Удалю: {file_path.name}")
            file_path.unlink()
    return {"to_remove": len(extra_files)}


def check_missing_images(input_dir, output_folder):
    """Проверяет наличие всех изображений из input в output папке"""
    input_path = Path(input_dir)
    output_path = Path(output_folder)

    # Получаем списки файлов из обеих папок
    input_files = [
        f
        for f in input_path.glob("*")
        if f.suffix.lower() in SUPPORTED_EXTENSIONS and f.is_file()
    ]

    if not input_files:
        print("Входная папка пуста")
        return

    # Проверяем отсутствующие файлы
    unprocessed_files = []
    for input_file in input_files:
        output_file = output_path / input_file.name
        if not output_file.exists():
            unprocessed_files.append(input_file)

    # Обрабатываем ненайденные файлы
    if unprocessed_files:
        print(f"Я нашел {len(unprocessed_files)} необработанных изображений :(")
        for file_path in unprocessed_files:
            print(f"Пробую обработать {file_path.name}")
            request_processing(file_path)
    else:
        print("Все изображения уже обработаны ;)")

    return {
        "to_process": len(unprocessed_files),
        **remove_extra_processed_files(input_dir, output_folder),
    }


class ImageHandler(FileSystemEventHandler):
    def __init__(self, output_path):
        self.output_path = Path(output_path)

    def on_created(self, event):
        # нам нужно обрабатывать только файлы изображений, а не папки
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            output_file = self.output_path / file_path.name
            if output_file.exists():
                print(
                    f"File {file_path.name} already exists in output folder, skipping"
                )
                return
            file_path = Path(event.src_path)
            request_processing(file_path)

    def on_deleted(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:

            output_file = self.output_path / file_path.name
            if output_file.exists():
                print(
                    f"Я видел как ты удалил {file_path.name} из input папки. Сейчас удалю и из output папки."
                )
                request_deletion(file_path)
                output_file.unlink()


def watch_directory(input_folder, output_folder):
    event_handler = ImageHandler(output_folder)
    observer = Observer()
    observer.schedule(event_handler, input_folder, recursive=False)
    observer.start()

    try:
        print(f"Начато отслеживание папки: {input_folder}")
        print(f"Изображения будут сохраняться в: {output_folder}")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()
        print("\nОтслеживание завершено")

    # чтобы Observer успел корректно остановиться
    observer.join()


if __name__ == "__main__":
    input_folder = "../input_photos"
    output_folder = "../processed_photos"

    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    check_missing_images(input_folder, output_folder)
    watch_directory(input_folder, output_folder)
