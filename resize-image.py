from PIL import Image
from pathlib import Path
import argparse

# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler


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


def resize_image(file_path, new_width, new_height, output_path):

    # Get original filename without extension
    path = Path(file_path)

    stem = path.stem  # filename
    suffix = path.suffix  # extension with dot

    width = int(new_width)
    height = int(new_height)

    new_filename = f"{stem}_{width}x{height}{suffix}"

    new_path = output_path / new_filename

    image = Image.open(path)

    resized_image = image.resize((width, height))

    resized_image.save(new_path)

    return resized_image


def process_directory(directory_path, new_width, new_height, output_dir):
    directory = Path(directory_path)

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    total_processed = 0
    for file_path in directory.iterdir():
        if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                resize_image(file_path, new_width, new_height, output_path)
                total_processed += 1
                print(f"Обработан файл: {file_path.name}")
            except Exception:
                print(f"Ошибка при обработке {file_path.name}: {str(Exception)}")

    print(f"\nГотово! Обработано файлов: {total_processed}")


if __name__ == "__main__":
    args = parse_args()
    process_directory(args.directory_path, args.new_width, args.new_height, args.output)
    print(f"Готово! Файлы сохранены с разрешением {args.new_width}x{args.new_height}")
