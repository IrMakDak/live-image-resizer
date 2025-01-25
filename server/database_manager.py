import os
import requests
import sqlite3
import hashlib

from pathlib import Path

SERVER_PORT = int(os.getenv("SERVER_PORT", 5001))
SERVER_HOST = os.getenv("SERVER_HOST")


SERVER_PATH = f"{SERVER_HOST}:{SERVER_PORT}"

# TODO: SQLAlchemy?


class DatabaseManager:
    def __init__(self, db_path="image_processing.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT UNIQUE,
                file_hash TEXT UNIQUE,
                status TEXT,
                created_at TIMESTAMP,
                processed_at TIMESTAMP,
                error_message TEXT
            )
        """
        )
        conn.commit()
        conn.close()

    def create_file_hash(self, file_path: Path):
        """Создание хеша файла для уникальной идентификации."""
        try:
            print("right path:", file_path)
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            print(file_hash, "file_hash2!")
            return file_hash
        except Exception as e:
            print(f"Неожиданная ошибка при создании хэша {file_path.name}: {str(e)}")

    def get_file_hash(self, file_path):
        """Получение хеша по file_path."""
        try:
            print("get_file_hash")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT file_hash FROM processed_images WHERE original_path = ?",
                (file_path,),
            )
            result = cursor.fetchone()
            conn.close()

            print(result, "result!!!")

            if result is None:
                raise ValueError(f"Hash не найден для файла: {file_path}")

            return result[0]  # Возвращаем первый элемент кортежа (hash)

        except sqlite3.Error as e:
            raise ValueError(f"Ошибка базы данных: {str(e)}")
        finally:
            if "conn" in locals() and conn:
                conn.close()

    def get_image_path(self, file_hash):
        """Получение original_path по file_hash."""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT original_path FROM processed_images WHERE file_hash = ?",
            (file_hash,),
        )
        result = cursor.fetchone()
        conn.close()

        return {"original_path": result[0]}

    def is_photo_processed(self, file_hash):
        """Проверка, была ли фотография уже обработана."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Добавим проверку содержимого таблицы

        cursor.execute(
            "SELECT id FROM processed_images WHERE file_hash = ?", (file_hash,)
        )
        result = cursor.fetchone()
        conn.close()

        return result is not None

    def process_image(self, file_path: Path):
        """Обработка фотографии и сохранение информации в базу данных."""
        try:
            file_hash = self.create_file_hash(file_path)

            # Проверяем, не была ли фотография уже обработана
            if self.is_photo_processed(file_hash):
                print(f"Файл {file_path.name} уже обработан")
                return

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Сначала добавляем новую запись
            cursor.execute(
                """
                INSERT INTO processed_images 
                (original_path, file_hash, status, created_at)
                VALUES (?, ?, ?, datetime('now'))
                """,
                (str(file_path), file_hash, "success"),
            )
            conn.commit()

            conn.close()
            print(f"Фото добавлено в БД")

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при отправке запроса: {str(e)}")
        except Exception as e:
            print(f"Неожиданная ошибка при обработке {file_path.name}: {str(e)}")

    def delete_image(self, file_hash):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Проверяем существование записи
            cursor.execute(
                "SELECT original_path, status FROM processed_images WHERE file_hash = ?",
                (file_hash,),
            )
            result = cursor.fetchone()
            print("Я тут", result)
            if not result:
                raise ValueError("Image not found in database")

            # Удаляем из БД
            cursor.execute(
                "DELETE FROM processed_images WHERE file_hash = ?", (file_hash,)
            )

            conn.commit()

            print(f"Удален файл")

        except Exception as e:
            raise ValueError(f"Error deleting image: {str(e)}")
        finally:
            conn.close()

    def get_random_image(self):
        """Получение случайной фотографии из базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT original_path, file_hash 
                FROM processed_images 
                ORDER BY RANDOM() 
                LIMIT 1
                """
            )
            result = cursor.fetchone()

            if not result:
                print("В базе данных нет фотографий")
                return None

            return {"original_path": result[0], "file_hash": result[1]}
        except Exception as e:
            print(f"Ошибка при получении случайной фотографии: {str(e)}")
            return None
        finally:
            conn.close()
