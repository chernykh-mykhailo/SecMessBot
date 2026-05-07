from aiogram import Router, types, F
from aiogram.exceptions import TelegramForbiddenError
from database.db import get_secret, claim_secret

router = Router()

@router.callback_query(F.data.startswith("read:"))
async def read_secret_handler(callback: types.CallbackQuery):
    # FIX: Correctly extract the FULL secret_id (it may contain colons)
    secret_id = callback.data.replace("read:", "")
    secret_data = await get_secret(secret_id)

    if not secret_data:
        await callback.answer("❌ Message expired or not found.", show_alert=True)
        return

    sender_id, recipient_id, recipient_username, content = secret_data
    current_user_id = callback.from_user.id
    current_username = callback.from_user.username.lower() if callback.from_user.username else None

    # Logic for "First person" secrets (no recipient_id and no recipient_username yet)
    if not recipient_id and not recipient_username:
        # Lock this secret to the first clicker
        await claim_secret(secret_id, current_user_id)
        recipient_id = current_user_id # Grant access to current user

    # Check authorization
    is_authorized = False
    
    if recipient_id and current_user_id == recipient_id:
        is_authorized = True
    elif recipient_username and current_username == recipient_username.lower():
        is_authorized = True
    elif current_user_id == sender_id:
        is_authorized = True 

    if not is_authorized:
        target = f"@{recipient_username}" if recipient_username else "another user (first come first served)"
        await callback.answer(f"🔒 Go away! This message is only for {target}.", show_alert=True)
        return

    # Handle disclosure
    if len(content) < 200:
        await callback.answer(f"🔓 Секрет:\n\n{content}", show_alert=True)
    else:
        # Long message handler
        try:
            await callback.bot.send_message(
                chat_id=current_user_id,
                text=f"🔓 <b>Ваше секретне повідомлення:</b>\n\n{content}",
                parse_mode="HTML"
            )
            await callback.answer("📬 Повідомлення довге, я надіслав його вам у приват!", show_alert=True)
        except TelegramForbiddenError:
            # Deep Link fallback if bot is blocked/not started
            bot_user = await callback.bot.get_me()
            link = f"https://t.me/{bot_user.username}?start=read_{secret_id}"
            await callback.answer(
                f"⚠️ Повідомлення занадто довге.\n\n"
                f"Щоб прочитати, натисніть сюди і кнопку 'Старт':\n{link}", 
                show_alert=True
            )
        except Exception:
            await callback.answer("❌ Помилка при відправці в приват.", show_alert=True)
