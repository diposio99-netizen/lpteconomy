"""
Discord Economy Bot
- Магазин ролей (бот создаёт роли, сам назначает цены)
- Мини-игры: слоты, кубик, монетка, блэкджек, гонки, сапёр
- Экономика: баланс, работа, daily, pay, top, rob
- БД: встроенный sqlite3 (не нужен aiosqlite)

Установка:
    pip install discord.py python-dotenv

.env:
    DISCORD_TOKEN=ВАШ_ТОКЕН

Запуск:
    python bot.py
"""

import os
import sqlite3
import random
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
import discord
from discord.ext import commands

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
DB_PATH = "./bot.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ─────────────────────────────────────────
# БД
# ─────────────────────────────────────────

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cooldowns (
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            last_used TEXT NOT NULL,
            PRIMARY KEY (user_id, action)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shop_roles (
            role_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            color INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, role_id)
        )
    """)
    con.commit()
    con.close()
    logger.info("Database ready: %s", DB_PATH)


def get_balance(user_id: int) -> int:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT balance FROM balances WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    con.close()
    return row[0] if row else 0


def set_balance(user_id: int, amount: int):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO balances(user_id, balance) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = excluded.balance",
        (user_id, amount),
    )
    con.commit()
    con.close()


def add_balance(user_id: int, delta: int):
    current = get_balance(user_id)
    set_balance(user_id, max(0, current + delta))


def get_cooldown(user_id: int, action: str) -> Optional[datetime]:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT last_used FROM cooldowns WHERE user_id = ? AND action = ?", (user_id, action))
    row = cur.fetchone()
    con.close()
    if row:
        return datetime.fromisoformat(row[0])
    return None


def set_cooldown(user_id: int, action: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO cooldowns(user_id, action, last_used) VALUES(?, ?, ?) ON CONFLICT(user_id, action) DO UPDATE SET last_used = excluded.last_used",
        (user_id, action, datetime.utcnow().isoformat()),
    )
    con.commit()
    con.close()


def check_cooldown(user_id: int, action: str, seconds: int) -> Optional[int]:
    """Возвращает оставшиеся секунды или None если кулдаун прошёл"""
    last = get_cooldown(user_id, action)
    if last is None:
        return None
    diff = (datetime.utcnow() - last).total_seconds()
    if diff < seconds:
        return int(seconds - diff)
    return None


# ─────────────────────────────────────────
# СОБЫТИЯ
# ─────────────────────────────────────────

@bot.event
async def on_ready():
    init_db()
    logger.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    logger.info("------")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help | Economy Bot"))


# ─────────────────────────────────────────
# ЭКОНОМИКА
# ─────────────────────────────────────────

@bot.command(name="balance", aliases=["bal", "money"])
async def balance(ctx, member: Optional[discord.Member] = None):
    """Показать баланс"""
    target = member or ctx.author
    bal = get_balance(target.id)
    embed = discord.Embed(color=discord.Color.green())
    embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)
    embed.add_field(name="Баланс", value=f"**{bal}**💰")
    await ctx.send(embed=embed)


@bot.command(name="daily")
async def daily(ctx):
    """Ежедневная награда (раз в 24 часа)"""
    remaining = check_cooldown(ctx.author.id, "daily", 86400)
    if remaining:
        h, m = divmod(remaining // 60, 60)
        return await ctx.send(f"⏳ Следующая награда через **{h}ч {m}м**")
    reward = random.randint(100, 500)
    add_balance(ctx.author.id, reward)
    set_cooldown(ctx.author.id, "daily")
    await ctx.send(f"🎁 {ctx.author.mention} получает ежедневную награду: **+{reward}**💰\nБаланс: **{get_balance(ctx.author.id)}**💰")


@bot.command(name="work")
async def work(ctx):
    """Поработать и получить деньги (раз в 1 час)"""
    remaining = check_cooldown(ctx.author.id, "work", 3600)
    if remaining:
        m, s = divmod(remaining, 60)
        return await ctx.send(f"⏳ Можно работать снова через **{m}м {s}с**")
    jobs = [
        ("программист", 150, 400),
        ("повар", 80, 250),
        ("таксист", 60, 200),
        ("художник", 100, 350),
        ("стример", 50, 500),
        ("майнер", 120, 300),
        ("блогер", 70, 450),
    ]
    job, min_pay, max_pay = random.choice(jobs)
    reward = random.randint(min_pay, max_pay)
    add_balance(ctx.author.id, reward)
    set_cooldown(ctx.author.id, "work")
    await ctx.send(f"💼 {ctx.author.mention} работает как **{job}** и зарабатывает **+{reward}**💰\nБаланс: **{get_balance(ctx.author.id)}**💰")


@bot.command(name="pay")
async def pay(ctx, member: discord.Member, amount: int):
    """Перевести деньги другому пользователю"""
    if member == ctx.author:
        return await ctx.send("Нельзя переводить деньги самому себе.")
    if amount <= 0:
        return await ctx.send("Сумма должна быть положительной.")
    bal = get_balance(ctx.author.id)
    if bal < amount:
        return await ctx.send(f"Недостаточно средств. Ваш баланс: **{bal}**💰")
    add_balance(ctx.author.id, -amount)
    add_balance(member.id, amount)
    await ctx.send(f"💸 {ctx.author.mention} перевёл **{amount}**💰 → {member.mention}")


@bot.command(name="rob")
async def rob(ctx, member: discord.Member):
    """Попытаться ограбить пользователя (раз в 30 минут)"""
    if member == ctx.author:
        return await ctx.send("Нельзя грабить самого себя.")
    remaining = check_cooldown(ctx.author.id, "rob", 1800)
    if remaining:
        m, s = divmod(remaining, 60)
        return await ctx.send(f"⏳ Ограбление снова доступно через **{m}м {s}с**")
    victim_bal = get_balance(member.id)
    if victim_bal < 50:
        return await ctx.send(f"У {member.display_name} слишком мало денег для ограбления.")
    set_cooldown(ctx.author.id, "rob")
    success_chance = random.random()
    if success_chance < 0.45:  # 45% успех
        stolen = random.randint(10, min(300, victim_bal // 2))
        add_balance(ctx.author.id, stolen)
        add_balance(member.id, -stolen)
        await ctx.send(f"🦹 {ctx.author.mention} успешно ограбил {member.mention} на **{stolen}**💰!")
    else:
        fine = random.randint(50, 200)
        add_balance(ctx.author.id, -fine)
        await ctx.send(f"👮 {ctx.author.mention} пойман при ограблении {member.mention} и штрафован на **{fine}**💰!")


@bot.command(name="top")
async def top(ctx):
    """Топ-10 богатейших пользователей"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT user_id, balance FROM balances ORDER BY balance DESC LIMIT 10")
    rows = cur.fetchall()
    con.close()
    if not rows:
        return await ctx.send("Таблица пуста.")
    embed = discord.Embed(title="🏆 Топ-10 богатейших", color=discord.Color.gold())
    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, bal) in enumerate(rows, 1):
        user = bot.get_user(uid)
        name = user.display_name if user else f"ID:{uid}"
        medal = medals[i - 1] if i <= 3 else f"{i}."
        lines.append(f"{medal} {name} — **{bal}**💰")
    embed.description = "\n".join(lines)
    await ctx.send(embed=embed)


@bot.command(name="addmoney")
@commands.has_permissions(administrator=True)
async def addmoney(ctx, member: discord.Member, amount: int):
    """[Админ] Добавить деньги"""
    add_balance(member.id, amount)
    await ctx.send(f"✅ Добавлено **{amount}**💰 → {member.mention}. Баланс: **{get_balance(member.id)}**💰")


@bot.command(name="setmoney")
@commands.has_permissions(administrator=True)
async def setmoney(ctx, member: discord.Member, amount: int):
    """[Админ] Установить баланс"""
    set_balance(member.id, amount)
    await ctx.send(f"✅ Баланс {member.mention} установлен: **{amount}**💰")


# ─────────────────────────────────────────
# МАГАЗИН РОЛЕЙ
# ─────────────────────────────────────────

ROLE_TEMPLATES = [
    ("⭐ VIP", 0xFFD700, 1000),
    ("💎 Premium", 0x00BFFF, 2500),
    ("🔥 Hot", 0xFF4500, 800),
    ("🌈 Rainbow", 0x9400D3, 1500),
    ("👑 King", 0xFFFF00, 5000),
    ("🤖 Cyborg", 0x00FF7F, 1200),
    ("🌙 Night", 0x191970, 700),
    ("☀️ Sun", 0xFFA500, 700),
    ("🎭 Artist", 0xFF69B4, 900),
    ("🎮 Gamer", 0x7CFC00, 600),
]


@bot.command(name="shop")
async def shop(ctx):
    """Показать магазин ролей"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT role_id, name, price FROM shop_roles WHERE guild_id = ?", (ctx.guild.id,))
    rows = cur.fetchall()
    con.close()

    if not rows:
        return await ctx.send("Магазин пуст. Используйте `!createshop` для создания ролей.")

    embed = discord.Embed(title="🛒 Магазин ролей", color=discord.Color.blurple())
    lines = []
    for role_id, name, price in rows:
        role = ctx.guild.get_role(role_id)
        status = "" if role else " *(удалена)*"
        lines.append(f"**{name}**{status} — **{price}**💰 | `!buyrole {name}`")
    embed.description = "\n".join(lines)
    embed.set_footer(text=f"Ваш баланс: {get_balance(ctx.author.id)}💰")
    await ctx.send(embed=embed)


@bot.command(name="createshop")
@commands.has_permissions(administrator=True)
async def createshop(ctx):
    """[Админ] Создать роли в магазине по шаблону"""
    await ctx.send("⏳ Создаю роли магазина...")
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    created = 0
    for name, color, price in ROLE_TEMPLATES:
        # Проверяем, не существует ли уже такая роль
        existing = discord.utils.get(ctx.guild.roles, name=name)
        if existing:
            cur.execute(
                "INSERT OR REPLACE INTO shop_roles(role_id, guild_id, name, price, color) VALUES(?, ?, ?, ?, ?)",
                (existing.id, ctx.guild.id, name, price, color),
            )
            created += 1
            continue
        try:
            role = await ctx.guild.create_role(
                name=name,
                color=discord.Color(color),
                reason="Economy Bot Shop",
            )
            cur.execute(
                "INSERT OR REPLACE INTO shop_roles(role_id, guild_id, name, price, color) VALUES(?, ?, ?, ?, ?)",
                (role.id, ctx.guild.id, name, price, color),
            )
            created += 1
            await asyncio.sleep(0.5)
        except discord.Forbidden:
            await ctx.send("❌ Нет прав для создания ролей. Дайте боту право `Manage Roles`.")
            con.close()
            return
    con.commit()
    con.close()
    await ctx.send(f"✅ Создано/обновлено **{created}** ролей в магазине! Используйте `!shop` для просмотра.")


@bot.command(name="buyrole")
async def buyrole(ctx, *, role_name: str):
    """Купить роль из магазина"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "SELECT role_id, price FROM shop_roles WHERE guild_id = ? AND name = ?",
        (ctx.guild.id, role_name),
    )
    row = cur.fetchone()
    con.close()

    if not row:
        return await ctx.send(f"Роль **{role_name}** не найдена в магазине. Используйте `!shop` для просмотра.")

    role_id, price = row
    role = ctx.guild.get_role(role_id)
    if not role:
        return await ctx.send("Роль была удалена с сервера. Обратитесь к администратору.")

    if role in ctx.author.roles:
        return await ctx.send(f"У вас уже есть роль **{role_name}**!")

    bal = get_balance(ctx.author.id)
    if bal < price:
        return await ctx.send(f"Недостаточно средств! Нужно **{price}**💰, у вас **{bal}**💰")

    try:
        await ctx.author.add_roles(role, reason="Economy Bot Shop Purchase")
        add_balance(ctx.author.id, -price)
        await ctx.send(f"✅ {ctx.author.mention} купил роль **{role_name}** за **{price}**💰!\nОстаток: **{get_balance(ctx.author.id)}**💰")
    except discord.Forbidden:
        await ctx.send("❌ Нет прав для выдачи ролей. Дайте боту право `Manage Roles`.")


@bot.command(name="sellrole")
async def sellrole(ctx, *, role_name: str):
    """Продать роль обратно (за 50% цены)"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "SELECT role_id, price FROM shop_roles WHERE guild_id = ? AND name = ?",
        (ctx.guild.id, role_name),
    )
    row = cur.fetchone()
    con.close()

    if not row:
        return await ctx.send(f"Роль **{role_name}** не найдена в магазине.")

    role_id, price = row
    role = ctx.guild.get_role(role_id)
    if not role or role not in ctx.author.roles:
        return await ctx.send(f"У вас нет роли **{role_name}**.")

    refund = price // 2
    try:
        await ctx.author.remove_roles(role, reason="Economy Bot Shop Sell")
        add_balance(ctx.author.id, refund)
        await ctx.send(f"💸 {ctx.author.mention} продал роль **{role_name}** за **{refund}**💰 (50% от цены).")
    except discord.Forbidden:
        await ctx.send("❌ Нет прав для снятия ролей.")


# ─────────────────────────────────────────
# МИНИ-ИГРЫ
# ─────────────────────────────────────────

# --- Монетка ---
@bot.command(name="coin", aliases=["flip"])
async def coin(ctx, side: str, bet: int):
    """Монетка: !coin орёл/решка <ставка>"""
    side = side.lower()
    if side not in ("орёл", "решка", "орел"):
        return await ctx.send("Выберите: `орёл` или `решка`")
    if side == "орел":
        side = "орёл"
    if bet <= 0:
        return await ctx.send("Ставка должна быть положительной.")
    bal = get_balance(ctx.author.id)
    if bal < bet:
        return await ctx.send(f"Недостаточно средств. Баланс: **{bal}**💰")
    result = random.choice(["орёл", "решка"])
    if result == side:
        add_balance(ctx.author.id, bet)
        await ctx.send(f"🪙 Выпало **{result}**! Вы угадали! **+{bet}**💰 → Баланс: **{get_balance(ctx.author.id)}**💰")
    else:
        add_balance(ctx.author.id, -bet)
        await ctx.send(f"🪙 Выпало **{result}**! Вы проиграли! **-{bet}**💰 → Баланс: **{get_balance(ctx.author.id)}**💰")


# --- Кубик ---
@bot.command(name="dice")
async def dice(ctx, number: int, bet: int):
    """Кубик: !dice <число 1-6> <ставка>"""
    if number < 1 or number > 6:
        return await ctx.send("Число должно быть от 1 до 6.")
    if bet <= 0:
        return await ctx.send("Ставка должна быть положительной.")
    bal = get_balance(ctx.author.id)
    if bal < bet:
        return await ctx.send(f"Недостаточно средств. Баланс: **{bal}**💰")
    result = random.randint(1, 6)
    dice_emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    if result == number:
        winnings = bet * 5
        add_balance(ctx.author.id, winnings)
        await ctx.send(f"🎲 Выпало {dice_emoji[result-1]}! Вы угадали! **+{winnings}**💰 (x5) → Баланс: **{get_balance(ctx.author.id)}**💰")
    else:
        add_balance(ctx.author.id, -bet)
        await ctx.send(f"🎲 Выпало {dice_emoji[result-1]}! Вы проиграли **-{bet}**💰 → Баланс: **{get_balance(ctx.author.id)}**💰")


# --- Слоты ---
SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣"]
SLOT_MULTIPLIERS = {"🍒": 2, "🍋": 2, "🍊": 3, "🍇": 3, "⭐": 5, "💎": 10, "7️⃣": 20}


@bot.command(name="slots")
async def slots(ctx, bet: int):
    """Слоты: !slots <ставка>"""
    if bet <= 0:
        return await ctx.send("Ставка должна быть положительной.")
    bal = get_balance(ctx.author.id)
    if bal < bet:
        return await ctx.send(f"Недостаточно средств. Баланс: **{bal}**💰")

    reels = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
    result_str = " | ".join(reels)

    if reels[0] == reels[1] == reels[2]:
        mult = SLOT_MULTIPLIERS[reels[0]]
        winnings = bet * mult
        add_balance(ctx.author.id, winnings)
        await ctx.send(f"🎰 [ {result_str} ]\n🎉 ДЖЕКПОТ! x{mult} → **+{winnings}**💰 → Баланс: **{get_balance(ctx.author.id)}**💰")
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        winnings = bet
        add_balance(ctx.author.id, winnings)
        await ctx.send(f"🎰 [ {result_str} ]\n✨ Два одинаковых! **+{winnings}**💰 → Баланс: **{get_balance(ctx.author.id)}**💰")
    else:
        add_balance(ctx.author.id, -bet)
        await ctx.send(f"🎰 [ {result_str} ]\n😞 Не повезло! **-{bet}**💰 → Баланс: **{get_balance(ctx.author.id)}**💰")


# --- Блэкджек ---
def card_value(card):
    rank = card[:-1]
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_value(hand):
    val = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[:-1] == "A")
    while val > 21 and aces:
        val -= 10
        aces -= 1
    return val


def make_deck():
    suits = ["♠", "♥", "♦", "♣"]
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    deck = [r + s for s in suits for r in ranks]
    random.shuffle(deck)
    return deck


def hand_str(hand):
    return " ".join(hand)


blackjack_games = {}


@bot.command(name="bj", aliases=["blackjack"])
async def blackjack(ctx, bet: int):
    """Блэкджек: !bj <ставка> затем !hit или !stand"""
    if ctx.author.id in blackjack_games:
        return await ctx.send("У вас уже идёт игра! Используйте `!hit` или `!stand`.")
    if bet <= 0:
        return await ctx.send("Ставка должна быть положительной.")
    bal = get_balance(ctx.author.id)
    if bal < bet:
        return await ctx.send(f"Недостаточно средств. Баланс: **{bal}**💰")

    deck = make_deck()
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]
    blackjack_games[ctx.author.id] = {"deck": deck, "player": player, "dealer": dealer, "bet": bet}
    add_balance(ctx.author.id, -bet)

    embed = discord.Embed(title="🃏 Блэкджек", color=discord.Color.dark_green())
    embed.add_field(name="Ваши карты", value=f"{hand_str(player)} (сумма: {hand_value(player)})", inline=False)
    embed.add_field(name="Карты дилера", value=f"{dealer[0]} ?", inline=False)
    embed.set_footer(text="!hit — взять карту | !stand — остановиться")

    if hand_value(player) == 21:
        winnings = int(bet * 2.5)
        add_balance(ctx.author.id, winnings)
        del blackjack_games[ctx.author.id]
        embed.add_field(name="🎉 БЛЭКДЖЕК!", value=f"Выигрыш: **+{winnings}**💰", inline=False)
        return await ctx.send(embed=embed)

    await ctx.send(embed=embed)


@bot.command(name="hit")
async def hit(ctx):
    """Взять карту в блэкджеке"""
    game = blackjack_games.get(ctx.author.id)
    if not game:
        return await ctx.send("У вас нет активной игры. Начните с `!bj <ставка>`.")
    game["player"].append(game["deck"].pop())
    val = hand_value(game["player"])
    embed = discord.Embed(title="🃏 Блэкджек", color=discord.Color.dark_green())
    embed.add_field(name="Ваши карты", value=f"{hand_str(game['player'])} (сумма: {val})", inline=False)
    if val > 21:
        del blackjack_games[ctx.author.id]
        embed.color = discord.Color.red()
        embed.add_field(name="💥 Перебор!", value=f"Вы проиграли **{game['bet']}**💰", inline=False)
    elif val == 21:
        await ctx.send(embed=embed)
        ctx.message.content = PREFIX + "stand"
        await stand(ctx)
        return
    else:
        embed.set_footer(text="!hit — взять карту | !stand — остановиться")
    await ctx.send(embed=embed)


@bot.command(name="stand")
async def stand(ctx):
    """Остановиться в блэкджеке"""
    game = blackjack_games.get(ctx.author.id)
    if not game:
        return await ctx.send("У вас нет активной игры. Начните с `!bj <ставка>`.")
    dealer = game["dealer"]
    deck = game["deck"]
    while hand_value(dealer) < 17:
        dealer.append(deck.pop())
    p_val = hand_value(game["player"])
    d_val = hand_value(dealer)
    bet = game["bet"]
    del blackjack_games[ctx.author.id]

    embed = discord.Embed(title="🃏 Блэкджек — Итог", color=discord.Color.dark_green())
    embed.add_field(name="Ваши карты", value=f"{hand_str(game['player'])} (сумма: {p_val})", inline=False)
    embed.add_field(name="Карты дилера", value=f"{hand_str(dealer)} (сумма: {d_val})", inline=False)

    if d_val > 21 or p_val > d_val:
        add_balance(ctx.author.id, bet * 2)
        embed.color = discord.Color.green()
        embed.add_field(name="🎉 Вы выиграли!", value=f"**+{bet}**💰 → Баланс: **{get_balance(ctx.author.id)}**💰", inline=False)
    elif p_val == d_val:
        add_balance(ctx.author.id, bet)
        embed.add_field(name="🤝 Ничья", value=f"Ставка возвращена → Баланс: **{get_balance(ctx.author.id)}**💰", inline=False)
    else:
        embed.color = discord.Color.red()
        embed.add_field(name="😞 Вы проиграли", value=f"**-{bet}**💰 → Баланс: **{get_balance(ctx.author.id)}**💰", inline=False)

    await ctx.send(embed=embed)


# --- Гонки ---
ANIMALS = ["🐎", "🐇", "🐢", "🦊", "🐆"]


@bot.command(name="race")
async def race(ctx, animal_num: int, bet: int):
    """Гонки: !race <номер 1-5> <ставка>"""
    if animal_num < 1 or animal_num > 5:
        return await ctx.send("Выберите участника от 1 до 5:\n" + " ".join(f"{i+1}:{a}" for i, a in enumerate(ANIMALS)))
    if bet <= 0:
        return await ctx.send("Ставка должна быть положительной.")
    bal = get_balance(ctx.author.id)
    if bal < bet:
        return await ctx.send(f"Недостаточно средств. Баланс: **{bal}**💰")

    msg = await ctx.send("🏁 Гонка начинается!\n" + "\n".join(f"{a} {'▪' * 1}" for a in ANIMALS))
    await asyncio.sleep(1)

    positions = [0] * 5
    track_len = 10
    while max(positions) < track_len:
        for i in range(5):
            positions[i] += random.randint(0, 3)
        track = "\n".join(f"{ANIMALS[i]} {'▪' * min(positions[i], track_len)}" for i in range(5))
        await msg.edit(content=f"🏁 Гонка!\n{track}")
        await asyncio.sleep(0.8)

    winner_idx = positions.index(max(positions))
    winner = ANIMALS[winner_idx]

    if winner_idx == animal_num - 1:
        winnings = bet * 4
        add_balance(ctx.author.id, winnings)
        await ctx.send(f"🏆 Победил {winner}! Вы угадали! **+{winnings}**💰 (x4) → Баланс: **{get_balance(ctx.author.id)}**💰")
    else:
        add_balance(ctx.author.id, -bet)
        await ctx.send(f"🏆 Победил {winner}! Ваш участник проиграл. **-{bet}**💰 → Баланс: **{get_balance(ctx.author.id)}**💰")


# --- Сапёр ---
minesweeper_games = {}


@bot.command(name="minesweeper", aliases=["ms"])
async def minesweeper(ctx, bet: int, mines: int = 3):
    """Сапёр: !ms <ставка> [мины 1-8]. Затем !open <номер 1-9>"""
    if ctx.author.id in minesweeper_games:
        return await ctx.send("У вас уже идёт игра! Используйте `!open <1-9>` или `!cashout`.")
    if bet <= 0:
        return await ctx.send("Ставка должна быть положительной.")
    if mines < 1 or mines > 8:
        return await ctx.send("Мины: от 1 до 8.")
    bal = get_balance(ctx.author.id)
    if bal < bet:
        return await ctx.send(f"Недостаточно средств. Баланс: **{bal}**💰")

    cells = list(range(9))
    mine_positions = set(random.sample(cells, mines))
    add_balance(ctx.author.id, -bet)
    minesweeper_games[ctx.author.id] = {
        "mines": mine_positions,
        "opened": set(),
        "bet": bet,
        "multiplier": 1.0,
        "mines_count": mines,
    }

    embed = discord.Embed(title="💣 Сапёр", color=discord.Color.orange())
    embed.add_field(name="Поле (9 клеток)", value="1️⃣2️⃣3️⃣\n4️⃣5️⃣6️⃣\n7️⃣8️⃣9️⃣", inline=False)
    embed.add_field(name="Мины на поле", value=str(mines), inline=True)
    embed.add_field(name="Ставка", value=f"**{bet}**💰", inline=True)
    embed.set_footer(text="!open <1-9> — открыть клетку | !cashout — забрать выигрыш")
    await ctx.send(embed=embed)


def ms_field_str(opened, mines=None, reveal=False):
    nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    cells = []
    for i in range(9):
        if i in opened:
            cells.append("✅")
        elif reveal and mines and i in mines:
            cells.append("💥")
        else:
            cells.append(nums[i])
    return f"{cells[0]}{cells[1]}{cells[2]}\n{cells[3]}{cells[4]}{cells[5]}\n{cells[6]}{cells[7]}{cells[8]}"


@bot.command(name="open")
async def ms_open(ctx, cell: int):
    """Открыть клетку в сапёре"""
    game = minesweeper_games.get(ctx.author.id)
    if not game:
        return await ctx.send("Нет активной игры. Начните с `!ms <ставка>`.")
    if cell < 1 or cell > 9:
        return await ctx.send("Номер клетки от 1 до 9.")
    idx = cell - 1
    if idx in game["opened"]:
        return await ctx.send("Эта клетка уже открыта!")

    if idx in game["mines"]:
        field = ms_field_str(game["opened"], game["mines"], reveal=True)
        del minesweeper_games[ctx.author.id]
        await ctx.send(f"💥 МИНА! Вы проиграли **{game['bet']}**💰!\n{field}\nБаланс: **{get_balance(ctx.author.id)}**💰")
    else:
        game["opened"].add(idx)
        safe = 9 - game["mines_count"]
        progress = len(game["opened"])
        game["multiplier"] = round(1.0 + (progress / safe) * (game["mines_count"] * 0.5), 2)
        field = ms_field_str(game["opened"])
        potential = int(game["bet"] * game["multiplier"])
        embed = discord.Embed(title="💣 Сапёр", color=discord.Color.green())
        embed.add_field(name="Поле", value=field, inline=False)
        embed.add_field(name="Множитель", value=f"x{game['multiplier']}", inline=True)
        embed.add_field(name="Потенциальный выигрыш", value=f"**{potential}**💰", inline=True)
        embed.set_footer(text="!open <1-9> — открыть | !cashout — забрать")
        if progress == safe:
            add_balance(ctx.author.id, potential)
            del minesweeper_games[ctx.author.id]
            embed.color = discord.Color.gold()
            embed.add_field(name="🎉 Вы открыли все безопасные клетки!", value=f"**+{potential}**💰", inline=False)
        await ctx.send(embed=embed)


@bot.command(name="cashout")
async def cashout(ctx):
    """Забрать выигрыш в сапёре"""
    game = minesweeper_games.get(ctx.author.id)
    if not game:
        return await ctx.send("Нет активной игры.")
    if not game["opened"]:
        add_balance(ctx.author.id, game["bet"])
        del minesweeper_games[ctx.author.id]
        return await ctx.send("Вы не открыли ни одной клетки. Ставка возвращена.")
    winnings = int(game["bet"] * game["multiplier"])
    add_balance(ctx.author.id, winnings)
    del minesweeper_games[ctx.author.id]
    await ctx.send(f"💰 Вы забрали **{winnings}**💰 (x{game['multiplier']}) → Баланс: **{get_balance(ctx.author.id)}**💰")


# ─────────────────────────────────────────
# ПОМОЩЬ
# ─────────────────────────────────────────

bot.remove_command("help")


@bot.command(name="help")
async def help_cmd(ctx):
    """Список команд"""
    embed = discord.Embed(title="📖 Список команд", color=discord.Color.blurple())

    embed.add_field(name="💰 Экономика", value="""
`!balance [@user]` — баланс
`!daily` — ежедневная награда
`!work` — работа (раз в час)
`!pay @user <сумма>` — перевод
`!rob @user` — ограбление
`!top` — топ-10 богатейших
""", inline=False)

    embed.add_field(name="🛒 Магазин ролей", value="""
`!shop` — список ролей
`!buyrole <название>` — купить роль
`!sellrole <название>` — продать роль (50%)
`!createshop` — создать роли [Админ]
""", inline=False)

    embed.add_field(name="🎮 Мини-игры", value="""
`!coin <орёл/решка> <ставка>` — монетка
`!dice <1-6> <ставка>` — кубик (x5 при угадывании)
`!slots <ставка>` — слоты
`!bj <ставка>` → `!hit` / `!stand` — блэкджек
`!race <1-5> <ставка>` — гонки (x4)
`!ms <ставка> [мины]` → `!open <1-9>` / `!cashout` — сапёр
""", inline=False)

    embed.set_footer(text=f"Префикс: {PREFIX}")
    await ctx.send(embed=embed)


# ─────────────────────────────────────────
# ОБРАБОТКА ОШИБОК
# ─────────────────────────────────────────

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Пропущен аргумент: `{error.param.name}`. Используйте `!help` для справки.")
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("У вас нет прав для этой команды.")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("Неверный аргумент. Используйте `!help` для справки.")
        return
    logger.exception(error)
    await ctx.send(f"Ошибка: {error}")


# ─────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────

def main():
    if not TOKEN:
        logger.error("DISCORD_TOKEN не найден! Создайте .env с DISCORD_TOKEN=ВАШ_ТОКЕН")
        return
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
