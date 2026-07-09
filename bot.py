import discord
from discord.ext import commands
import asyncio, random, sqlite3, datetime, os

# ---------- CONFIG ----------
TOKEN = 'YOUR_BOT_TOKEN_HERE'  # <- замените на ваш токен
PREFIX = '!'
CURRENCY = '₵'
DB_PATH = 'economy.db'
DAILY_AMOUNT = 500
WORK_MIN, WORK_MAX = 50, 200
START_BALANCE = 100
RPS_FRAMES = ['✊', '✋', '✌️']
RPS_ANIM_DELAY = 0.5

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ---------- DATABASE ----------
if not os.path.exists(DB_PATH):
    open(DB_PATH, 'w').close()

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

# NOTE: sqlite3 does not accept parameter placeholders inside DDL statements for default values.
# Insert the START_BALANCE value directly into the CREATE TABLE SQL.
c.execute(f"""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT {START_BALANCE},
    last_daily TEXT
)""")

c.execute('''CREATE TABLE IF NOT EXISTS shop(
    role_id INTEGER PRIMARY KEY,
    price INTEGER NOT NULL
)''')
conn.commit()

db_lock = asyncio.Lock()

async def ensure_user(uid: int):
    async with db_lock:
        c.execute('SELECT user_id FROM users WHERE user_id=?', (uid,))
        if not c.fetchone():
            c.execute('INSERT INTO users(user_id,balance,last_daily) VALUES(?,?,?)', (uid, START_BALANCE, ''))
            conn.commit()

async def get_balance(uid: int) -> int:
    await ensure_user(uid)
    async with db_lock:
        c.execute('SELECT balance FROM users WHERE user_id=?', (uid,))
        return c.fetchone()[0]

async def change_balance(uid: int, amount: int):
    await ensure_user(uid)
    async with db_lock:
        c.execute('UPDATE users SET balance = balance + ? WHERE user_id=?', (amount, uid))
        conn.commit()

async def set_balance(uid: int, amount: int):
    await ensure_user(uid)
    async with db_lock:
        c.execute('UPDATE users SET balance = ? WHERE user_id=?', (amount, uid))
        conn.commit()

async def get_last_daily(uid: int):
    await ensure_user(uid)
    async with db_lock:
        c.execute('SELECT last_daily FROM users WHERE user_id=?', (uid,))
        return c.fetchone()[0]

async def set_last_daily(uid: int, iso: str):
    async with db_lock:
        c.execute('UPDATE users SET last_daily = ? WHERE user_id=?', (iso, uid))
        conn.commit()

# ---------- UTIL ----------
def mention(member):
    return member.mention if isinstance(member, discord.Member) else str(member)

# ---------- ECONOMY COMMANDS ----------
@bot.command(aliases=['bal'])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    bal = await get_balance(member.id)
    await ctx.send(f'{mention(member)} — {bal} {CURRENCY}')

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
    await ctx.send(f'{ctx.author.mention}, вы получили {DAILY_AMOUNT} {CURRENCY}!')

@bot.command()
async def work(ctx):
    amount = random.randint(WORK_MIN, WORK_MAX)
    await change_balance(ctx.author.id, amount)
    await ctx.send(f'{ctx.author.mention} поработал и получил {amount} {CURRENCY}')

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send('Сумма должна быть положительной.')
    bal = await get_balance(ctx.author.id)
    if bal < amount:
        return await ctx.send('Недостаточно средств.')
    await change_balance(ctx.author.id, -amount)
    await change_balance(member.id, amount)
    await ctx.send(f'{ctx.author.mention} отправил {amount} {CURRENCY} {member.mention}')

@bot.command()
async def top(ctx, limit: int = 10):
    async with db_lock:
        c.execute('SELECT user_id,balance FROM users ORDER BY balance DESC LIMIT ?', (limit,))
        rows = c.fetchall()
    if not rows:
        return await ctx.send('Никто не в базе.')
    lines = []
    for i,(uid,b) in enumerate(rows, start=1):
        user = bot.get_user(uid)
        name = user.name if user else str(uid)
        lines.append(f'{i}. {name} — {b} {CURRENCY}')
    await ctx.send('\n'.join(lines))

# ---------- SHOP (roles) ----------
@bot.command()
async def shop(ctx, action: str = None, role: discord.Role = None, price: int = None):
    if action is None:
        async with db_lock:
            c.execute('SELECT role_id, price FROM shop')
            rows = c.fetchall()
        if not rows:
            return await ctx.send('Магазин пуст.')
        lines = []
        for rid, p in rows:
            r = ctx.guild.get_role(rid)
            if r:
                lines.append(f'{r.name} — {p} {CURRENCY}')
        return await ctx.send('\n'.join(lines) or 'Магазин пуст.')

    if action == 'add':
        if not ctx.author.guild_permissions.manage_roles:
            return await ctx.send('Нужны права manage_roles')
        if not role or price is None:
            return await ctx.send('Использование: shop add @role price')
        async with db_lock:
            c.execute('INSERT OR REPLACE INTO shop(role_id,price) VALUES(?,?)', (role.id, price))
            conn.commit()
        return await ctx.send(f'Роль {role.name} добавлена за {price} {CURRENCY}')

    if action == 'buy':
        if not role:
            return await ctx.send('Укажите роль для покупки: shop buy @role')
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
            await ctx.send('Не удалось выдать роль: ' + str(e))
            await change_balance(ctx.author.id, price)
            return
        await ctx.send(f'{ctx.author.mention} купил роль {role.name} за {price} {CURRENCY}')

    elif action == 'remove':
        if not ctx.author.guild_permissions.manage_roles:
            return await ctx.send('Нужны права manage_roles')
        if not role:
            return await ctx.send('Укажите роль: shop remove @role')
        async with db_lock:
            c.execute('DELETE FROM shop WHERE role_id=?', (role.id,))
            conn.commit()
        return await ctx.send(f'Роль {role.name} удалена из магазина.')

    await ctx.send('Неверное действие. Доступные: (без аргументов) показать, add, remove, buy')

# ---------- GAMES ----------
@bot.command()
async def coin(ctx, guess: str = None, bet: int = 0):
    guess = (guess or '').lower()
    if guess not in ('heads','tails',''):
        return await ctx.send('Угадайте heads или tails')
    bet = max(0, bet)
    bal = await get_balance(ctx.author.id)
    if bet and bal < bet:
        return await ctx.send('Недостаточно средств для ставки')
    result = random.choice(['heads','tails'])
    win = (result == guess) if guess else None
    if bet and win is not None:
        if win:
            await change_balance(ctx.author.id, bet)
            return await ctx.send(f'Выпало {result}. Вы выиграли {bet} {CURRENCY}!')
        else:
            await change_balance(ctx.author.id, -bet)
            return await ctx.send(f'Выпало {result}. Вы проиграли {bet} {CURRENCY}.')
    await ctx.send(f'Выпало {result}.')

@bot.command()
async def dice(ctx, sides: int = 6, bet: int = 0):
    sides = max(2, min(100, sides))
    bet = max(0, bet)
    bal = await get_balance(ctx.author.id)
    if bet and bal < bet:
        return await ctx.send('Недостаточно средств для ставки')
    result = random.randint(1, sides)
    if bet:
        # простая ставка: выигрыш если выпало max
        if result == sides:
            await change_balance(ctx.author.id, bet * (sides//2))
            return await ctx.send(f'Выпало {result} — джекпот! Вы получили {bet * (sides//2)} {CURRENCY}')
        else:
            await change_balance(ctx.author.id, -bet)
            return await ctx.send(f'Выпало {result}. Вы проиграли {bet} {CURRENCY}.')
    await ctx.send(f'Выпало {result}.')

@bot.command()
async def slots(ctx, bet: int = 0):
    bet = max(0, bet)
    bal = await get_balance(ctx.author.id)
    if bet and bal < bet:
        return await ctx.send('Недостаточно средств для ставки')
    symbols = ['🍒','🍋','🍊','🔔','💎']
    r = [random.choice(symbols) for _ in range(3)]
    if bet:
        if r[0]==r[1]==r[2]:
            win = bet * 5
            await change_balance(ctx.author.id, win)
            return await ctx.send(' | '.join(r) + f' — Вы выиграли {win} {CURRENCY}!')
        else:
            await change_balance(ctx.author.id, -bet)
            return await ctx.send(' | '.join(r) + f' — Вы проиграли {bet} {CURRENCY}.')
    await ctx.send(' | '.join(r))

# Simple blackjack (player vs dealer) — text-only, single round
@bot.command()
async def blackjack(ctx, bet: int = 0):
    bet = max(0, bet)
    bal = await get_balance(ctx.author.id)
    if bet and bal < bet:
        return await ctx.send('Недостаточно средств для ставки')
    deck = [2,3,4,5,6,7,8,9,10,10,10,10,11]*4
    random.shuffle(deck)
    def total(cards):
        s = sum(cards)
        aces = cards.count(11)
        while s>21 and aces:
            s-=10; aces-=1
        return s
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]
    # simple auto-play: player hits while <17
    while total(player)<17:
        player.append(deck.pop())
    while total(dealer)<17:
        dealer.append(deck.pop())
    p = total(player); d = total(dealer)
    if bet:
        if p>21 or (d<=21 and d>p):
            await change_balance(ctx.author.id, -bet)
            res = f'Вы проиграли {bet} {CURRENCY}.'
        elif d>21 or p>d:
            await change_balance(ctx.author.id, bet)
            res = f'Вы выиграли {bet} {CURRENCY}!' 
        else:
            res = 'Ничья.'
        await ctx.send(f'Ваши карты: {player} ({p})\nКарты дилера: {dealer} ({d})\n{res}')
    else:
        await ctx.send(f'Ваши карты: {player} ({p})\nКарты дилера: {dealer} ({d})')

# Race — несколько участников ставят, случайный победитель получает общий банк
@bot.command()
async def race(ctx, *members: discord.Member):
    if not members:
        return await ctx.send('Укажите хотя бы одного участника (упомяните).')
    participants = [ctx.author] + list(dict.fromkeys(members))
    participants = participants[:6]
    positions = {p: 0 for p in participants}
    # simple simulation
    msg = await ctx.send('Старт гонки: ' + ' '.join(p.mention for p in participants))
    for i in range(12):
        for p in participants:
            positions[p] += random.randint(0,2)
        line = '\n'.join(f'{p.display_name}: ' + '>'*positions[p] for p in participants)
        await msg.edit(content=line)
        await asyncio.sleep(0.6)
    winner = max(positions, key=positions.get)
    await ctx.send(f'Победитель — {winner.mention}!')

# Minesweeper — generate a simple field and allow reveal by coords via command
@bot.command()
async def minesweeper(ctx, rows: int = 6, cols: int = 6, bombs: int = 8):
    rows = max(2, min(9, rows))
    cols = max(2, min(9, cols))
    bombs = max(1, min(rows*cols-1, bombs))
    # place bombs
    cells = [(r,c) for r in range(rows) for c in range(cols)]
    bombs_pos = set(random.sample(cells, bombs))
    def neighbors(r,c):
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr==0 and dc==0: continue
                rr,cc = r+dr, c+dc
                if 0<=rr<rows and 0<=cc<cols:
                    yield (rr,cc)
    # build numbers
    board = [['B' if (r,c) in bombs_pos else 0 for c in range(cols)] for r in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if board[r][c]=='B': continue
            board[r][c] = sum(1 for n in neighbors(r,c) if n in bombs_pos)
    # show masked board with coordinates
    header = '   ' + ' '.join(f'{i:2d}' for i in range(cols))
    lines = [header]
    for r in range(rows):
        line = f'{r:2d} ' + ' '.join('▢ ' for _ in range(cols))
        lines.append(line)
    lines.append('\nЧтобы открыть клетку используйте: ms open row col')
    await ctx.send('\n'.join(lines))
    # store board for user in memory (simple, not persistent)
    if not hasattr(bot, 'ms_boards'):
        bot.ms_boards = {}
    bot.ms_boards[ctx.author.id] = board

@bot.command()
async def ms_open(ctx, row: int, col: int):
    if not hasattr(bot, 'ms_boards') or ctx.author.id not in bot.ms_boards:
        return await ctx.send('У вас нет активного поля. Создайте: minesweeper')
    board = bot.ms_boards[ctx.author.id]
    rows = len(board); cols = len(board[0])
    if not (0<=row<rows and 0<=col<cols):
        return await ctx.send('Неверные координаты')
    val = board[row][col]
    if val=='B':
        # reveal all
        lines = ['   ' + ' '.join(f'{i:2d}' for i in range(cols))]
        for r in range(rows):
            line = f'{r:2d} ' + ' '.join('B ' if board[r][c]=='B' else f'{board[r][c]} ' for c in range(cols))
            lines.append(line)
        del bot.ms_boards[ctx.author.id]
        return await ctx.send('\n'.join(lines) + '\nВы подорвались!')
    # reveal single cell (no flood-fill for simplicity)
    lines = ['   ' + ' '.join(f'{i:2d}' for i in range(cols))]
    for r in range(rows):
        line = f'{r:2d} ' + ' '.join(('▢ ' if not (r==row and c==col) else f'{board[row][col]} ') for c in range(cols))
        lines.append(line)
    await ctx.send('\n'.join(lines))

# RPS with animation and betting
@bot.command(name='rps')
async def rps(ctx, choice: str = None, bet: int = 0):
    choice = (choice or '').lower()
    if choice not in ('rock','paper','scissors','r','p','s'):
        return await ctx.send('Выберите: rock/paper/scissors')
    mapping = {'r':'rock','p':'paper','s':'scissors'}
    if choice in mapping: choice = mapping[choice]
    bet = max(0, bet)
    bal = await get_balance(ctx.author.id)
    if bet and bal < bet:
        return await ctx.send('Недостаточно средств для ставки')
    bot_choice = random.choice(['rock','paper','scissors'])
    anim_msg = await ctx.send(''.join(RPS_FRAMES))
    # simple animation: rotate frames
    for _ in range(4):
        await asyncio.sleep(RPS_ANIM_DELAY)
        RPS_FRAMES.append(RPS_FRAMES.pop(0))
        await anim_msg.edit(content=' '.join(RPS_FRAMES))
    await anim_msg.edit(content=f'Вы: {choice} \nБот: {bot_choice}')
    outcome = None
    if choice == bot_choice:
        outcome = 'tie'
    elif (choice=='rock' and bot_choice=='scissors') or (choice=='scissors' and bot_choice=='paper') or (choice=='paper' and bot_choice=='rock'):
        outcome = 'win'
    else:
        outcome = 'lose'
    if bet:
        if outcome=='win':
            await change_balance(ctx.author.id, bet)
            await ctx.send(f'Вы выиграли {bet} {CURRENCY}!')
        elif outcome=='lose':
            await change_balance(ctx.author.id, -bet)
            await ctx.send(f'Вы проиграли {bet} {CURRENCY}.')
        else:
            await ctx.send('Ничья — ставка возвращена.')
    else:
        await ctx.send({'win':'Вы победили!','lose':'Вы проиграли.','tie':'Ничья.'}[outcome])

# ---------- READY ----------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (id: {bot.user.id})')
    print('------')

# ---------- RUN ----------
if __name__ == '__main__':
    bot.run(TOKEN)
