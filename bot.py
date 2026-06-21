import os
import asyncio
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# ضع التوكن الجديد هنا بعد ما تجدده من BotFather
BOT_TOKEN = "ضع_التوكن_الجديد_هنا"

# ==================== رسالة الترحيب ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📖 كيفية الاستخدام", callback_data="help")],
        [InlineKeyboardButton("📡 المنصات المدعومة", callback_data="platforms")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 أهلاً وسهلاً!\n"
        "أنا بوت *علاء للتحميل* 🚀\n\n"
        "📌 فقط أرسل لي أي رابط وسأحمّله لك فوراً!\n\n"
        "اختر من القائمة أدناه 👇",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ==================== أزرار التفاعل ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        await query.edit_message_text(
            "📖 *كيفية الاستخدام:*\n\n"
            "1️⃣ انسخ رابط الفيديو أو الصورة\n"
            "2️⃣ الصقه هنا وأرسله\n"
            "3️⃣ انتظر قليلاً وسيصلك المحتوى ✅\n\n"
            "⚠️ الحد الأقصى لحجم الملف: 50MB",
            parse_mode="Markdown"
        )
    elif query.data == "platforms":
        await query.edit_message_text(
            "📡 *المنصات المدعومة:*\n\n"
            "🎥 يوتيوب\n"
            "📸 إنستغرام (ريلز، صور، ستوري)\n"
            "🎵 تيك توك\n"
            "🐦 تويتر / X\n"
            "👍 فيسبوك\n"
            "🎬 Vimeo\n"
            "🎮 Twitch\n"
            "وغيرها الكثير...",
            parse_mode="Markdown"
        )

# ==================== التحميل الرئيسي ====================
async def download_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    # التحقق من أن الرسالة رابط
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("❌ الرجاء إرسال رابط صحيح يبدأ بـ http أو https")
        return

    msg = await update.message.reply_text("⏳ جاري تحليل الرابط...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:

            # إعدادات التحميل
            ydl_opts = {
                'outtmpl': f'{tmpdir}/%(title).50s.%(ext)s',
                'format': 'best[filesize<50M]/bestvideo[filesize<50M]+bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4',
            }

            await msg.edit_text("📥 جاري التحميل... قد يستغرق بعض الوقت")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # تصحيح امتداد الملف إذا كان mp4
                if not os.path.exists(filename):
                    filename = filename.rsplit('.', 1)[0] + '.mp4'

                title = info.get('title', 'المحتوى')
                duration = info.get('duration', 0)
                uploader = info.get('uploader', '')

            # التحقق من وجود الملف
            if not os.path.exists(filename):
                await msg.edit_text("❌ فشل التحميل، جرب رابطاً آخر")
                return

            file_size = os.path.getsize(filename)

            # التحقق من الحجم (50MB حد تيليغرام)
            if file_size > 50 * 1024 * 1024:
                await msg.edit_text(
                    "❌ حجم الملف أكبر من 50MB\n"
                    "تيليغرام لا يسمح بإرسال ملفات أكبر من ذلك"
                )
                return

            await msg.edit_text("📤 جاري الإرسال...")

            caption = f"✅ *{title}*"
            if uploader:
                caption += f"\n👤 {uploader}"
            if duration:
                mins = int(duration) // 60
                secs = int(duration) % 60
                caption += f"\n⏱ {mins}:{secs:02d}"

            # إرسال الملف
            ext = filename.split('.')[-1].lower()
            with open(filename, 'rb') as f:
                if ext in ['mp4', 'mkv', 'avi', 'mov', 'webm']:
                    await update.message.reply_video(
                        video=f,
                        caption=caption,
                        parse_mode="Markdown",
                        supports_streaming=True
                    )
                elif ext in ['mp3', 'm4a', 'ogg', 'wav']:
                    await update.message.reply_audio(
                        audio=f,
                        caption=caption,
                        parse_mode="Markdown"
                    )
                elif ext in ['jpg', 'jpeg', 'png', 'webp']:
                    await update.message.reply_photo(
                        photo=f,
                        caption=caption,
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_document(
                        document=f,
                        caption=caption,
                        parse_mode="Markdown"
                    )

            await msg.delete()

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Private" in error_msg or "private" in error_msg:
            await msg.edit_text("🔒 هذا المحتوى خاص ولا يمكن تحميله")
        elif "not available" in error_msg:
            await msg.edit_text("❌ المحتوى غير متاح أو محذوف")
        else:
            await msg.edit_text(f"❌ فشل التحميل\nتأكد من صحة الرابط وأن المحتوى عام")
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ غير متوقع\nحاول مرة أخرى لاحقاً")
        print(f"Error: {e}")

# ==================== تشغيل البوت ====================
def main():
    print("✅ بوت علاء للتحميل يعمل الآن...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_content))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
