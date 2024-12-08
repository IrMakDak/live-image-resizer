import aiohttp

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from pathlib import Path

SERVER_PORT = 5000
PROCESS_IMAGE_HOST = "http://127.0.0.1"
PROCESS_IMAGE_ROUTE = "/process_image"
RANDOM_IMAGE_ROUTE = "/random_image"
# TELEGRAM_TOKEN = "мой_токен"
UPLOAD_DIR = "../originals"  # Папка для хранения оригиналов

Path(UPLOAD_DIR).mkdir(exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь мне фотографию, и я сохраню её в папку resized с новым размером.\n"
        "Используй /random чтобы получить случайное обработанное изображение."
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]  # Берём самое большое разрешение

    try:
        # Скачиваем фото
        file = await context.bot.get_file(photo.file_id)
        file_path = Path(UPLOAD_DIR) / f"{photo.file_id}.jpg"

        await file.download_to_drive(file_path)

        await update.message.reply_text(f"✅ Фото загружено!\n{photo.file_id}")

    except aiohttp.ClientError as e:
        await update.message.reply_text(f"❌ Ошибка соединения с сервером: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def get_random_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получить и отправить случайное изображение
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PROCESS_IMAGE_HOST}:{SERVER_PORT}{RANDOM_IMAGE_ROUTE}",
            ) as response:
                if response.status == 200:
                    # Если получили изображение, отправляем его
                    image_data = await response.read()
                    await update.message.reply_photo(
                        photo=image_data, caption="🎲 Случайное изображение из галереи"
                    )
                else:
                    # Если получили ошибку, парсим JSON с ошибкой
                    error_data = await response.json()
                    await update.message.reply_text(
                        f"❌ Не удалось получить изображение: {error_data.get('message', 'Неизвестная ошибка')}"
                    )

    except aiohttp.ClientError as e:
        await update.message.reply_text(f"❌ Ошибка соединения с сервером: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


def run_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("random", get_random_image))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    application.run_polling()


if __name__ == "__main__":
    run_bot()
