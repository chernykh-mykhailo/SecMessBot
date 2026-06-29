import re
import html
import uuid
from aiogram import Router, types
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import save_secret, get_recent_recipients, get_reply_recipient

router = Router()

@router.inline_query()
async def inline_handler(query: types.InlineQuery):
    """
    Shows results but DOES NOT save anything to the database.
    """
    text = query.query.strip()
    if not text:
        return

    match = re.search(r"(.*)@(\w+)$", text)
    results = []

    if match:
        content = match.group(1).strip()
        username = match.group(2).strip()
        if content:
            result_id = str(uuid.uuid4())[:18]
            
            safe_username = html.escape(username)
            username_display = f"@{username}" if username.lower() != "any" else "того, хто першим натисне"
            
            results.append(InlineQueryResultArticle(
                id=result_id,
                title=f"🔒 Надіслати для {username_display}",
                description=f"Текст: {content[:30]}...",
                input_message_content=InputTextMessageContent(
                    message_text=f"🎁 <b>Секретне повідомлення для {html.escape(username_display)}</b>\n\nНатисніть кнопку нижче, щоб прочитати.",
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔓 Відкрити повідомлення", callback_data=f"read:{result_id}")]
                ])
            ))
    else:
        # Check if there is a cached reply recipient
        reply_recipient = await get_reply_recipient(query.from_user.id)
        if reply_recipient:
            r_username, r_id = reply_recipient
            if r_username.startswith("ID_"):
                username_display = f"користувача (ID: {r_id})"
            else:
                username_display = f"@{r_username}"
                
            res_id = f"R:{r_username}:{str(uuid.uuid4())[:8]}"
            results.append(InlineQueryResultArticle(
                id=res_id,
                title=f"🔒 Надіслати для {username_display} (з реплаю)",
                description=f"Текст: {text[:30]}...",
                input_message_content=InputTextMessageContent(
                    message_text=f"🎁 <b>Секретне повідомлення для {html.escape(username_display)}</b>\n\nНатисніть кнопку нижче, щоб прочитати.",
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔓 Відкрити повідомлення", callback_data=f"read:{res_id}")]
                ])
            ))

        # Hint result
        results.append(InlineQueryResultArticle(
            id="hint",
            title="⚠️ Напишіть @юзернейм в кінці",
            description="Формат: [текст] @username",
            input_message_content=InputTextMessageContent(
                message_text="Щоб надіслати секрет, використовуйте формат: <code>@bot [текст] @username</code>",
                parse_mode="HTML"
            )
        ))
        
        # History results
        recent = await get_recent_recipients(query.from_user.id)
        for r_username in recent:
            # FIX: Use ':' as separator because usernames can contain '_'
            res_id = f"H:{r_username}:{str(uuid.uuid4())[:8]}"
            results.append(InlineQueryResultArticle(
                id=res_id,
                title=f"🕒 {r_username}",
                description=f"Надіслати поточний текст для @{r_username}",
                input_message_content=InputTextMessageContent(
                    message_text=f"🎁 <b>Секретне повідомлення для @{html.escape(r_username)}</b>\n\nНатисніть кнопку нижче.",
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔓 Відкрити повідомлення", callback_data=f"read:{res_id}")]
                ])
            ))

    await query.answer(results, cache_time=1, is_personal=True)


@router.chosen_inline_result()
async def chosen_result_handler(chosen_result: types.ChosenInlineResult):
    """
    Saves the secret ONLY when the user actually clicks a result.
    """
    text = chosen_result.query.strip()
    result_id = chosen_result.result_id
    
    if result_id == "hint":
        return

    content = text
    username = None
    recipient_id = None

    # FIX: Correctly parse history ID using ':' separator
    if result_id.startswith("R:"):
        parts = result_id.split(":")
        if len(parts) >= 2:
            username = parts[1]
            content = text
            if username.startswith("ID_"):
                try:
                    recipient_id = int(username.replace("ID_", ""))
                    username = None
                except ValueError:
                    pass
    elif result_id.startswith("H:"):
        parts = result_id.split(":")
        if len(parts) >= 2:
            username = parts[1]
            content = text
    else:
        # Regular item - parse query
        match = re.search(r"(.*)@(\w+)$", text)
        if match:
            content = match.group(1).strip()
            username = match.group(2).strip()
    
    if username and username.lower() == "any":
        username = None
        
    await save_secret(
        sender_id=chosen_result.from_user.id,
        content=content,
        recipient_id=recipient_id,
        recipient_username=username,
        secret_id=result_id
    )
    print(f"✅ Секрет збережено в БД! ID: {result_id} для {username or recipient_id or 'ANY'}")
