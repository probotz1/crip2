
import os
import time
import math
import subprocess
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import BOT_TOKEN, API_ID, API_HASH, DATABASE_URL
from motor.motor_asyncio import AsyncIOMotorClient

# Initialize your Pyrogram client
app = Client(
    "stream_remover_bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

# MongoDB connection
mongo_client = AsyncIOMotorClient(DATABASE_URL)
db = mongo_client["stream_remover_db"]
collection = db["videos"]

# Directory for storing downloaded files
DOWNLOADS_DIR = "downloads"

# Ensure the downloads directory exists
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

PROGRESS_TEMPLATE = """
Progress: {0}%
Downloaded: {1} / {2}
Speed: {3}/s
ETA: {4}
"""

# Dictionary to store the last update time for each message
last_update_time = {}

async def progress_callback(current, total, message, start_time):
    now = time.time()
    elapsed_time = now - start_time
    if elapsed_time == 0:
        elapsed_time = 1  # Avoid division by zero

    speed = current / elapsed_time
    percentage = current * 100 / total
    eta = (total - current) / speed

    progress_str = "[{0}{1}]".format(
        ''.join(["⬢" for _ in range(math.floor(percentage / 10))]),
        ''.join(["⬡" for _ in range(10 - math.floor(percentage / 10))])
    )
    tmp = progress_str + PROGRESS_TEMPLATE.format(
        round(percentage, 2),
        human_readable_size(current),
        human_readable_size(total),
        human_readable_size(speed),
        time_formatter(eta)
    )

    # Throttle updates to every 10 seconds
    message_id = message.id  # Changed from message.message_id to message.id
    if message_id not in last_update_time or (now - last_update_time[message_id]) > 10:
        try:
            await message.edit(
                text=tmp,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Owner", url='https://t.me/atxbots')]]
                )
            )
            last_update_time[message_id] = now
        except Exception as e:
            print(f"Error updating progress: {e}")

def human_readable_size(size):
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

def time_formatter(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    time_str = ((f"{days}d, " if days else "") +
                (f"{hours}h, " if hours else "") +
                (f"{minutes}m, " if minutes else "") +
                (f"{seconds}s, " if seconds else ""))
    return time_str.strip(', ')

@app.on_message(filters.command("start"))
async def start_command(bot, message: Message):
    welcome_text = (
        "Hello! I am the Stream Remover Bot.\n\n"
        "I can help you remove audio and subtitles from video files.\n\n"
        "To use me, simply forward a video to this chat, and I will process it for you.\n\n"
        "Owner: [@atxbots](https://t.me/atxbots)"
    )
    await message.reply(welcome_text, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.video & filters.forwarded)
async def process_forwarded_video(bot, message: Message):
    try:
        ms = await message.reply("Processing video...")

        file_info = message.video
        file_id = file_info.file_id
        file_path = os.path.join(DOWNLOADS_DIR, f"{file_id}.mp4")

        # Download the video file
        await bot.download_media(message, file_path, progress=progress_callback, progress_args=(ms, time.time()))

        # Verify the file is completely downloaded by checking file size
        if not os.path.exists(file_path) or os.path.getsize(file_path) != file_info.file_size:
            await ms.edit("Download failed or file is incomplete.")
            return

        start_time = time.time()
        output_filename = os.path.join(DOWNLOADS_DIR, f"processed_{file_id}.mp4")

        # Run ffmpeg command to remove audio and subtitles
        ffmpeg_cmd = [
            'ffmpeg', '-i', file_path,
            '-c:v', 'copy', '-an', '-sn',
            output_filename
        ]
        print("FFmpeg command:", " ".join(ffmpeg_cmd))  # Print the command for debugging
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("FFmpeg error output:", result.stderr)
            await ms.edit(f"Error processing video with FFmpeg: {result.stderr}")
            return

        processing_time = time.time() - start_time
        processed_size = os.path.getsize(output_filename)

        # Send the processed video
        await bot.send_document(
            chat_id=message.chat.id,
            document=output_filename,
            caption=f"Processed video\nSize: {human_readable_size(processed_size)}\nProcessing Time: {time_formatter(processing_time)}"
        )

        # Save to MongoDB
        video_data = {
            "file_id": file_id,
            "original_size": file_info.file_size,
            "processed_size": processed_size,
            "processing_time": processing_time,
            "timestamp": start_time
        }
        await collection.insert_one(video_data)

        # Clean up - remove original and processed files
        os.remove(file_path)
        os.remove(output_filename)

    except subprocess.CalledProcessError as e:
        await ms.edit(f"Error processing video: {e}")

    except Exception as e:
        await ms.edit(f"An error occurred: {e}")

if __name__ == "__main__":
    app.run()
