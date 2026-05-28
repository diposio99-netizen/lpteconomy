FILES = {

════════════════════════════════════════════════════════════════

“requirements.txt”: “””
discord.py==2.3.2
aiosqlite==0.19.0
python-dotenv==1.0.0
Pillow==10.2.0
“”“,

════════════════════════════════════════════════════════════════

”.env”: “””
DISCORD_TOKEN=ВАШ_ТОКЕН_ЗДЕСЬ
PREFIX=!
OWNER_ID=ВАШ_DISCORD_ID
“”“,

════════════════════════════════════════════════════════════════

“config.py”: “””
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN     = os.getenv(‘DISCORD_TOKEN’)
PREFIX    = os.getenv(‘PREFIX’, ‘!’)
OWNER_ID  = int(os.getenv(‘OWNER_ID’, 0))
DB_PATH   = ‘database/bot.db’

STARTING_BALANCE  = 100
DAILY_REWARD      = 500
WEEKLY_REWARD     = 2500
WORK_COOLDOWN     = 3600
WORK_MIN          = 50
WORK_MAX          = 200

MSG_COOLDOWN      = 45
MSG_REWARD_MIN    = 1
MSG_REWARD_MAX    = 8
MSG_BONUS_LENGTH  = 80
MSG_BONUS_AMOUNT  = 3
VOICE_INTERVAL    = 5
VOICE_BASE        = 10
VOICE_MULTI_BONUS = 2
VOICE_ALONE_MULT  = 0.3

ROLE_CREATE_COST  = 1000
ROLE_EDIT_COST    = 250

COLOR_SUCCESS = 0x2ecc71
COLOR_ERROR   = 0xe74c3c
COLOR_INFO    = 0x3498db
COLOR_GOLD    = 0xf1c40f
COLOR_PURPLE  = 0x9b59b6
COLOR_ORANGE  = 0xe67e22

RARITY_DATA = {
    ‘common’:    {‘color’: 0x95a5a6, ‘label’: ‘⬜ Обычный’,    ‘emoji’: ‘⬜’},
    ‘rare’:      {‘color’: 0x3498db, ‘label’: ‘🟦 Редкий’,      ‘emoji’: ‘🟦’},
    ‘epic’:      {‘color’: 0x9b59b6, ‘label’: ‘🟪 Эпический’,   ‘emoji’: ‘🟪’},
    ‘legendary’: {‘color’: 0xf1c40f, ‘label’: ‘🟨 Легендарный’, ‘emoji’: ‘🟨’},
}

JOBS = {
    ‘cashier’: {
        ‘name’: ‘💵 Кассир’, ‘desc’: ‘Работа в супермаркете’,
        ‘min’: 40,  ‘max’: 90,  ‘cooldown’: 3600,
        ‘xp_reward’: 10, ‘level_up_xp’: 100, ‘max_level’: 5,
        ‘events’: [
            (‘normal’,  80, ‘Спокойная смена’),
            (‘bonus’,   12, ‘Благодарный покупатель дал чаевые! +30%’),
            (‘penalty’,  8, ‘Пробил лишний товар, вычли из зарплаты… -20%’),
        ]
    },
    ‘programmer’: {
        ‘name’: ‘👨\u200d💻 Программист’, ‘desc’: ‘Пишешь код за деньги’,
        ‘min’: 100, ‘max’: 250, ‘cooldown’: 5400,
        ‘xp_reward’: 20, ‘level_up_xp’: 150, ‘max_level’: 5,
        ‘events’: [
            (‘normal’,  70, ‘Сдал задачу вовремя’),
            (‘bonus’,   20, ‘Клиент доволен, выплатил бонус! +40%’),
            (‘penalty’, 10, ‘Баг в продакшене, штраф… -25%’),
        ]
    },
    ‘driver’: {
        ‘name’: ‘🚕 Таксист’, ‘desc’: ‘Возишь пассажиров’,
        ‘min’: 60,  ‘max’: 140, ‘cooldown’: 3600,
        ‘xp_reward’: 12, ‘level_up_xp’: 120, ‘max_level’: 5,
        ‘events’: [
            (‘normal’,  75, ‘Обычная поездка’),
            (‘bonus’,   15, ‘VIP-клиент дал щедрые чаевые! +35%’),
            (‘penalty’, 10, ‘Штраф за парковку… -15%’),
        ]
    },
    ‘doctor’: {
        ‘name’: ‘👨\u200d⚕️ Врач’, ‘desc’: ‘Лечишь пациентов’,
        ‘min’: 150, ‘max’: 350, ‘cooldown’: 7200,
        ‘xp_reward’: 30, ‘level_up_xp’: 200, ‘max_level’: 5,
        ‘events’: [
            (‘normal’,  65, ‘Обычный приём’),
            (‘bonus’,   25, ‘Благодарный пациент принёс подарок! +50%’),
            (‘penalty’, 10, ‘Перерасход медикаментов… -20%’),
        ]
    },
    ‘miner’: {
        ‘name’: ‘⛏️ Шахтёр’, ‘desc’: ‘Добываешь ресурсы’,
        ‘min’: 70,  ‘max’: 180, ‘cooldown’: 4200,
        ‘xp_reward’: 15, ‘level_up_xp’: 130, ‘max_level’: 5,
        ‘events’: [
            (‘normal’,  70, ‘Обычная смена’),
            (‘bonus’,   20, ‘Нашёл редкую жилу! +45%’),
            (‘penalty’, 10, ‘Сломал инструмент… -20%’),
        ]
    },
    ‘chef’: {
        ‘name’: ‘👨\u200d🍳 Шеф-повар’, ‘desc’: ‘Готовишь в ресторане’,
        ‘min’: 80,  ‘max’: 200, ‘cooldown’: 4800,
        ‘xp_reward’: 18, ‘level_up_xp’: 140, ‘max_level’: 5,
        ‘events’: [
            (‘normal’,  72, ‘Отличный ужин’),
            (‘bonus’,   18, ‘Ресторан получил хороший отзыв! +40%’),
            (‘penalty’, 10, ‘Пережарил блюдо, вычет… -15%’),
        ]
    },
    ‘lawyer’: {
        ‘name’: ‘⚖️ Юрист’, ‘desc’: ‘Ведёшь дела в суде’,
        ‘min’: 200, ‘max’: 500, ‘cooldown’: 10800,
        ‘xp_reward’: 40, ‘level_up_xp’: 250, ‘max_level’: 5,
        ‘events’: [
            (‘normal’,  60, ‘Выиграл дело’),
            (‘bonus’,   28, ‘Крупный клиент, огромный гонорар! +60%’),
            (‘penalty’, 12, ‘Проиграл дело, репутация пострадала… -30%’),
        ]
    },
    ‘streamer’: {
        ‘name’: ‘🎮 Стример’, ‘desc’: ‘Стримишь в интернете’,
        ‘min’: 30,  ‘max’: 300, ‘cooldown’: 3600,
        ‘xp_reward’: 10, ‘level_up_xp’: 100, ‘max_level’: 5,
        ‘events’: [
            (‘normal’,  65, ‘Обычный стрим’),
            (‘bonus’,   25, ‘Донат от зрителя! +70%’),
            (‘penalty’, 10, ‘Технические проблемы, зрители ушли… -10%’),
        ]
    },
}
“”“,

════════════════════════════════════════════════════════════════

“database/schema.sql”: “””
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    balance     INTEGER DEFAULT 0,
    bank        INTEGER DEFAULT 0,
    last_work   INTEGER DEFAULT 0,
    last_daily  INTEGER DEFAULT 0,
    last_weekly INTEGER DEFAULT 0,
    created_at  INTEGER DEFAULT (strftime(‘%s’,‘now’))
);

CREATE TABLE IF NOT EXISTS activity (
    user_id         INTEGER PRIMARY KEY,
    messages_count  INTEGER DEFAULT 0,
    voice_minutes   INTEGER DEFAULT 0,
    last_message_ts INTEGER DEFAULT 0,
    streak_days     INTEGER DEFAULT 0,
    last_streak_ts  INTEGER DEFAULT 0,
    total_earned    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS voice_sessions (
    user_id    INTEGER PRIMARY KEY,
    joined_at  INTEGER NOT NULL,
    channel_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS shop_items (
    item_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT,
    price       INTEGER NOT NULL,
    item_type   TEXT    NOT NULL,
    role_id     INTEGER,
    emoji       TEXT    DEFAULT ‘📦’,
    stock       INTEGER DEFAULT -1
);

CREATE TABLE IF NOT EXISTS inventory (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL,
    item_id  INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    FOREIGN KEY (item_id) REFERENCES shop_items(item_id)
);

CREATE TABLE IF NOT EXISTS cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL,
    price   INTEGER NOT NULL,
    emoji   TEXT    DEFAULT ‘🎁’
);

CREATE TABLE IF NOT EXISTS case_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id      INTEGER NOT NULL,
    item_name    TEXT    NOT NULL,
    rarity       TEXT    NOT NULL,
    reward_type  TEXT    NOT NULL,
    reward_value TEXT    NOT NULL,
    weight       INTEGER DEFAULT 100,
    FOREIGN KEY (case_id) REFERENCES cases(case_id)
);

CREATE TABLE IF NOT EXISTS custom_roles (
    user_id   INTEGER PRIMARY KEY,
    role_id   INTEGER NOT NULL,
    role_name TEXT    NOT NULL,
    color_hex TEXT    DEFAULT ‘#ffffff’
);

CREATE TABLE IF NOT EXISTS user_jobs (
    user_id  INTEGER PRIMARY KEY,
    job_id   TEXT    NOT NULL,
    level    INTEGER DEFAULT 1,
    xp       INTEGER DEFAULT 0,
    hired_at INTEGER DEFAULT (strftime(‘%s’,‘now’))
);

CREATE TABLE IF NOT EXISTS job_history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL,
    job_id    TEXT    NOT NULL,
    earned    INTEGER NOT NULL,
    event     TEXT,
    worked_at INTEGER DEFAULT (strftime(‘%s’,‘now’))
);

CREATE TABLE IF NOT EXISTS multipliers (
    role_id    INTEGER PRIMARY KEY,
    multiplier REAL    DEFAULT 1.0,
    label      TEXT
);

INSERT OR IGNORE INTO shop_items (name, description, price, item_type, emoji) VALUES
    (‘Зелье удачи’,  ‘Увеличивает шанс редкостей на 1 час’, 300,  ‘item’, ‘🧪’),
    (‘VIP-значок’,   ‘Престижный значок в профиле’,          800,  ‘item’, ‘⭐’),
    (‘Кейс новичка’, ‘Твой первый кейс!’,                    200,  ‘case’, ‘📦’);

INSERT OR IGNORE INTO cases (name, price, emoji) VALUES
    (‘Новичок’,  200, ‘📦’),
    (‘Премиум’,  500, ‘💎’),
    (‘Легенда’, 1500, ‘👑’);

INSERT OR IGNORE INTO case_items (case_id, item_name, rarity, reward_type, reward_value, weight) VALUES
    (1, ‘50 монет’,    ‘common’,    ‘coins’, ‘50’,    60),
    (1, ‘150 монет’,   ‘rare’,      ‘coins’, ‘150’,   25),
    (1, ‘500 монет’,   ‘epic’,      ‘coins’, ‘500’,   12),
    (1, ‘1500 монет’,  ‘legendary’, ‘coins’, ‘1500’,   3),
    (2, ‘200 монет’,   ‘common’,    ‘coins’, ‘200’,   55),
    (2, ‘600 монет’,   ‘rare’,      ‘coins’, ‘600’,   28),
    (2, ‘1500 монет’,  ‘epic’,      ‘coins’, ‘1500’,  14),
    (2, ‘5000 монет’,  ‘legendary’, ‘coins’, ‘5000’,   3),
    (3, ‘500 монет’,   ‘common’,    ‘coins’, ‘500’,   50),
    (3, ‘2000 монет’,  ‘rare’,      ‘coins’, ‘2000’,  30),
    (3, ‘7000 монет’,  ‘epic’,      ‘coins’, ‘7000’,  15),
    (3, ‘25000 монет’, ‘legendary’, ‘coins’, ‘25000’,  5);
“”“,

════════════════════════════════════════════════════════════════

“database/db.py”: “””
import aiosqlite
import config

async def init_db():
    async with aiosqlite.connect(config.DB_PATH) as db:
        with open(‘database/schema.sql’, encoding=‘utf-8’) as f:
            await db.executescript(f.read())
        await db.commit()

async def get_user(user_id: int) -> dict:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(‘SELECT * FROM users WHERE user_id=?’, (user_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            await db.execute(
                ‘INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)’,
                (user_id, config.STARTING_BALANCE)
            )
            await db.execute(‘INSERT OR IGNORE INTO activity (user_id) VALUES (?)’, (user_id,))
            await db.commit()
            return {‘user_id’: user_id, ‘balance’: config.STARTING_BALANCE,
                    ‘bank’: 0, ‘last_work’: 0, ‘last_daily’: 0, ‘last_weekly’: 0}
        return dict(row)

async def get_balance(user_id: int) -> tuple:
    user = await get_user(user_id)
    return user[‘balance’], user[‘bank’]

async def update_balance(user_id: int, amount: int):
    await get_user(user_id)
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(‘UPDATE users SET balance=balance+? WHERE user_id=?’, (amount, user_id))
        await db.commit()

async def get_multiplier(guild, member) -> float:
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(‘SELECT role_id, multiplier FROM multipliers’) as cur:
            rows = await cur.fetchall()
    role_ids = {r.id for r in member.roles}
    mult = 1.0
    for role_id, multiplier in rows:
        if role_id in role_ids:
            mult = max(mult, multiplier)
    return mult

async def get_shop_items() -> list:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(‘SELECT * FROM shop_items’) as cur:
            return [dict® for r in await cur.fetchall()]

async def add_to_inventory(user_id: int, item_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            ‘SELECT id FROM inventory WHERE user_id=? AND item_id=?’, (user_id, item_id)
        ) as cur:
            row = await cur.fetchone()
        if row:
            await db.execute(‘UPDATE inventory SET quantity=quantity+1 WHERE id=?’, (row[0],))
        else:
            await db.execute(‘INSERT INTO inventory (user_id,item_id) VALUES (?,?)’, (user_id, item_id))
        await db.commit()

async def get_inventory(user_id: int) -> list:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            ‘SELECT s.name,s.emoji,s.description,i.quantity FROM inventory i ’
            ‘JOIN shop_items s ON s.item_id=i.item_id WHERE i.user_id=?’, (user_id,)
        ) as cur:
            return [dict® for r in await cur.fetchall()]

async def get_cases() -> list:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(‘SELECT * FROM cases’) as cur:
            return [dict® for r in await cur.fetchall()]

async def get_case_items(case_id: int) -> list:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(‘SELECT * FROM case_items WHERE case_id=?’, (case_id,)) as cur:
            return [dict® for r in await cur.fetchall()]

async def get_activity(user_id: int) -> dict:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(‘SELECT * FROM activity WHERE user_id=?’, (user_id,)) as cur:
            row = await cur.fetchone()
    if not row:
        return {‘user_id’: user_id, ‘messages_count’: 0, ‘voice_minutes’: 0,
                ‘streak_days’: 0, ‘total_earned’: 0}
    return dict(row)

async def add_earned(user_id: int, amount: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(‘UPDATE users SET balance=balance+? WHERE user_id=?’, (amount, user_id))
        await db.execute(
            ‘INSERT INTO activity (user_id,total_earned) VALUES (?,?) ’
            ‘ON CONFLICT(user_id) DO UPDATE SET total_earned=total_earned+?’,
            (user_id, amount, amount)
        )
        await db.commit()

async def get_user_job(user_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(‘SELECT * FROM user_jobs WHERE user_id=?’, (user_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None

async def save_job_history(user_id: int, job_id: str, earned: int, event: str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            ‘INSERT INTO job_history (user_id,job_id,earned,event) VALUES (?,?,?,?)’,
            (user_id, job_id, earned, event)
        )
        await db.execute(
            ‘DELETE FROM job_history WHERE user_id=? AND id NOT IN ’
            ‘(SELECT id FROM job_history WHERE user_id=? ORDER BY id DESC LIMIT 20)’,
            (user_id, user_id)
        )
        await db.commit()

async def get_leaderboard(limit: int = 10) -> list:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            ‘SELECT user_id, balance+bank AS total FROM users ORDER BY total DESC LIMIT ?’,
            (limit,)
        ) as cur:
            return [dict® for r in await cur.fetchall()]
“”“,

════════════════════════════════════════════════════════════════

“utils/animations.py”: “””
import asyncio, random
import discord

async def loading_bar
