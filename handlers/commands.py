import asyncio
import uuid
from aiogram import Router, types, filters
from database.db import get_secret, claim_secret, save_reply_recipient

router = Router()

@router.message(lambda msg: msg.reply_to_message is not None)
@router.guest_message(lambda msg: msg.reply_to_message is not None)
async def reply_mention_handler(message: types.Message):
    # Check if the message contains the bot's username (e.g. "@bot_username")
    bot_info = await message.bot.get_me()
    bot_username = f"@{bot_info.username}"
    
    if message.text and bot_username.lower() in message.text.lower():
        target_user = message.reply_to_message.from_user
        if not target_user:
            return
            
        recipient_username = target_user.username
        recipient_id = target_user.id
        
        username_to_store = recipient_username if recipient_username else f"ID_{recipient_id}"
        
        await save_reply_recipient(
            sender_id=message.from_user.id,
            recipient_username=username_to_store,
            recipient_id=recipient_id
        )
        
        display_name = f"@{recipient_username}" if recipient_username else target_user.full_name
        
        text_content = (
            f"🎯 <b>Отримувача {display_name} встановлено!</b>\n\n"
            f"Тепер введіть у полі повідомлення:\n"
            f"<blockquote><code>@{bot_info.username} [ваш секретний текст]</code></blockquote>\n\n"
        )
        
        # Check if it is a guest message
        if hasattr(message, "guest_query_id") and message.guest_query_id:
            from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
            
            result_article = InlineQueryResultArticle(
                id=str(uuid.uuid4())[:8],
                title="🎯 Отримувача встановлено!",
                input_message_content=InputTextMessageContent(
                    message_text=text_content,
                    parse_mode="HTML"
                )
            )
            sent_msg = await message.bot.answer_guest_query(
                guest_query_id=message.guest_query_id,
                result=result_article
            )
            
            async def delete_guest_message():
                await asyncio.sleep(30)
                try:
                    await message.delete()
                except Exception:
                    pass
                
                inline_id = getattr(sent_msg, 'inline_message_id', None)
                if inline_id:
                    try:
                        await message.bot.edit_message_text(
                            text="🗑️",
                            inline_message_id=inline_id
                        )
                    except Exception:
                        pass
                        
            asyncio.create_task(delete_guest_message())
        else:
            reply_msg = await message.answer(
                text_content,
                parse_mode="HTML"
            )
            
            async def delete_messages():
                await asyncio.sleep(10)
                try:
                    await message.delete()
                except Exception:
                    pass
                try:
                    await reply_msg.delete()
                except Exception:
                    pass
                    
            asyncio.create_task(delete_messages())




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
