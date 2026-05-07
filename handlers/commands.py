from aiogram import Router, types, filters
from database.db import get_secret, claim_secret

router = Router()

@router.message(filters.CommandStart())
async def start_handler(message: types.Message):
    # Check for deep linking arguments (e.g., /start read_secretid)
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("read_"):
        secret_id = args[1].replace("read_", "")
        secret_data = await get_secret(secret_id)
        
        if secret_data:
            sender_id, recipient_id, recipient_username, content = secret_data
            current_user_id = message.from_user.id
            current_username = message.from_user.username.lower() if message.from_user.username else None

            # Handle generic "first come" secrets
            if not recipient_id and not recipient_username:
                await claim_secret(secret_id, current_user_id)
                recipient_id = current_user_id

            # Authorization check
            is_authorized = (
                (recipient_id and current_user_id == recipient_id) or 
                (recipient_username and current_username == recipient_username.lower()) or 
                (current_user_id == sender_id)
            )

            if is_authorized:
                await message.answer(f"🔓 <b>Ваше секретне повідомлення:</b>\n\n{content}", parse_mode="HTML")
                return
            else:
                await message.answer("🔒 Вибачте, це повідомлення не для вас.")
                return

    # Standard start message
    await message.answer(
        "🔒 <b>Вітаю у Secret Message Bot!</b>\n\n"
        "Я допоможу надіслати повідомлення, яке прочитає лише обрана людина.\n\n"
        "<b>Як користуватися:</b>\n"
        "1. Зайдіть у будь-який чат.\n"
        "2. Почніть писати: <code>@bot_username [текст] @username</code>.\n"
        "3. Виберіть результат у списку для відправки.\n\n"
        "💡 <b>Секрет</b>: напишіть <code>@any</code> замість юзернейма, щоб секрет дістався першому, хто натисне!",
        parse_mode="HTML"
    )
