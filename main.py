
import os
import logging
import httpx

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL = "openai/gpt-oss-20b"

SYSTEM_PROMPT = """
Ты — Фаворит AI ❤️, дружелюбный помощник Telegram-группы Фаворит.

Общайся естественно, тепло и уважительно.
Поддерживай русский, украинский и английский языки.
Отвечай на языке собеседника.
Помогай с правилами группы, конкурсами, идеями,
расчётами, загадками и повседневными вопросами.
Учитывай, что ты находишься в большой дружной группе.
Не выдумывай факты и не утверждай, что выполнил
действие, если у тебя нет такой возможности.
Пиши понятно, без лишней официальности.
"""

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

history = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! ❤️ Я Фаворит AI!\n\n"
        "Я умею общаться, отвечать на вопросы, "
        "помогать с конкурсами и расчётами.\n\n"
        "Напиши мне в личку или упомяни меня в группе!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❤️ Фаворит AI — помощник группы!\n\n"
        "Обратись ко мне через @упоминание "
        "или ответь на моё сообщение.\n"
        "Также можно написать /ask и свой вопрос."
    )


async def ask_ai(question: str, chat_id: int, user_id: int):
    key = (chat_id, user_id)

    if key not in history:
        history[key] = []

    history[key].append({
        "role": "user",
        "content": question
    })

    history[key] = history[key][-10:]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ] + history[key]

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": 1200,
            },
        )

        response.raise_for_status()
        data = response.json()

    answer = data["choices"][0]["message"]["content"]

    history[key].append({
        "role": "assistant",
        "content": answer
    })

    return answer


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not message.text or not user:
        return

    question = message.text.strip()

    if chat.type != "private":
        bot_username = context.bot.username.lower()
        mentioned = f"@{bot_username}" in question.lower()

        replied = (
            message.reply_to_message is not None
            and message.reply_to_message.from_user is not None
            and message.reply_to_message.from_user.id == context.bot.id
        )

        if not mentioned and not replied:
            return

        question = question.replace(
            f"@{context.bot.username}", ""
        ).strip()

    if not question:
        await message.reply_text("Я слушаю ❤️ Напиши свой вопрос!")
        return

    await context.bot.send_chat_action(
        chat_id=chat.id,
        action=ChatAction.TYPING
    )

    try:
        answer = await ask_ai(question, chat.id, user.id)

        if not answer:
            answer = "Не получилось подготовить ответ. Попробуй ещё раз ❤️"

        for i in range(0, len(answer), 4000):
            await message.reply_text(answer[i:i + 4000])

    except httpx.HTTPStatusError as error:
        logging.exception("Groq API error")
        await message.reply_text(
            "Сейчас не получается получить ответ от AI. "
            "Попробуй немного позже ❤️"
        )

    except Exception:
        logging.exception("Bot error")
        await message.reply_text(
            "Произошла ошибка. Попробуй ещё раз ❤️"
        )


async def ask_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:
        await update.message.reply_text(
            "Напиши вопрос после команды /ask ❤️"
        )
        return

    update.message.text = " ".join(context.args)
    await handle_message(update, context)


def main():
    if not BOT_TOKEN or not GROQ_API_KEY:
        raise RuntimeError(
            "Не настроены BOT_TOKEN и GROQ_API_KEY"
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ask", ask_command))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("Favorit AI запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
