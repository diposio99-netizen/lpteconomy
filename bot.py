import os
import discord
from discord.ext import commands, tasks
import asyncio
import random
import sqlite3
import datetime
import time
from collections import deque

# ----------------- CONFIG -----------------
TOKEN = os.getenv('DISCORD_TOKEN', 'YOUR_BOT_TOKEN_HERE')
PREFIX = '!'
CURRENCY = '₵'
DB_PATH = 'economy.db'
DAILY_AMOUNT = 500
WORK_MIN, WORK_MAX = 50, 200
START_BALANCE = 100
RPS_FRAMES = ['✊', '✋', '✌️']
RPS_ANIM_DELAY = 0.45
MAX_TOP = 25
VOICE_COINS_PER_MIN = 1           # монет в минуту
VOICE_MIN_SECONDS = 60            # минимальное оплачиваемое время в секундах
VOICE_DAILY_LIMIT = 300           # лимит монет в день за голосовую
VOICE_IGNORE_AFK = True           # не платить в AFK каналах
VOICE_AFK_CATEGORY_NAMES = ['AFK', 'afk']  # дополнительные названия категорий для исключения

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ----------------- DATABASE -----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

c.execute(f"""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT {START_BALANCE},
    last_daily TEXT,
    voice_today INTEGER DEFAULT 0,
    voice_last_reset TEXT
)""")

c.execute('''CREATE TABLE IF NOT EXISTS shop(
    role_id INTEGER PRIMARY KEY,
    price INTEGER NOT NULL
)''')

c.execute('''CREATE TABLE IF NOT EXISTS mines(
    owner_id INTEGER,
    board TEXT,
    rows INTEGER,
    cols INTEGER,
    PRIMARY KEY(owner_id)
)''')
conn.commit()

db_lock = asyncio.Lock()

# ----------------- DB HELPERS -----------------
async def ensure_user(uid: int):
    async with db_lock:
        c.execute('SELECT user_id FROM users WHERE user_id=?', (uid,))
        if not c.fetchone():
            c.execute('INSERT INTO users(user_id,balance,last_daily,voice_today,voice_last_reset) VALUES(?,?,?,?,?)', (uid, START_BALANCE, '', 0, datetime.date.today().isoformat()))
            conn.commit()

async def get_balance(uid: int) -> int:
    await ensure_user(uid)
    async with db_lock:
        c.execute('SELECT balance FROM users WHERE user_id=?', (uid,))
        r = c.fetchone()
        return r[0] if r else START_BALANCE

async def change_balance(uid: int, amount: int):
    await ensure_user(uid)
    async with db_lock:
        c.execute('UPDATE users SET balance = balance + ? WHERE user_id=?', (amount, uid))
        conn.commit()

async def get_last_daily(uid: int):
    await ensure_user(uid)
    async with db_lock:
        c.execute('SELECT last_daily FROM users WHERE user_id=?', (uid,))
        r = c.fetchone()
        return r[0] if r else None

async def set_last_daily(uid: int, iso: str):
    await ensure_user(uid)
    async with db_lock:
        c.execute('UPDATE users SET last_daily = ? WHERE user_id=?', (iso, uid))
        conn.commit()

async def add_voice_earned(uid: int, earned: int):
    await ensure_user(uid)
    async with db_lock:
        c.execute('SELECT voice_today, voice_last_reset FROM users WHERE user_id=?', (uid,))
        row = c.fetchone()
        if row:
            voice_today, last_reset = row
            if last_reset != datetime.date.today().isoformat():
                voice_today = 0
            new_today = min(VOICE_DAILY_LIMIT, voice_today + earned)
            delta = new_today - voice_today
            if delta > 0:
                c.execute('UPDATE users SET voice_today=?, voice_last_reset=? WHERE user_id=?', (new_today, datetime.date.today().isoformat(), uid))
                c.execute('UPDATE users SET balance = balance + ? WHERE user_id=?', (delta, uid))
                conn.commit()
                return delta
        return 0

# ----------------- MINES DB -----------------
async def save_mine(owner_id: int, board, rows, cols):
    import json
    b = json.dumps(board)
    async with db_lock:
        c.execute('INSERT OR REPLACE INTO mines(owner_id, board, rows, cols) VALUES(?,?,?,?)', (owner_id, b, rows, cols))
        conn.commit()

async def load_mine(owner_id: int):
    import json
    async with db_lock:
        c.execute('SELECT board,rows,cols FROM mines WHERE owner_id=?', (owner_id,))
        r = c.fetchone()
    if not r:
        return None
    board = json.loads(r[0])
    return board, r[1], r[2]

# ----------------- VOICE TRACKING -----------------
voice_sessions = {}  # user_id -> (channel_id, join_ts)

@bot.event
async def on_voice_state_update(member, before, after):
    try:
        if member.bot:
            return
        uid = member.id
        # joined
        if before.channel is None and after.channel is not None:
            if VOICE_IGNORE_AFK and is_afk_channel(after.channel):
                return
            voice_sessions[uid] = (after.channel.id, time.time())
        # moved
        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            if uid in voice_sessions:
                _, ts = voice_sessions.pop(uid)
                duration = max(0, int(time.time() - ts))
                await process_voice_session(uid, duration)
            if VOICE_IGNORE_AFK and is_afk_channel(after.channel):
                return
            voice_sessions[uid] = (after.channel.id, time.time())
        # left
        elif before.channel is not None and after.channel is None:
            if uid in voice_sessions:
                _, ts = voice_sessions.pop(uid)
                duration = max(0, int(time.time() - ts))
                await process_voice_session(uid, duration)
    except Exception as e:
        print('voice update error', e)


def is_afk_channel(channel):
    try:
        if getattr(channel, 'category', None) and channel.category and channel.category.name in VOICE_AFK_CATEGORY_NAMES:
            return True
    except Exception:
        pass
    try:
        if getattr(channel.guild, 'afk_channel', None) and channel.guild.afk_channel and channel.guild.afk_channel.id == channel.id:
            return True
    except Exception:
        pass
    return False

async def process_voice_session(uid: int, duration_seconds: int):
    if duration_seconds < VOICE_MIN_SECONDS:
        return
    minutes = duration_seconds // 60
    earned = minutes * VOICE_COINS_PER_MIN
    got = await add_voice_earned(uid, earned)
    if got > 0:
        user = bot.get_user(uid)
        try:
            if user:
                await user.send(f'Вы получили **{got} {CURRENCY}** за {minutes} минут(ы) голосовой активности.')
        except Exception:
            pass

@tasks.loop(minutes=5)
async def flush_voice_sessions():
    now_ts = time.time()
    to_process = []
    for uid, (ch_id, ts) in list(voice_sessions.items()):
        if now_ts - ts >= 300:
            duration = int(now_ts - ts)
            to_process.append((uid, duration))
            voice_sessions[uid] = (ch_id, now_ts)
    for uid, duration in to_process:
        try:
            await process_voice_session(uid, duration)
        except Exception as e:
            print('flush error', e)

# ----------------- HELP -----------------
@bot.command(name='help')
async def help_cmd(ctx, command: str = None):
    prefix = PREFIX
    if not command:
        embed = discord.Embed(title='Помощь — команды бота', color=0x2F3136)
        embed.description = (
            f'Префикс команд: `{prefix}`\n'
            f'Валюта: {CURRENCY}\n\n'
            'Примеры: `!balance`, `!rps камень 50`, `!shop buy @Role`'
        )
        sections = {
            'Экономика': '`balance`, `daily`, `work`, `give`, `top`',
            'Магазин': '`shop` (add/buy/remove)',
            'Игры': '`coin`, `dice`, `slots`, `blackjack`, `race`, `minesweeper`, `rps`',
            'Голос': '`voiceinfo` — информация о начислениях за голосовую активность'
        }
        for k, v in sections.items():
            embed.add_field(name=k, value=v, inline=False)
        embed.set_footer(text='Напишите: !help <команда> для подробной информации')
        return await ctx.send(embed=embed)
    await ctx.send('Подробная помощь временно отключена — используйте `!help`')

# ----------------- ECONOMY -----------------
@bot.command(aliases=['bal','баланс'])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    bal = await get_balance(member.id)
    embed = discord.Embed(title='Баланс', color=0xFAA61A)
    embed.set_thumbnail(url=member.display_avatar.url if member else '')
    embed.add_field(name=member.display_name, value=f'{bal} {CURRENCY}', inline=True)
    embed.set_footer(text=f'Запросил: {ctx.author.display_name}')
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    uid = ctx.author.id
    last = await get_last_daily(uid)
    now = datetime.datetime.utcnow()
    if last:
        try:
            last_dt = datetime.datetime.fromisoformat(last)
            if now - last_dt < datetime.timedelta(hours=24):
                rem = datetime.timedelta(hours=24) - (now - last_dt)
                hours = rem.seconds // 3600
                mins = (rem.seconds % 3600) // 60
                return await ctx.send(f'Ежедневная уже взята. Подождите {hours}ч {mins}м')
        except Exception:
            pass
    await change_balance(uid, DAILY_AMOUNT)
    await set_last_daily(uid, now.isoformat())
    embed = discord.Embed(title='Daily получен!', description=f'Вы получили {DAILY_AMOUNT} {CURRENCY}', color=0x2ECC71)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text='Заходите снова через 24 часа')
    await ctx.send(embed=embed)

@bot.command()
async def work(ctx):
    amount = random.randint(WORK_MIN, WORK_MAX)
    await change_balance(ctx.author.id, amount)
    embed = discord.Embed(title='Работа завершена', color=0xF39C12)
    embed.add_field(name='Заработано', value=f'{amount} {CURRENCY}')
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send('Сумма должна быть положительной.')
    bal = await get_balance(ctx.author.id)
    if bal < amount:
        return await ctx.send('Недостаточно средств.')
    await change_balance(ctx.author.id, -amount)
    await change_balance(member.id, amount)
    embed = discord.Embed(title='Трансфер выполнен', color=0x57F287)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name='От', value=f'{ctx.author.display_name}', inline=True)
    embed.add_field(name='Кому', value=f'{member.display_name}', inline=True)
    embed.add_field(name='Сумма', value=f'{amount} {CURRENCY}', inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def top(ctx, limit: int = 10):
    limit = max(1, min(limit, MAX_TOP))
    async with db_lock:
        c.execute('SELECT user_id,balance FROM users ORDER BY balance DESC LIMIT ?', (limit,))
        rows = c.fetchall()
    embed = discord.Embed(title=f'TOP {limit} по балансу', color=0xFFD700)
    if not rows:
        embed.description = 'Пока нет пользователей в базе.'
        return await ctx.send(embed=embed)
    for i, (uid, bal) in enumerate(rows, start=1):
        member = ctx.guild.get_member(uid)
        name = member.display_name if member else str(uid)
        avatar = getattr(member, 'display_avatar', None)
        avatar_url = avatar.url if avatar else None
        embed.add_field(name=f'{i}. {name}', value=f'`{bal} {CURRENCY}`', inline=False)
        if i == 1 and avatar_url:
            embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text='Ники показываются как display_name на сервере')
    await ctx.send(embed=embed)

# ----------------- SHOP -----------------
@bot.command()
async def shop(ctx, action: str = None, role: discord.Role = None, price: int = None):
    if action is None:
        async with db_lock:
            c.execute('SELECT role_id, price FROM shop')
            rows = c.fetchall()
        embed = discord.Embed(title='Магазин ролей', color=0x7289DA)
        if not rows:
            embed.description = 'Магазин пуст.'
            return await ctx.send(embed=embed)
        for rid, p in rows:
            r = ctx.guild.get_role(rid)
            name = r.name if r else f'Роль ({rid}) — удалена'
            embed.add_field(name=name, value=f'{p} {CURRENCY}', inline=False)
        embed.set_footer(text=f'Купить: {PREFIX}shop buy @Role')
        return await ctx.send(embed=embed)

    if action == 'add':
        if not ctx.author.guild_permissions.manage_roles:
            return await ctx.send('Нужны права manage_roles')
        if not role or price is None:
            return await ctx.send('Использование: shop add @Role 500')
        async with db_lock:
            c.execute('INSERT OR REPLACE INTO shop(role_id,price) VALUES(?,?)', (role.id, price))
            conn.commit()
        return await ctx.send(embed=discord.Embed(description=f'Роль **{role.name}** добавлена за **{price} {CURRENCY}**', color=0x2ECC71))

    if action == 'buy':
        if not role:
            return await ctx.send('Укажите роль: shop buy @Role')
        async with db_lock:
            c.execute('SELECT price FROM shop WHERE role_id=?', (role.id,))
            r = c.fetchone()
        if not r:
            return await ctx.send('Эта роль не продаётся.')
        price = r[0]
        bal = await get_balance(ctx.author.id)
        if bal < price:
            return await ctx.send('Недостаточно средств.')
        await change_balance(ctx.author.id, -price)
        try:
            await ctx.author.add_roles(role)
        except Exception as e:
            await change_balance(ctx.author.id, price)
            return await ctx.send('Не удалось выдать роль: ' + str(e))
        return await ctx.send(embed=discord.Embed(description=f'{ctx.author.mention} купил роль **{role.name}** за **{price} {CURRENCY}**', color=0x57F287))

    if action == 'remove':
        if not ctx.author.guild_permissions.manage_roles:
            return await ctx.send('Нужны права manage_roles')
        if not role:
            return await ctx.send('Укажите роль: shop remove @Role')
        async with db_lock:
            c.execute('DELETE FROM shop WHERE role_id=?', (role.id,))
            conn.commit()
        return await ctx.send(embed=discord.Embed(description=f'Роль **{role.name}** удалена из магазина', color=0xE74C3C))

    await ctx.send('Неверное действие. Доступные: (без аргументов) показать, add, remove, buy')

# ----------------- GAMES -----------------
@bot.command(aliases=['монета'])
async def coin(ctx, guess: str = None, bet: int = 0):
    guess = (guess or '').lower()
    if guess and guess not in ('орёл','решка','heads','tails'):
        return await ctx.send('Угадайте `орёл` или `решка`. Пример: `!coin орёл 50`')
    if guess == 'орёл': guess = 'heads'
    if guess == 'решка': guess = 'tails'
    bet = max(0, bet)
    bal = await get_balance(ctx.author.id)
    if bet and bal < bet:
        return await ctx.send('Недостаточно средств для ставки')
    result = random.choice(['heads','tails'])
    res_text = 'орёл' if result=='heads' else 'решка'
    if bet:
        if guess and result == guess:
            await change_balance(ctx.author.id, bet)
            return await ctx.send(embed=discord.Embed(description=f'Выпало **{res_text}** — вы выиграли **{bet} {CURRENCY}**', color=0x2ECC71))
        else:
            await change_balance(ctx.author.id, -bet)
            return await ctx.send(embed=discord.Embed(description=f'Выпало **{res_text}** — вы проиграли **{bet} {CURRENCY}**', color=0xE74C3C))
    await ctx.send(embed=discord.Embed(description=f'Выпало **{res_text}**').set_footer(text='Используйте ставку: !coin орёл 50'))

@bot.command(aliases=['кубик'])
async def dice(ctx, sides: int = 6, bet: int = 0):
    sides = max(2, min(100, sides))
    bet = max(0, bet)
    bal = await get_balance(ctx.author.id)
    if bet and bal < bet:
        return await ctx.send('Недостаточно средств для ставки')
    result = random.randint(1, sides)
    if bet:
        if result == sides:
            win = bet * (sides//2)
            await change_balance(ctx.author.id, win)
            return await ctx.send(embed=discord.Embed(description=f'Выпало **{result}** — джекпот! Вы получили **{win} {CURRENCY}**', color=0x2ECC71))
        else:
            await change_balance(ctx.author.id, -bet)
            return await ctx.send(embed=discord.Embed(description=f'Выпало **{result}** — вы проиграли **{bet} {CURRENCY}**', color=0xE74C3C))
    await ctx.send(embed=discord.Embed(description=f'Выпало **{result}**'))

@bot.command(aliases=['слоты'])
async def slots(ctx, bet: int = 0):
    bet = max(0, bet)
    bal = await get_balance(ctx.author.id)
    if bet and bal < bet:
        return await ctx.send('Недостаточно средств для ставки')
    symbols = ['🍒','🍋','🍊','🔔','💎']
    r = [random.choice(symbols) for _ in range(3)]
    line = ' | '.join(r)
    if bet:
        if r[0]==r[1]==r[2]:
            win = bet * 5
            await change_balance(ctx.author.id, win)
            return await ctx.send(embed=discord.Embed(description=f'{line} — Вы выиграли **{win} {CURRENCY}**!', color=0x2ECC71))
        else:
            await change_balance(ctx.author.id, -bet)
            return await ctx.send(embed=discord.Embed(description=f'{line} — Вы проиграли **{bet} {CURRENCY}**', color=0xE74C3C))
    await ctx.send(embed=discord.Embed(description=line))

@bot.command(name='rps', aliases=['камень'])
async def rps_cmd(ctx, choice: str = None, bet: int = 0):
    choice = (choice or '').lower()
    mapping = {'r':'rock','p':'paper','s':'scissors','камень':'rock','ножницы':'scissors','бумага':'paper'}
    if choice in mapping:
        choice = mapping[choice]
    if choice not in ('rock','paper','scissors'):
        return await ctx.send('Выберите: `камень`, `ножницы` или `бумага`. Пример: `!rps камень 50`')
    bet = max(0, bet)
    bal = await get_balance(ctx.author.id)
    if bet and bal < bet:
        return await ctx.send('Недостаточно средств для ставки')
    bot_choice = random.choice(['rock','paper','scissors'])
    # animation (simple)
    try:
        anim = await ctx.send(' '.join(RPS_FRAMES))
        for _ in range(5):
            await asyncio.sleep(RPS_ANIM_DELAY)
            RPS_FRAMES.append(RPS_FRAMES.pop(0))
            try:
                await anim.edit(content=' '.join(RPS_FRAMES))
            except Exception:
                pass
    except Exception:
        pass
    await ctx.send(f'Вы: **{choice}**\nБот: **{bot_choice}**')
    if choice == bot_choice:
        outcome = 'tie'
    elif (choice=='rock' and bot_choice=='scissors') or (choice=='scissors' and bot_choice=='paper') or (choice=='paper' and bot_choice=='rock'):
        outcome = 'win'
    else:
        outcome = 'lose'
    if bet:
        if outcome=='win':
            await change_balance(ctx.author.id, bet)
            return await ctx.send(embed=discord.Embed(description=f'Вы выиграли **{bet} {CURRENCY}**', color=0x2ECC71))
        if outcome=='lose':
            await change_balance(ctx.author.id, -bet)
            return await ctx.send(embed=discord.Embed(description=f'Вы проиграли **{bet} {CURRENCY}**', color=0xE74C3C))
        return await ctx.send('Ничья — ставка возвращена.')
    else:
        texts = {'win':'Вы победили!','lose':'Вы проиграли.','tie':'Ничья.'}
        return await ctx.send(embed=discord.Embed(description=texts[outcome], color=0x5865F2))

@bot.command()
async def race(ctx, *members: discord.Member):
    if not members:
        return await ctx.send('Укажите хотя бы одного участника (упомяните). Пример: `!race @user1 @user2`')
    participants = [ctx.author] + list(dict.fromkeys(members))
    participants = participants[:6]
    positions = {p: 0 for p in participants}
    msg = await ctx.send('Старт гонки: ' + ' '.join(p.mention for p in participants))
    for _ in range(12):
        for p in participants:
            positions[p] += random.randint(0,2)
        line = '\n'.join(f'{p.display_name}: ' + '>'*positions[p] for p in participants)
        try:
            await msg.edit(content=line)
        except Exception:
            await msg.channel.send(line)
        await asyncio.sleep(0.6)
    winner = max(positions, key=positions.get)
    await ctx.send(f'Победитель — {winner.mention}!')

# ----------------- BLACKJACK -----------------
BLACKJACK_TIMEOUT = 60

class BJGame:
    def __init__(self, ctx, bet):
        self.ctx = ctx
        self.bet = bet
        deck = [2,3,4,5,6,7,8,9,10,10,10,10,11]*4
        random.shuffle(deck)
        self.deck = deck
        self.player = [self.deck.pop(), self.deck.pop()]
        self.dealer = [self.deck.pop(), self.deck.pop()]

    def total(self, cards):
        s = sum(cards)
        aces = cards.count(11)
        while s>21 and aces:
            s -= 10
            aces -= 1
        return s

    def player_text(self):
        return f'Ваши карты: {self.player} ({self.total(self.player)})'

    def dealer_text(self, reveal=False):
        if reveal:
            return f'Карты дилера: {self.dealer} ({self.total(self.dealer)})'
        return f'Карты дилера: [{self.dealer[0]}, ?]'

    def is_blackjack(self, cards):
        return self.total(cards) == 21 and len(cards) == 2

@bot.command(aliases=['блекджек'])
async def blackjack(ctx, bet: int = 0):
    bet = max(0, bet)
    bal = await get_balance(ctx.author.id)
    if bet and bal < bet:
        return await ctx.send('Недостаточно средств для ставки')
    game = BJGame(ctx, bet)
    if bet:
        await change_balance(ctx.author.id, -bet)
    try:
        dm = await ctx.author.create_dm()
        await dm.send('Начинаем блекджек! В DM отвечайте командами: `взять` или `стоять` (или `хит`/`стенд`) в течение 60 секунд.')
    except Exception:
        if bet:
            await change_balance(ctx.author.id, bet)
        return await ctx.send('Не удалось отправить личное сообщение. Включите приём личных сообщений от участников сервера.')

    if game.is_blackjack(game.player) and game.is_blackjack(game.dealer):
        if bet:
            await change_balance(ctx.author.id, bet)
        return await dm.send(game.player_text() + '\n' + game.dealer_text(reveal=True) + '\nНичья (оба Blackjack).')
    if game.is_blackjack(game.player):
        if bet:
            await change_balance(ctx.author.id, int(bet * 1.5))
        return await dm.send(game.player_text() + '\n' + game.dealer_text(reveal=True) + '\nBlackjack! Вы выиграли.')

    # player turn
    while True:
        await dm.send(game.player_text() + '\n' + game.dealer_text(reveal=False) + '\nНапишите `взять`/`хит` или `стоять`/`стенд`.')
        try:
            def check(m):
                return m.author == ctx.author and isinstance(m.channel, discord.DMChannel) and m.content.lower() in ('взять','хит','стоять','стенд')
            resp = await bot.wait_for('message', check=check, timeout=BLACKJACK_TIMEOUT)
        except asyncio.TimeoutError:
            if bet:
                await change_balance(ctx.author.id, bet)
            return await dm.send('Время вышло — игра отменена, ставка возвращена.')
        cmd = resp.content.lower()
        if cmd in ('взять','хит'):
            game.player.append(game.deck.pop())
            if game.total(game.player) > 21:
                return await dm.send(game.player_text() + '\nПеребор! Вы проиграли.')
            continue
        break

    while game.total(game.dealer) < 17:
        game.dealer.append(game.deck.pop())

    p = game.total(game.player)
    d = game.total(game.dealer)
    if p > 21:
        res = 'Вы проиграли.'
    elif d > 21 or p > d:
        res = 'Вы выиграли!'
        if bet:
            await change_balance(ctx.author.id, bet * 2)
    elif p == d:
        res = 'Ничья.'
        if bet:
            await change_balance(ctx.author.id, bet)
    else:
        res = 'Вы проиграли.'
    await dm.send(game.player_text() + '\n' + game.dealer_text(reveal=True) + '\n' + res)
    await ctx.send(f'{ctx.author.mention}, результаты блекджека отправлены в личные сообщения.')

# ----------------- MINESWEEPER -----------------
@bot.command(aliases=['сапёр','минесвипер'])
async def minesweeper(ctx, rows: int = 6, cols: int = 6, bombs: int = 8):
    rows = max(2, min(12, rows))
    cols = max(2, min(12, cols))
    bombs = max(1, min(rows*cols-1, bombs))
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    bombs_pos = set(random.sample(cells, bombs))

    def neighbors(r, c):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < rows and 0 <= cc < cols:
                    yield (rr, cc)

    board = [[-1 for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if (r, c) in bombs_pos:
                board[r][c] = 'B'
            else:
                board[r][c] = sum(1 for n in neighbors(r, c) if n in bombs_pos)

    await save_mine(ctx.author.id, board, rows, cols)
    header = '   ' + ' '.join(f'{i:2d}' for i in range(cols))
    lines = [header]
    for r in range(rows):
        line = f'{r:2d} ' + ' '.join('▢ ' for _ in range(cols))
        lines.append(line)
    lines.append('\nОткрыть: `!ms_open row col` — пример: `!ms_open 2 3`')
    await ctx.send('\n'.join(lines))

@bot.command()
async def ms_open(ctx, row: int, col: int):
    data = await load_mine(ctx.author.id)
    if not data:
        return await ctx.send('У вас нет сохранённого поля. Создайте с помощью `!minesweeper`')
    board, rows, cols = data
    if not (0 <= row < rows and 0 <= col < cols):
        return await ctx.send('Неверные координаты')
    if board[row][col] == 'B':
        out = ['   ' + ' '.join(f'{i:2d}' for i in range(cols))]
        for r in range(rows):
            out.append(f'{r:2d} ' + ' '.join('B ' if board[r][c] == 'B' else f'{board[r][c]} ' for c in range(cols)))
        async with db_lock:
            c.execute('DELETE FROM mines WHERE owner_id=?', (ctx.author.id,))
            conn.commit()
        return await ctx.send('\n'.join(out) + '\nВы подорвались! Поле удалено.')

    revealed = [[False] * cols for _ in range(rows)]
    q = deque()
    q.append((row, col))
    while q:
        r, c = q.popleft()
        if revealed[r][c]:
            continue
        revealed[r][c] = True
        if board[r][c] == 0:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < rows and 0 <= cc < cols and not revealed[rr][cc] and board[rr][cc] != 'B':
                        q.append((rr, cc))

    out = ['   ' + ' '.join(f'{i:2d}' for i in range(cols))]
    for r in range(rows):
        line = f'{r:2d} ' + ' '.join((f'{board[r][c]} ' if revealed[r][c] else '▢ ') for c in range(cols))
        out.append(line)
    await ctx.send('\n'.join(out))

# ----------------- VOICE INFO -----------------
@bot.command()
async def voiceinfo(ctx):
    embed = discord.Embed(title='Начисления за голосовую активность', color=0x3498DB)
    embed.add_field(name='Ставка', value=f'{VOICE_COINS_PER_MIN} {CURRENCY} / минута', inline=False)
    embed.add_field(name='Минимум оплачиваемого времени', value=f'{VOICE_MIN_SECONDS} секунд', inline=False)
    embed.add_field(name='Лимит в день', value=f'{VOICE_DAILY_LIMIT} {CURRENCY}', inline=False)
    embed.add_field(name='AFK-каналы исключены', value=str(VOICE_IGNORE_AFK), inline=False)
    await ctx.send(embed=embed)

# ----------------- STARTUP -----------------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (id: {bot.user.id})')
    if not flush_voice_sessions.is_running():
        flush_voice_sessions.start()

# ----------------- RUN -----------------
if __name__ == '__main__':
    bot.run(TOKEN)

