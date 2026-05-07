import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database.db import init_db
from handlers import inline, commands, callbacks

async def main():
    # Initialize logging
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    if not BOT_TOKEN or BOT_TOKEN == "your_token_here":
        print("CRITICAL: BOT_TOKEN is not set in .env file!")
        return

    # Initialize Bot and Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Register routers
    dp.include_router(commands.router)
    dp.include_router(inline.router)
    dp.include_router(callbacks.router)

    # Initialize Database
    await init_db()

    # Start polling
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
