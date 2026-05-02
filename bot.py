import os
import uuid
import subprocess
import logging
import imageio_ffmpeg
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Отправь мне видео, и я пересоздам его с новыми метаданными.\n\n"
        "📹 Просто прикрепи файл — и получишь его обратно с уникальным хешем."
    )


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    file_obj = None
    if message.video:
        file_obj = message.video
    elif message.document and message.document.mime_type and "video" in message.document.mime_type:
        file_obj = message.document
    else:
        await message.reply_text("❌ Пожалуйста, отправь видеофайл.")
        return

    if file_obj.file_size and file_obj.file_size > 50 * 1024 * 1024:
        await message.reply_text("❌ Файл слишком большой. Максимум 50 МБ.")
        return

    await message.reply_text("⏳ Обрабатываю видео, подожди...")

    uid = uuid.uuid4().hex
    input_path = f"/tmp/input_{uid}.mp4"
    output_path = f"/tmp/output_{uid}.mp4"

    try:
        await message.reply_text("📥 Скачиваю файл...")
        tg_file = await context.bot.get_file(file_obj.file_id)
        await tg_file.download_to_drive(input_path)
        await message.reply_text("✅ Файл скачан, запускаю FFmpeg...")

        cmd = [
             FFMPEG_PATH, "-y",
            "-i", input_path,
            "-c:v", "libx264",
            "-crf", "28",
            "-preset", "fast",
            "-c:a", "aac",
            "-metadata", f"comment={uuid.uuid4()}",
            "-metadata", f"title={uuid.uuid4()}",
            "-metadata", "encoder=",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        await message.reply_text(f"FFmpeg код: {result.returncode}\n{result.stderr[-500:] if result.stderr else 'нет ошибок'}")

        if result.returncode != 0:
            return

        await message.reply_text("📤 Отправляю файл...")
        with open(output_path, "rb") as f:
            await message.reply_document(
                document=f,
                filename=f"reels_{uid[:8]}.mp4",
                caption="✅ Готово!"
            )

    except Exception as e:
        await message.reply_text(f"❌ Ошибка: {type(e).__name__}: {e}")
    finally:
        for path in [input_path, output_path]:
            if os.path.exists(path):
                os.remove(path)


def main():
    from telegram.request import HTTPXRequest
request = HTTPXRequest(read_timeout=120, write_timeout=120, connect_timeout=60)
app = ApplicationBuilder().token(TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    print("🤖 Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
