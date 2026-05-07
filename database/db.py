import aiosqlite
import os
from datetime import datetime
import uuid

DB_PATH = "bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                id TEXT PRIMARY KEY,
                sender_id INTEGER,
                recipient_id INTEGER,
                recipient_username TEXT,
                content TEXT,
                created_at TIMESTAMP
            )
        """)
        await db.commit()

async def save_secret(sender_id, content, recipient_id=None, recipient_username=None, secret_id=None):
    if not secret_id:
        secret_id = str(uuid.uuid4())[:18]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO secrets (id, sender_id, recipient_id, recipient_username, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (secret_id, sender_id, recipient_id, recipient_username, content, datetime.now())
        )
        await db.commit()
    return secret_id

async def get_secret(secret_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT sender_id, recipient_id, recipient_username, content FROM secrets WHERE id = ?", (secret_id,)) as cursor:
            return await cursor.fetchone()

async def delete_secret(secret_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM secrets WHERE id = ?", (secret_id,))
        await db.commit()

async def get_recent_recipients(sender_id, limit=5):
    async with aiosqlite.connect(DB_PATH) as db:
        # Smart history: GROUP BY username to show only the latest unique recipient, ignoring short fragments
        query = """
            SELECT recipient_username FROM (
                SELECT recipient_username, MAX(created_at) as last_date 
                FROM secrets 
                WHERE sender_id = ? AND recipient_username IS NOT NULL AND length(recipient_username) > 2
                GROUP BY recipient_username
            ) ORDER BY last_date DESC LIMIT ?
        """
        async with db.execute(query, (sender_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def claim_secret(secret_id, recipient_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE secrets SET recipient_id = ? WHERE id = ? AND recipient_id IS NULL", (recipient_id, secret_id))
        await db.commit()

async def cleanup_history():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM secrets WHERE recipient_username IS NOT NULL AND length(recipient_username) < 3")
        await db.commit()
