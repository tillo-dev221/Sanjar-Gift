import aiosqlite
from config import DB_PATH, ADMIN_ID


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance INTEGER DEFAULT 0,
                language TEXT DEFAULT 'uz',
                referal_code TEXT UNIQUE,
                refered_by INTEGER,
                referal_count INTEGER DEFAULT 0,
                referal_earned INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                emoji TEXT DEFAULT '🎁',
                color TEXT DEFAULT 'primary',
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                gift_id INTEGER NOT NULL,
                gift_name TEXT,
                gift_price INTEGER,
                recipient TEXT,
                status TEXT DEFAULT 'pending',
                receipt_file_id TEXT,
                admin_message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                channel_username TEXT,
                title TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                role TEXT DEFAULT 'admin',
                added_by INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

        await db.execute("""
            INSERT OR IGNORE INTO settings (key, value) VALUES
                ('card_number', '0000 0000 0000 0000'),
                ('card_owner', 'Admin'),
                ('referal_bonus', '1000'),
                ('referal_percent', '5'),
                ('min_topup', '5000'),
                ('support_username', 'Sanjarbek00011')
        """)
        await db.commit()

        await db.execute("""
            INSERT OR IGNORE INTO gifts (id, name, price, emoji, color, sort_order) VALUES
                (1, '13 stars', 2850, '💝', 'success', 1),
                (2, '13 stars', 2850, '🧸', 'primary', 2),
                (3, '21 stars', 4850, '🎁', 'danger', 3),
                (4, '21 stars', 4850, '🌹', 'warning', 4),
                (5, '43 stars', 9350, '🎂', 'success', 5),
                (6, '43 stars', 9350, '🚀', 'primary', 6),
                (7, '85 stars', 18500, '🏆', 'warning', 7),
                (8, '85 stars', 18500, '💍', 'danger', 8)
        """)
        await db.commit()

        async with db.execute("SELECT * FROM admins WHERE user_id = ?", (ADMIN_ID,)) as cursor:
            existing = await cursor.fetchone()

        if not existing:
            await db.execute("""
                INSERT INTO admins (user_id, username, full_name, role)
                VALUES (?, '', '', 'owner')
            """, (ADMIN_ID,))
            await db.commit()


async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()


async def create_user(user_id, username, full_name, referal_code, refered_by=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, full_name, referal_code, refered_by)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, full_name, referal_code, refered_by))
        await db.commit()


async def update_balance(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()


async def set_language(user_id, lang):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()


async def get_gifts():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM gifts WHERE is_active = 1 ORDER BY sort_order") as cursor:
            return await cursor.fetchall()


async def get_all_gifts():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM gifts ORDER BY sort_order") as cursor:
            return await cursor.fetchall()


async def get_gift(gift_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM gifts WHERE id = ?", (gift_id,)) as cursor:
            return await cursor.fetchone()


async def add_gift(name, price, emoji='🎁', color='primary'):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT MAX(sort_order) FROM gifts") as c:
            max_order = (await c.fetchone())[0] or 0
        cursor = await db.execute("""
            INSERT INTO gifts (name, price, emoji, color, sort_order)
            VALUES (?, ?, ?, ?, ?)
        """, (name, price, emoji, color, max_order + 1))
        await db.commit()
        return cursor.lastrowid


async def update_gift(gift_id, name=None, price=None, emoji=None, color=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if name is not None:
            await db.execute("UPDATE gifts SET name = ? WHERE id = ?", (name, gift_id))
        if price is not None:
            await db.execute("UPDATE gifts SET price = ? WHERE id = ?", (price, gift_id))
        if emoji is not None:
            await db.execute("UPDATE gifts SET emoji = ? WHERE id = ?", (emoji, gift_id))
        if color is not None:
            await db.execute("UPDATE gifts SET color = ? WHERE id = ?", (color, gift_id))
        await db.commit()


async def delete_gift(gift_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM gifts WHERE id = ?", (gift_id,))
        await db.commit()


async def toggle_gift(gift_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE gifts SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
            WHERE id = ?
        """, (gift_id,))
        await db.commit()


async def create_order(user_id, gift_id, gift_name, gift_price, recipient):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO orders (user_id, gift_id, gift_name, gift_price, recipient)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, gift_id, gift_name, gift_price, recipient))
        await db.commit()
        return cursor.lastrowid


async def get_order(order_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
            return await cursor.fetchone()


async def update_order_status(order_id, status, receipt_file_id=None, admin_message_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders SET status = ?, receipt_file_id = ?, admin_message_id = ?,
            processed_at = CURRENT_TIMESTAMP WHERE id = ?
        """, (status, receipt_file_id, admin_message_id, order_id))
        await db.commit()


async def get_setting(key):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()


async def get_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels") as cursor:
            return await cursor.fetchall()


async def add_channel(channel_id, channel_username, title):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO channels (channel_id, channel_username, title) VALUES (?, ?, ?)
        """, (channel_id, channel_username, title))
        await db.commit()


async def remove_channel(channel_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        await db.commit()


async def get_referals(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE refered_by = ?", (user_id,)) as cursor:
            return await cursor.fetchall()


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders") as c:
            orders = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'") as c:
            pending = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders WHERE status = 'approved'") as c:
            approved = (await c.fetchone())[0]
        async with db.execute("SELECT SUM(gift_price) FROM orders WHERE status = 'approved'") as c:
            total = (await c.fetchone())[0] or 0
        return {"users": users, "orders": orders, "pending": pending, "approved": approved, "total": total}


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as cursor:
            return await cursor.fetchall()


async def ban_user(user_id, banned=True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if banned else 0, user_id))
        await db.commit()


async def is_admin_user(user_id):
    if user_id == ADMIN_ID:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def get_admins():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins ORDER BY added_at") as cursor:
            return await cursor.fetchall()


async def add_admin(user_id, username, full_name, added_by):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO admins (user_id, username, full_name, role, added_by)
            VALUES (?, ?, ?, 'admin', ?)
        """, (user_id, username, full_name, added_by))
        await db.commit()


async def remove_admin(user_id):
    if user_id == ADMIN_ID:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ? AND role != 'owner'", (user_id,))
        await db.commit()
        return True


async def log_admin_action(admin_id, action, details=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO admin_log (admin_id, action, details)
            VALUES (?, ?, ?)
        """, (admin_id, action, details))
        await db.commit()


async def get_admin_log(limit=50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM admin_log ORDER BY created_at DESC LIMIT ?
        """, (limit,)) as cursor:
            return await cursor.fetchall()


async def get_owner():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins WHERE role = 'owner' LIMIT 1") as cursor:
            return await cursor.fetchone()


async def transfer_ownership(new_owner_id, new_owner_username, new_owner_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE admins SET role = 'admin' WHERE role = 'owner'")
        await db.execute("""
            INSERT OR REPLACE INTO admins (user_id, username, full_name, role)
            VALUES (?, ?, ?, 'owner')
        """, (new_owner_id, new_owner_username, new_owner_name))
        await db.commit()


async def update_admin_info(user_id, username, full_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE admins SET username = ?, full_name = ?
            WHERE user_id = ?
        """, (username, full_name, user_id))
        await db.commit()