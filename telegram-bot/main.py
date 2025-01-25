import os
import aiohttp
import base64
import hashlib
import time

from telegram import (
    Update,
)
from dotenv import load_dotenv
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


SERVER_PORT = int(os.getenv("SERVER_PORT", 5001))
SERVER_HOST = os.getenv("SERVER_HOST", "http://127.0.0.1")


SERVER_PATH = f"{SERVER_HOST}:{SERVER_PORT}"

RANDOM_IMAGE_ROUTE = "random-image"


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


UPLOAD_DIR = os.getenv("ORIGINALS_PATH", "../originals")


Path(UPLOAD_DIR).mkdir(exist_ok=True)


def handle_error():
    def decorator(func):
        @wraps(func)
        async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            try:
                return await func(update, context, *args, **kwargs)
            except aiohttp.ClientError as e:
                if update.message is not None:
                    await update.message.reply_text(
                        f"❌ Ошибка соединения с сервером: {str(e)}"
                    )
                elif update.callback_query is not None:
                    await update.callback_query.answer(
                        f"❌ Ошибка соединения с сервером"
                    )
            except Exception as e:
                if update.message is not None:
                    await update.message.reply_text(f"❌ Ошибка: {str(e)}")

        return wrapper

    return decorator


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is not None:
        await update.message.reply_text(
            "Отправь мне фотку и я буду показывать ее в рамочке.\n"
            "/random - получить случайную фотку\n",
            "/delete <id> - удалить фото\n",
        )


# TODO: опираясь на статус отдавать id после обработки?
@handle_error()
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is not None:
        image = update.message.photo[-1]

        # Скачиваем фото
        file = await context.bot.get_file(image.file_id)
        file_path = Path(UPLOAD_DIR) / f"{image.file_id}.jpg"
        if file_path.exists():
            await update.message.reply_text("❌ Такое фото уже есть!")
            return

        await file.download_to_drive(file_path)
        if update.message is None:
            raise

        await update.message.reply_text(f"✅ Получил!")


@handle_error()
async def get_random_image(update: Update, context: ContextTypes.DEFAULT_TYPE):

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{SERVER_PATH}/{RANDOM_IMAGE_ROUTE}",
        ) as response:
            if response.status == 200 and update.message is not None:
                response_json = await response.json()
                image_base64 = response_json.get("image")
                image_data = base64.b64decode(image_base64)
                file_hash = str(response_json.get("file_hash"))

                await update.message.reply_photo(photo=image_data)
                await update.message.reply_text(
                    "🎲 Вот случайная фотка, её id...\nНапиши /delete <id> чтобы удалить её",
                )
                await update.message.reply_text(
                    file_hash,
                )

            elif update.message is not None:
                error_data = await response.json()
                await update.message.reply_text(
                    f"❌ Не удалось получить изображение: {error_data.get('message', 'Неизвестная ошибка')}"
                )


async def delete_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is not None:
        async with aiohttp.ClientSession() as session:

            # context.args содержит список аргументов после команды
            if not context.args:
                await update.message.reply_text(
                    f"❌ Вставь id фотки которую удалить хочешь"
                )
                return

            file_hash = context.args[0]

            async with session.delete(
                f"{SERVER_PATH}/images/{file_hash}",
            ) as response:
                if response.status in (200, 204):
                    await update.message.reply_text(text="✅ Фотка удалена!")
                else:
                    await update.message.reply_text(text="❌ Что-то пошло не так")


def run_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("random", get_random_image))
    application.add_handler(CommandHandler("delete", delete_image))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))

    application.run_polling()


if __name__ == "__main__":
    run_bot()
