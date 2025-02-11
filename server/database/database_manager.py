import os
import sqlite3
import hashlib

from enum import Enum
from pathlib import Path
from utils.exceptions import ImageProcessingError, DatabaseError, ImageNotFoundError

from contextlib import contextmanager

SERVER_PORT = int(os.getenv("SERVER_PORT", 5001))
SERVER_HOST = os.getenv("SERVER_HOST")


SERVER_PATH = f"{SERVER_HOST}:{SERVER_PORT}"

# TODO: SQLAlchemy?


class ImageStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    PROCESSING = "processing"


class DatabaseManager:

    def __init__(self):
        self.db_path = "image_processing.db"
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для соединения с БД"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
        except sqlite3.Error as e:
            raise DatabaseError(f"Ошибка при работе с БД: {e}")
        finally:
            if conn:
                conn.close()

    def init_db(self) -> None:
        """Инициализация базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_path TEXT UNIQUE,
                    file_hash TEXT UNIQUE,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    error_message TEXT
                )
            """
            )
            conn.commit()

    @staticmethod
    def create_file_hash(file_path: Path) -> str:
        """Создание хеша файла для уникальной идентификации."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except IOError as e:
            raise ImageProcessingError(f"Ошибка чтения файла {file_path}: {e}")
        except Exception as e:
            raise ImageProcessingError(f"Ошибка создания хеша для {file_path}: {e}")

    def update_status(
        self, file_hash: str, status: ImageStatus, error_message: str | None = None
    ) -> None:
        """Обновление статуса обработки изображения"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status == ImageStatus.ERROR:
                cursor.execute(
                    """
                    UPDATE processed_images 
                    SET status = ?, error_message = ?, processed_at = datetime('now')
                    WHERE file_hash = ?
                """,
                    (status.value, error_message, file_hash),
                )
            else:
                cursor.execute(
                    """
                    UPDATE processed_images 
                    SET status = ?, processed_at = datetime('now')
                    WHERE file_hash = ?
                """,
                    (status.value, file_hash),
                )

            if cursor.rowcount == 0:
                raise ImageNotFoundError(f"Изображение с хешем {file_hash} не найдено")
            conn.commit()

    def get_file_hash(self, file_path: str | Path) -> str:
        """Получение хеша по file_path."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT file_hash FROM processed_images WHERE original_path = ?",
                (str(file_path),),
            )
            result = cursor.fetchone()

            if result is None:
                raise ImageNotFoundError(f"Hash не найден для файла: {file_path}")

            return result[0]

    def get_image_path(self, file_hash: str) -> dict:
        """Получение original_path по file_hash."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT original_path FROM processed_images WHERE file_hash = ?",
                (file_hash,),
            )
            result = cursor.fetchone()

            if not result:
                raise ImageNotFoundError(f"Изображение с хешем {file_hash} не найдено")

        return {"original_path": result[0]}

    def get_image_status(self, file_hash: str) -> ImageStatus | None:
        """Проверка статуса."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status FROM processed_images WHERE file_hash = ?", (file_hash,)
            )
            result = cursor.fetchone()

            if not result:
                return None

            return ImageStatus(result[0])

    def process_image(self, file_path: Path) -> str:
        """Обработка фотографии и сохранение информации в базу данных."""
        file_hash = self.create_file_hash(file_path)
        if self.get_image_status(file_hash) == ImageStatus.SUCCESS:
            return file_hash

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO processed_images 
                (original_path, file_hash, status, created_at)
                VALUES (?, ?, ?, datetime('now'))
            """,
                (str(file_path), file_hash, ImageStatus.SUCCESS.value),
            )
            conn.commit()

        return file_hash

    def delete_image(self, file_hash: str) -> None:
        """Удаление изображения из БД"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM processed_images WHERE file_hash = ?", (file_hash,)
            )
            if cursor.rowcount == 0:
                raise ImageNotFoundError(f"Изображение с хешем {file_hash} не найдено")
            conn.commit()

    def get_random_image(self) -> dict | None:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT original_path, file_hash, status, created_at, processed_at
                    FROM processed_images 
                    WHERE status = ?
                    ORDER BY RANDOM() 
                    LIMIT 1
                """,
                    (ImageStatus.SUCCESS.value,),
                )

                result = cursor.fetchone()
                if not result:
                    return None

                return {
                    "original_path": result[0],
                    "file_hash": result[1],
                    "status": result[2],
                    "created_at": result[3],
                    "processed_at": result[4],
                }

        except sqlite3.Error as e:
            raise DatabaseError(f"Ошибка при получении случайной фотографии: {str(e)}")
