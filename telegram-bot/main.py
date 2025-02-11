import os
import aiohttp
import base64

from telegram import (
    Update,
)
from dotenv import load_dotenv
from typing import Callable
from functools import wraps
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from pathlib import Path

load_dotenv()

RANDOM_IMAGE_ROUTE = "random-image"


def handle_error(error_message: str = "Произошла ошибка: {error}"):

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            try:
                return await func(self, update, context, *args, **kwargs)

            except aiohttp.ClientError as e:
                if update.message:
                    await update.message.reply_text(
                        "❌ Ошибка соединения с сервером: " + str(e)
                    )
                elif update.callback_query:
                    await update.callback_query.answer(
                        "❌ Ошибка соединения с сервером"
                    )

            except ValueError as e:
                if update.message:
                    await update.message.reply_text(f"❌ {str(e)}")

            except Exception as e:
                if update.message:
                    await update.message.reply_text(error_message.format(error=str(e)))

            return None

        return wrapper

    return decorator


class Config:
    def __init__(self):
        load_dotenv()
        self.SERVER_PORT = int(os.getenv("SERVER_PORT", 5001))
        self.SERVER_HOST = os.getenv("SERVER_HOST", "http://127.0.0.1")
        self.SERVER_PATH = f"{self.SERVER_HOST}:{self.SERVER_PORT}"
        self.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
        self.UPLOAD_DIR = Path(os.getenv("ORIGINALS_PATH", "../originals"))
        self.UPLOAD_DIR.mkdir(exist_ok=True)


class ImageAPIClient:
    def __init__(self, server_path: str):
        self.server_path = server_path

    async def get_random_image(self) -> tuple[bytes, str]:
        """Получение случайного изображения"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.server_path}/{RANDOM_IMAGE_ROUTE}"
            ) as response:
                if response.status != 200:
                    error_data = await response.json()
                    raise ValueError(
                        f"Не удалось получить изображение: {error_data.get('message', 'Неизвестная ошибка')}"
                    )

                response_json = await response.json()
                image_base64 = response_json.get("image")
                image_data = base64.b64decode(image_base64)
                file_hash = str(response_json.get("file_hash"))
                return image_data, file_hash

    async def delete_image(self, file_hash: str) -> bool:
        """Удаление изображения"""
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self.server_path}/images/{file_hash}"
            ) as response:
                return response.status in (200, 204)


class ImageBot:
    def __init__(self, config: Config):
        self.config = config
        self.api_client = ImageAPIClient(config.SERVER_PATH)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        if update.message:
            await update.message.reply_text(
                "Отправь мне фотку и я буду показывать ее в рамочке.\n"
                "/random - получить случайную фотку\n"
                "/delete <id> - удалить фото\n"
            )

    # TODO: опираясь на статус отдавать id после обработки?
    @handle_error()
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик входящих фотографий"""
        if not update.message or not update.message.photo:
            return

        image = update.message.photo[-1]
        file = await context.bot.get_file(image.file_id)
        file_path = self.config.UPLOAD_DIR / f"{image.file_id}.jpg"

        if file_path.exists():
            await update.message.reply_text("❌ Такое фото уже есть!")
            return

        await file.download_to_drive(file_path)
        await update.message.reply_text("✅ Получил!")

    @handle_error()
    async def random_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /random"""
        if not update.message:
            return

        try:
            image_data, file_hash = await self.api_client.get_random_image()
            await update.message.reply_photo(photo=image_data)
            await update.message.reply_text(
                "🎲 Вот случайная фотка, её id...\n"
                "Напиши /delete <id> чтобы удалить её"
            )
            await update.message.reply_text(file_hash)
        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")

    @handle_error()
    async def delete_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /delete"""
        if not update.message:
            return

        if not context.args:
            await update.message.reply_text("❌ Вставь id фотки которую удалить хочешь")
            return

        file_hash = context.args[0]
        success = await self.api_client.delete_image(file_hash)

        if success:
            await update.message.reply_text("✅ Фотка удалена!")
        else:
            await update.message.reply_text("❌ Что-то пошло не так")

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(self.config.TELEGRAM_TOKEN).build()

        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("random", self.random_command))
        application.add_handler(CommandHandler("delete", self.delete_command))
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))

        application.run_polling()


def main():
    config = Config()
    bot = ImageBot(config)
    bot.run()


if __name__ == "__main__":
    main()
