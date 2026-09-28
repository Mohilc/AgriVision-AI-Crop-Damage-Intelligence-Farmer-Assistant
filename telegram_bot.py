"""
AgriVision - Telegram Bot Interface
Handles farmer interactions, multimodal image processing, text agronomic Q&A, and PDF reports.
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
    """Retrieves the Telegram bot token from env or secrets.toml."""
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token and len(token) > 15 and not token.startswith("your-"):
        return token

    # Check .streamlit/secrets.toml
    secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            import toml
            secrets = toml.load(secrets_path)
            tok = secrets.get("TELEGRAM_BOT_TOKEN")
            if tok and len(tok) > 15 and not tok.startswith("your-"):
                return tok
        except Exception:
            pass

    return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    first_name = user.first_name if user else "Farmer"
    
    welcome_msg = f"""🌿 *Welcome to AgriVision, {first_name}!*

AgriVision is your 24/7 AI-powered Agricultural Intelligence & Crop Health Assistant.

🌟 *How I can assist you:*
1. 📸 *Crop Image Analysis:* Send a clear photo of your plant or field. I will detect diseases, pest damage, weather stress, estimate damage severity %, and give recommended actions.
2. 💬 *Text Question & Answer:* Type *any* farming question (e.g., _"How to control aphids?"_, _"Best fertilizer for wheat"_, _"Yellow leaves remedy"_). I answer directly by text!
3. 📄 *Instant Reports:* Type /report to receive a structured assessment and official PDF report.

📋 *Quick Commands:*
/analyze — Instructions to submit crop photos
/history — View your previous field diagnoses
/report — Download PDF report of your latest scan
/help — Tips for best photo & question results

🌾 *Send me a crop photo or ask any farming question to begin!*"""

    await update.message.reply_text(welcome_msg, parse_mode=constants.ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command."""
    help_msg = """📖 *AgriVision Guide & Tips*

📸 *Taking Effective Crop Photos:*
• ☀️ *Lighting:* Natural daylight works best (avoid harsh flash or shadows).
• 🔍 *Focus:* Close-up of damaged leaves, stems, pods, or fruits.
• 📐 *Contrast:* Include both damaged and healthy areas if possible.

💬 *Asking Questions by Text:*
You don't need a photo to get agricultural advice! You can ask:
• _"What causes white powder on pumpkin leaves?"_
• _"How to manage stem borer in paddy without toxic chemicals?"_
• _"What are the best companion plants for tomato?"_
• _"How much water does maize need during flowering?"_

📋 *Commands:*
/analyze — Start photo diagnosis
/history — View your past inspection logs
/report — Download latest PDF assessment
/start — Re-introduce AgriVision"""

    await update.message.reply_text(help_msg, parse_mode=constants.ParseMode.MARKDOWN)


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /analyze command."""
    msg = """📷 *Ready for Crop Inspection!*

Please tap the 📎 attachment icon and send a photograph of your crop or field.

AgriVision AI examines:
• Fungal leaf spots, rusts, blights & virus marks
• Pest chewing, caterpillars & borer damage
• Animal trampling & structural loss
• Hail, flood waterlogging & heat stress
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
            "⚠️ No crop analysis found. Please send a crop photo first!",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    await update.message.reply_chat_action(constants.ChatAction.TYPING)

    # Format text report
    text_report = report_generator.format_telegram_report(latest)
    try:
        await update.message.reply_text(text_report, parse_mode=constants.ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text(text_report)

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
    """Handles incoming crop images for AI vision analysis with immediate feedback."""
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or user.first_name or "Anonymous"
    chat_id = str(update.effective_chat.id)

    # Report immediately that the bot is responding
    await update.message.reply_chat_action(constants.ChatAction.TYPING)
    status_msg = await update.message.reply_text(
        "📸 *AgriVision received your crop image!*\n⏳ *AI Vision is inspecting leaves, disease symptoms, pest damage, and severity...*",
        parse_mode=constants.ParseMode.MARKDOWN
    )

    try:
        # Download highest resolution photo
        photo_obj = update.message.photo[-1]
        tg_file = await photo_obj.get_file()
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_filename = f"crop_{user_id}_{timestamp_str}.jpg"
        local_filepath = os.path.join(database.UPLOADS_DIR, local_filename)
        
        await tg_file.download_to_drive(local_filepath)

        # Run AI Vision analysis
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

        # Format report
        reply_text = report_generator.format_telegram_report(analysis_result)
        followup_hint = "\n\n💡 *Tip:* Ask any follow-up question directly or type /report for a PDF download."

        # Remove temporary status message
        try:
            await status_msg.delete()
        except Exception:
            pass

        # Send full assessment
        try:
            await update.message.reply_text(reply_text + followup_hint, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(reply_text + followup_hint)

    except Exception as e:
        logger.error(f"Error analyzing photo: {e}", exc_info=True)
        try:
            await status_msg.edit_text(
                f"❌ *Analysis Notice:*\nCould not complete image analysis: {str(e)}\n\nPlease try sending another clear close-up photograph.",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        except Exception:
            await update.message.reply_text(f"Notice: Could not analyze image. {str(e)}")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles text inquiries from farmers.
    Answers both follow-up questions for previous images AND direct general agricultural questions!
    Reports immediate responding status so the user knows the bot is actively working.
    """
    user = update.effective_user
    user_id = str(user.id)
    user_text = update.message.text.strip()

    # Report immediately that the bot is responding
    await update.message.reply_chat_action(constants.ChatAction.TYPING)
    status_msg = await update.message.reply_text(
        "🌾 *AgriVision is analyzing your question...*",
        parse_mode=constants.ParseMode.MARKDOWN
    )

    try:
        # Check if the user has a recent crop analysis
        latest = database.get_latest_analysis_for_user(user_id)

        if latest:
            # Contextual follow-up grounded in the uploaded crop
            chat_history = database.get_chat_history_for_analysis(latest["id"], limit=6)
            answer = ai_analyzer.answer_follow_up(
                analysis_context=latest,
                user_question=user_text,
                chat_history=chat_history
            )
            # Save conversation to database
            database.save_chat_message(latest["id"], user_id, "user", user_text)
            database.save_chat_message(latest["id"], user_id, "assistant", answer)
        else:
            # Direct general agricultural advice (no image required!)
            chat_history = database.get_chat_history_for_user(user_id, limit=6)
            answer = ai_analyzer.answer_general_question(
                user_question=user_text,
                chat_history=chat_history
            )
            # Save conversation to database
            database.save_chat_message(None, user_id, "user", user_text)
            database.save_chat_message(None, user_id, "assistant", answer)

        # Update status message with response
        formatted_reply = f"🌾 *AgriVision Assistant:*\n\n{answer}"
        try:
            await status_msg.edit_text(formatted_reply, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception:
            # Fallback if markdown symbols in LLM response fail Telegram parser
            await status_msg.edit_text(f"🌾 AgriVision Assistant:\n\n{answer}")

    except Exception as e:
        logger.error(f"Error answering text message: {e}", exc_info=True)
        try:
            await status_msg.edit_text(f"⚠️ Unable to answer right now: {str(e)}")
        except Exception:
            await update.message.reply_text(f"⚠️ Unable to answer right now: {str(e)}")


def run_telegram_bot():
    """Initializes and runs the Telegram Bot polling loop."""
    token = get_telegram_token()
    if not token or token == "your-telegram-bot-token-here":
        print("[!] Error: TELEGRAM_BOT_TOKEN is not set.")
        print("    Please set TELEGRAM_BOT_TOKEN in .streamlit/secrets.toml or .env")
        return

    # Initialize Database & seed samples if empty
    database.init_db()
    database.seed_sample_data()

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

    print("[+] AgriVision Telegram Bot is active and listening for messages (Photo & Text)!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_telegram_bot()
