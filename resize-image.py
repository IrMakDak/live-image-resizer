import argparse
import time

from PIL import Image
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


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
    parser.add_argument("new_width", type=int, help="Новая ширина изображений")
    parser.add_argument("new_height", type=int, help="Новая высота изображений")
    parser.add_argument(
        "--output",
        "-o",
        default="./resized",
        help="Папка для сохранения результатов (по умолчанию: ./resized)",
    )
    return parser.parse_args()


class ImageHandler(FileSystemEventHandler):
    def __init__(self, new_width, new_height, output_path):
        self.new_width = new_width
        self.new_height = new_height
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)

    def on_created(self, event):
        # нам нужно обрабатывать только файлы изображений, а не папки
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                self.resize_image(file_path)
                print(f"Обработан новый файл: {file_path.name}")
            except Exception as e:
                print(f"Ошибка при обработке {file_path.name}: {str(e)}")

    def resize_image(self, file_path):

        stem = file_path.stem  # filename
        suffix = file_path.suffix  # extension with dot

        width = int(self.new_width)
        height = int(self.new_height)

        new_filename = f"{stem}_{width}x{height}{suffix}"

        new_path = self.output_path / new_filename

        image = Image.open(file_path)

        resized_image = image.resize((width, height))

        resized_image.save(new_path)


def watch_directory(directory_path, new_width, new_height, output_dir):
    event_handler = ImageHandler(new_width, new_height, output_dir)
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
    watch_directory(args.directory_path, args.new_width, args.new_height, args.output)
