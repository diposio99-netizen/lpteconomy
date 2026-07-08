"""
Простой полностью рабочий Discord-бот на discord.py (pycord style compatible).
Требования: Python 3.8+, установить зависимости:
    pip install -U discord.py python-dotenv aiosqlite

Функции:
- Загружает TOKEN из переменных окружения (или .env)
- Командный префикс '!' (можно изменить)
- Команды: ping, info, balance (sqlite), addmoney (админ), sync (slash sync)
- Сохраняет баланс пользователей в SQLite bot.db
- Логирование в консоль

Запуск:
- Создайте .env с DISCORD_TOKEN=ВАШ_ТОКЕН
- python bot.py
"""

import os
import asyncio
import logging
from typing import Optional

import aiosqlite
from dotenv import load_dotenv
import discord
from discord.ext import commands

# Загрузка .env (если есть)
load_dotenv()

# Конфигурация
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")
DB_PATH = os.getenv("DATABASE_PATH", "./bot.db")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # опционально

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bot")

# Интенты
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Подключение к БД
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await db.commit()
    logger.info("Database initialized: %s", DB_PATH)


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info("------")
    # Инициализация БД при старте
    await init_db()


# Utility: get/set balance
async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM balances WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        await cur.close()
        return row[0] if row else 0


async def set_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO balances(user_id, balance) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = excluded.balance",
            (user_id, amount),
        )
        await db.commit()


async def add_balance(user_id: int, delta: int):
    current = await get_balance(user_id)
    await set_balance(user_id, current + delta)


# Команды
@bot.command(name="ping")
async def ping(ctx: commands.Context):
    """Проверка отклика"""
    ws = round(bot.latency * 1000)
    await ctx.send(f"Pong! {ws}ms")


@bot.command(name="info")
async def info(ctx: commands.Context):
    """Информация о боте"""
    embed = discord.Embed(title="Bot info", color=discord.Color.blurple())
    embed.add_field(name="User", value=str(bot.user), inline=True)
    embed.add_field(name="Prefix", value=PREFIX, inline=True)
    embed.set_footer(text=f"Running on {os.name}")
    await ctx.send(embed=embed)


@bot.command(name="balance")
async def balance(ctx: commands.Context, member: Optional[discord.Member] = None):
    """Показать баланс (по умолчанию — вызывающего)"""
    target = member or ctx.author
    bal = await get_balance(target.id)
    await ctx.send(f"Баланс {target.display_name}: {bal}💰")


@bot.command(name="addmoney")
@commands.has_permissions(administrator=True)
async def addmoney(ctx: commands.Context, member: discord.Member, amount: int):
    """Добавить деньги пользователю (только админы)"""
    if amount == 0:
        return await ctx.send("Сумма должна быть не нулевой")
    await add_balance(member.id, amount)
    await ctx.send(f"Добавлено {amount}💰 пользователю {member.display_name}")


@addmoney.error
async def addmoney_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Использование: !addmoney @user amount")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Неверный аргумент — убедитесь, что @user и amount указаны корректно")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("Требуются права администратора")
    else:
        logger.exception(error)
        await ctx.send("Произошла ошибка при выполнении команды")


# Owner-only command to shutdown
@bot.command(name="shutdown")
@commands.is_owner()
async def shutdown(ctx: commands.Context):
    await ctx.send("Shutting down...")
    await bot.close()


# Slash command sync helper (если нужны слэши)
@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx: commands.Context):
    """Синхронизировать application commands (если используете слэши)"""
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands")
    except Exception as e:
        logger.exception(e)
        await ctx.send("Не удалось синхронизировать")


# Error handler
@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Пропущен аргумент")
        return
    logger.exception(error)
    await ctx.send(f"Ошибка: {error}")


# Запуск
def main():
    if not TOKEN:
        logger.error("DISCORD_TOKEN не найден в окружении. Создайте .env с DISCORD_TOKEN=... или установите переменную окружения.")
        return
    try:
        bot.run(TOKEN)
    except Exception:
        logger.exception("Ошибка при запуске бота")


if __name__ == "__main__":
    main()
