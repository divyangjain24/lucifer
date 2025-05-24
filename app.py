import logging
import aiohttp
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# --- Config ---
BOT_TOKEN = "7609953641:AAFFNM0Me8fMNIFWQdofUZvWxXi7sp4wnRY"  # Replace with your actual Telegram bot token
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-3.5-turbo"

# --- Logger ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Conversation States ---
LANGUAGE, PROMPT = range(2)

# --- Available Languages ---
LANGUAGES = ["Python", "Java", "JavaScript", "C++", "C#", "Go", "Rust", "Kotlin"]

# Store selected language per user
user_language_map = {}

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(lang, callback_data=lang)] for lang in LANGUAGES
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_chat.send_message(
        text="👋 Welcome to the AI Code Generator Bot!\n\nPlease select your programming language:",
        reply_markup=reply_markup
    )
    return LANGUAGE

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = query.data

    user_id = query.from_user.id
    user_language_map[user_id] = language

    await query.message.reply_text(
        f"✅ Language set to *{language}*.\n\nNow send me your prompt.",
        parse_mode="Markdown"
    )
    return PROMPT

async def receive_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    language = user_language_map.get(user_id, "Python")
    prompt = update.message.text

    await update.message.reply_text("🧠 Generating code, please wait...")

    system_prompt = f"You are an expert code assistant. Write clean and efficient code in {language}."
    full_prompt = f"{prompt}\n\nLanguage: {language}"

    result = await generate_code(system_prompt, full_prompt)
    await update.message.reply_text(f"```{language.lower()}\n{result}```", parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

# --- OpenRouter Code Generation ---
async def generate_code(system_instruction, user_prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 700
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(payload)) as response:
            if response.status == 200:
                result = await response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                error_text = await response.text()
                logger.error(f"OpenRouter error: {response.status} - {error_text}")
                return "❌ Failed to generate code. Please try again later."

# --- Main Bot Setup ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE: [CallbackQueryHandler(select_language)],
            PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prompt)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    print("🚀 AI Code Generator Bot is running...")
    app.run_polling()
