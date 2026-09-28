"""
AgriVision - Telegram Bot Interface
Handles farmer interactions, image processing, AI analysis, follow-up Q&A, and PDF reports.
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

from telegram import Update, constants
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import database
import ai_analyzer
import report_generator

load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("AgriVisionBot")


def get_telegram_token() -> Optional[str]:
    """Retrieves the Telegram bot token from secrets/env."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token and token != "your-telegram-bot-token-here":
        return token

    # Check .streamlit/secrets.toml
    secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            import toml
            secrets = toml.load(secrets_path)
            tok = secrets.get("TELEGRAM_BOT_TOKEN")
            if tok and tok != "your-telegram-bot-token-here":
                return tok
        except Exception:
            pass

    return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    first_name = user.first_name if user else "Farmer"
    
    welcome_msg = f"""🌿 *Welcome to AgriVision, {first_name}!*

AgriVision is an AI-powered agricultural damage detection, quantification, and reporting assistant.

📸 *How it works:*
1. Send a clear photo of your crop or field.
2. AI examines visible symptoms (disease, pest, animal, flood, weather damage).
3. Receive an instant visual damage assessment and recommended next steps.
4. Ask follow-up questions directly or download a PDF report!

📋 *Available Commands:*
/analyze — Instructions to submit an image
/history — View your recent crop assessments
/report — Get the full report & PDF for your latest photo
/help — Guide on how to get the most accurate results

Send me a photo now to begin! 🌱"""

    await update.message.reply_text(welcome_msg, parse_mode=constants.ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command."""
    help_msg = """📖 *AgriVision Guide & Best Practices*

*How to take effective crop photos:*
• ☀️ *Lighting:* Capture in good natural daylight (avoid heavy glare/shadows).
• 🔍 *Focus:* Take a sharp close-up of the affected leaves, stems, or fruits.
• 📐 *Context:* Include both damaged parts and healthy nearby tissue for contrast.
• 🚫 *Avoid:* Blurry, dark, or extremely distant aerial shots.

*Follow-up Questions you can ask:*
After sending a photo, simply type your question, such as:
• _"What is the possible problem?"_
• _"How severe is this damage?"_
• _"What should I inspect next in my field?"_
• _"Will this spread to neighboring crops?"_

*Commands:*
/analyze — Start a new crop image analysis
/history — View your past inspection logs
/report — Download PDF report of the last analysis
/start — Re-introduce AgriVision"""

    await update.message.reply_text(help_msg, parse_mode=constants.ParseMode.MARKDOWN)


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /analyze command."""
    msg = """📷 *Ready for Crop Analysis!*

Please tap the 📎 attachment icon and send a clear photograph of your crop or field.

AgriVision will examine:
• Disease & fungal leaf spots
• Pest defoliation & insect damage
• Wild animal trampling/grazing
• Weather, hail & flood waterlogging
• Estimated damage severity & affected zones"""

    await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /history command."""
    user_id = str(update.effective_user.id)
    history = database.get_user_history(user_id, limit=5)

    if not history:
        await update.message.reply_text(
            "📭 You have no previous crop analyses on record. Send a crop photograph to start!",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    lines = ["📋 *Your Recent AgriVision Analyses:*", ""]
    for i, item in enumerate(history, 1):
        lines.append(report_generator.format_history_item(item, i))

    lines.append("\n_Type /report to download the latest assessment report as a PDF._")
    await update.message.reply_text("\n".join(lines), parse_mode=constants.ParseMode.MARKDOWN)


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /report command: sends text summary and generated PDF."""
    user_id = str(update.effective_user.id)
    latest = database.get_latest_analysis_for_user(user_id)

    if not latest:
        await update.message.reply_text(
            "⚠️ No analysis found. Please send a crop photo first!",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    await update.message.reply_chat_action(constants.ChatAction.TYPING)

    # Format text report
    text_report = report_generator.format_telegram_report(latest)
    await update.message.reply_text(text_report, parse_mode=constants.ParseMode.MARKDOWN)

    # Generate and send PDF
    try:
        await update.message.reply_chat_action(constants.ChatAction.UPLOAD_DOCUMENT)
        pdf_filename = f"AgriVision_Report_{latest['id']}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"
        pdf_path = os.path.join(database.UPLOADS_DIR, pdf_filename)
        
        report_generator.generate_pdf_report(
            data=latest,
            output_pdf_path=pdf_path,
            image_path=latest.get("image_path")
        )

        with open(pdf_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=pdf_filename,
                caption=f"📄 Official AgriVision Assessment Report (ID: #{latest['id']})"
            )
    except Exception as e:
        logger.error(f"Error generating PDF for user {user_id}: {e}")
        await update.message.reply_text("ℹ️ Text report sent. (PDF generation encountered an error).")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming crop images for AI vision analysis."""
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or user.first_name or "Anonymous"
    chat_id = str(update.effective_chat.id)

    # Send status
    status_msg = await update.message.reply_text(
        "⏳ *Analyzing crop image with Gemini Vision...*\nPlease wait a moment.",
        parse_mode=constants.ParseMode.MARKDOWN
    )
    await update.message.reply_chat_action(constants.ChatAction.TYPING)

    try:
        # Download highest resolution photo
        photo_obj = update.message.photo[-1]
        tg_file = await photo_obj.get_file()
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_filename = f"crop_{user_id}_{timestamp_str}.jpg"
        local_filepath = os.path.join(database.UPLOADS_DIR, local_filename)
        
        await tg_file.download_to_drive(local_filepath)

        # Run Gemini Vision analysis
        analysis_result = ai_analyzer.analyze_crop_image(local_filepath)

        # Save to SQLite database
        analysis_id = database.save_analysis(
            data=analysis_result,
            image_path=local_filepath,
            telegram_user_id=user_id,
            telegram_chat_id=chat_id,
            username=username,
            source="telegram"
        )
        analysis_result["id"] = analysis_id

        # Format and send response
        reply_text = report_generator.format_telegram_report(analysis_result)
        
        followup_hint = "\n\n💡 *Tip:* Ask any follow-up question (e.g., _\"How severe is this?\"_) or type /report for a PDF download."
        
        # Delete or edit loading status
        try:
            await status_msg.delete()
        except Exception:
            pass

        await update.message.reply_text(reply_text + followup_hint, parse_mode=constants.ParseMode.MARKDOWN)

    except ValueError as val_err:
        logger.error(f"Configuration or validation error: {val_err}")
        await status_msg.edit_text(
            f"⚠️ *Configuration Notice:*\n{str(val_err)}\n\nPlease ensure `GEMINI_API_KEY` is configured.",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error analyzing photo: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ *Analysis Error:*\nFailed to process image. Reason: {str(e)}\n\nPlease try sending a clearer image or try again shortly.",
            parse_mode=constants.ParseMode.MARKDOWN
        )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text follow-ups from the farmer regarding the latest crop analysis."""
    user = update.effective_user
    user_id = str(user.id)
    user_text = update.message.text.strip()

    # Retrieve user's latest analysis context
    latest = database.get_latest_analysis_for_user(user_id)

    if not latest:
        await update.message.reply_text(
            "🌱 Please send a photo of your crop first, or type /help for instructions!",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    await update.message.reply_chat_action(constants.ChatAction.TYPING)

    # Save user message
    database.save_chat_message(latest["id"], user_id, "user", user_text)

    # Fetch recent chat context
    chat_history = database.get_chat_history_for_analysis(latest["id"], limit=6)

    # Generate answer using Gemini
    answer = ai_analyzer.answer_follow_up(
        analysis_context=latest,
        user_question=user_text,
        chat_history=chat_history
    )

    # Save assistant answer
    database.save_chat_message(latest["id"], user_id, "assistant", answer)

    await update.message.reply_text(
        f"🌾 *AgriVision Assistant:*\n\n{answer}",
        parse_mode=constants.ParseMode.MARKDOWN
    )


def run_telegram_bot():
    """Initializes and runs the Telegram Bot polling loop."""
    token = get_telegram_token()
    if not token or token == "your-telegram-bot-token-here":
        print("[!] Error: TELEGRAM_BOT_TOKEN is not set.")
        print("    Please set TELEGRAM_BOT_TOKEN in .streamlit/secrets.toml or .env")
        return

    # Initialize Database
    database.init_db()

    print("[*] Starting AgriVision Telegram Bot...")
    app = ApplicationBuilder().token(token).build()

    # Register Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("report", report_command))

    # Register Media & Message Handlers
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    print("[+] AgriVision Telegram Bot is active and listening for messages!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_telegram_bot()
