import os
import re
import sys
import asyncio
import tempfile
import shutil
import threading
import traceback
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def run_ping():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Ping).serve_forever()


threading.Thread(target=run_ping, daemon=True).start()

try:
    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import CommandStart
    from aiogram.types import Message, FSInputFile
    import yt_dlp

    TOKEN = os.environ.get("BOT_TOKEN", "").strip()
    print("TOKEN length:", len(TOKEN), "has colon:", ":" in TOKEN, flush=True)
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is empty or missing")

    MAX_MB = 49
    bot = Bot(TOKEN)
    dp = Dispatcher()

    URL_RE = re.compile(r"https?://\S+")
    SUPPORTED = ("youtube.com", "youtu.be", "tiktok.com", "facebook.com",
                 "fb.watch", "fb.com", "xiaohongshu.com", "xhslink.com", "rednote")

    def download(url, folder):
        opts = {
            "outtmpl": os.path.join(folder, "%(id)s.%(ext)s"),
            "format": f"best[filesize<{MAX_MB}M]/best[height<=480]/best",
            "noplaylist": True,
            "quiet": True,
            "max_filesize": MAX_MB * 1024 * 1024,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    @dp.message(CommandStart())
    async def start(m: Message):
        await m.answer("👋 YouTube / TikTok / Facebook / RedNote link ပို့ပေးပါ၊ video ဒေါင်းပေးပါမယ်။")

    @dp.message(F.text)
    async def handle(m: Message):
        match = URL_RE.search(m.text or "")
        if not match:
            await m.answer("Link တစ်ခု ပို့ပေးပါ 🔗")
            return
        url = match.group(0)
        if not any(s in url for s in SUPPORTED):
            await m.answer("ဒီ site ကို မထောက်ပံ့သေးပါဘူး 😅")
            return
        status = await m.answer("⏳ ဒေါင်းနေပါတယ်...")
        folder = tempfile.mkdtemp()
        try:
            path = await asyncio.to_thread(download, url, folder)
            if os.path.getsize(path) > MAX_MB * 1024 * 1024:
                await status.edit_text("❌ Video က 50MB ထက်ကြီးပါတယ်")
                return
            await m.answer_video(FSInputFile(path))
            await status.delete()
        except Exception as e:
            await status.edit_text(f"❌ မအောင်မြင်ပါ: {str(e)[:150]}")
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    async def main():
        print("Starting polling...", flush=True)
        await dp.start_polling(bot)

    asyncio.run(main())

except BaseException:
    print("=== BOT CRASHED ===", flush=True)
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    time.sleep(600)
