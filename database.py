import secrets
from datetime import datetime, timedelta
import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.execute(
            "CREATE TABLE IF NOT EXISTS services "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT, "
            "price INTEGER NOT NULL, active INTEGER DEFAULT 1, category_id INTEGER, image_file_id TEXT, "
            "delivery_mode TEXT DEFAULT 'manual', required_referrals INTEGER DEFAULT 0, "
            "requires_email INTEGER DEFAULT 0, referral_deadline_days INTEGER DEFAULT 0)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS users "
            "(id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, phone TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, language TEXT DEFAULT 'uz', "
            "referral_code TEXT, referred_by INTEGER, is_blocked INTEGER DEFAULT 0)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS orders "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, service_id INTEGER NOT NULL, "
            "service_name TEXT NOT NULL, price INTEGER NOT NULL, status TEXT DEFAULT 'payment_waiting', "
            "note TEXT, receipt_file_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, discount INTEGER DEFAULT 0, "
            "final_price INTEGER, coupon_code TEXT, customer_email TEXT, "
            "required_referrals INTEGER DEFAULT 0, current_referrals INTEGER DEFAULT 0, "
            "referral_status TEXT DEFAULT 'not_required', referral_code TEXT, referral_link TEXT, "
            "referral_deadline_at TEXT, activation_status TEXT DEFAULT 'pending', "
            "activation_ready_at TEXT, activated_at TEXT)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS categories "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS reviews "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, user_id INTEGER NOT NULL, "
            "service_id INTEGER NOT NULL, rating INTEGER NOT NULL, comment TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS coupons "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, "
            "discount_percent INTEGER NOT NULL, max_uses INTEGER NOT NULL, "
            "used_count INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1, "
            "service_id INTEGER, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS bonus_log "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
            "amount INTEGER NOT NULL, type TEXT NOT NULL, description TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS promos "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, "
            "text TEXT, image_file_id TEXT, url TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS service_promotions "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, service_id INTEGER NOT NULL, "
            "title TEXT, cashback_percent REAL NOT NULL, is_active INTEGER DEFAULT 1, "
            "starts_at TIMESTAMP, ends_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "FOREIGN KEY(service_id) REFERENCES services(id))"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS subscriptions "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
            "service_id INTEGER, end_date TIMESTAMP NOT NULL, "
            "is_active INTEGER DEFAULT 1, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS service_bulk_prices "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, service_id INTEGER NOT NULL, "
            "min_quantity INTEGER NOT NULL, price_per_unit INTEGER NOT NULL, "
            "UNIQUE(service_id, min_quantity))"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS bonus_transactions "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
            "order_id INTEGER, amount INTEGER NOT NULL, reason TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS cart_items "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
            "service_id INTEGER NOT NULL, quantity INTEGER DEFAULT 1, "
            "price INTEGER NOT NULL, "
            "added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS support_tickets "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
            "username TEXT, full_name TEXT, message TEXT NOT NULL, "
            "status TEXT DEFAULT 'open', admin_reply TEXT, "
            "replied_by INTEGER, replied_at TIMESTAMP, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS payments "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, "
            "user_id INTEGER NOT NULL, method TEXT DEFAULT 'manual', "
            "status TEXT DEFAULT 'pending', amount INTEGER DEFAULT 0, "
            "receipt_file_id TEXT, charge_id TEXT, payload TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "paid_at TIMESTAMP)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS referral_invites "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, "
            "service_id INTEGER NOT NULL, owner_user_id INTEGER NOT NULL, "
            "invited_user_id INTEGER NOT NULL, referral_code TEXT NOT NULL, "
            "status TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await db.execute("CREATE INDEX IF NOT EXISTS idx_services_category ON services(category_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_reviews_service ON reviews(service_id)")
        await db.commit()
        migrations = [
            ("services", "category_id", "INTEGER"),
            ("services", "image_file_id", "TEXT"),
            ("services", "delivery_content", "TEXT"),
            ("services", "stock", "INTEGER DEFAULT 0"),
            ("users", "language", "TEXT DEFAULT 'uz'"),
            ("users", "referral_code", "TEXT"),
            ("users", "referred_by", "INTEGER"),
            ("users", "is_blocked", "INTEGER DEFAULT 0"),
            ("users", "bonus_balance", "INTEGER DEFAULT 0"),
            ("orders", "discount", "INTEGER DEFAULT 0"),
            ("orders", "final_price", "INTEGER"),
            ("orders", "coupon_code", "TEXT"),
            ("orders", "bonus_used", "INTEGER DEFAULT 0"),
            ("orders", "cashback_awarded", "INTEGER DEFAULT 0"),
            ("orders", "quantity", "INTEGER DEFAULT 1"),
            ("coupons", "service_id", "INTEGER"),
            ("services", "description_uz", "TEXT"),
            ("services", "description_ru", "TEXT"),
            ("services", "stars_price", "INTEGER DEFAULT 0"),
            ("services", "supports_stars", "INTEGER DEFAULT 0"),
            ("orders", "payment_method", "TEXT"),
            ("orders", "payment_status", "TEXT DEFAULT 'pending'"),
            ("orders", "invoice_payload", "TEXT"),
            ("orders", "telegram_payment_charge_id", "TEXT"),
            ("orders", "paid_at", "TIMESTAMP"),
            ("services", "form_instruction", "TEXT"),
            ("services", "auto_deliver", "INTEGER DEFAULT 0"),
            ("coupons", "max_per_user", "INTEGER DEFAULT 0"),
            ("services", "flash_discount", "INTEGER DEFAULT 0"),
            ("services", "flash_expire_at", "TIMESTAMP"),
            ("services", "is_deleted", "INTEGER DEFAULT 0"),
            ("services", "delivery_mode", "TEXT DEFAULT 'manual'"),
            ("services", "required_referrals", "INTEGER DEFAULT 0"),
            ("services", "requires_email", "INTEGER DEFAULT 0"),
            ("services", "referral_deadline_days", "INTEGER DEFAULT 0"),
            ("orders", "fulfillment_status", "TEXT DEFAULT 'pending'"),
            ("orders", "delivered_at", "TIMESTAMP"),
            ("orders", "customer_email", "TEXT"),
            ("orders", "required_referrals", "INTEGER DEFAULT 0"),
            ("orders", "current_referrals", "INTEGER DEFAULT 0"),
            ("orders", "referral_status", "TEXT DEFAULT 'not_required'"),
            ("orders", "referral_code", "TEXT"),
            ("orders", "referral_link", "TEXT"),
            ("orders", "referral_deadline_at", "TEXT"),
            ("orders", "activation_status", "TEXT DEFAULT 'pending'"),
            ("orders", "activation_ready_at", "TEXT"),
            ("orders", "activated_at", "TEXT"),
            ("services", "icon_emoji_id", "TEXT"),
            ("categories", "icon_emoji_id", "TEXT"),
        ]
        for table, col, col_type in migrations:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                await db.commit()
            except Exception:
                pass

        # --- NULL normalization for legacy DBs ---
        try:
            await db.execute(
                "UPDATE services SET stars_price = 0 WHERE stars_price IS NULL"
            )
            await db.execute(
                "UPDATE services SET supports_stars = 0 WHERE supports_stars IS NULL"
            )
            await db.execute(
                "UPDATE services SET stock = -1 WHERE stock IS NULL"
            )
            await db.execute(
                "UPDATE services SET price = 0 WHERE price IS NULL"
            )
            await db.execute(
                "UPDATE services SET active = 1 WHERE active IS NULL"
            )
            await db.execute(
                "UPDATE services SET supports_stars = 0 WHERE stars_price <= 0 AND supports_stars = 1"
            )
            await db.execute(
                "UPDATE services SET delivery_mode = 'manual' WHERE delivery_mode IS NULL OR delivery_mode = ''"
            )
            await db.execute(
                "UPDATE services SET required_referrals = 0 WHERE required_referrals IS NULL"
            )
            await db.execute(
                "UPDATE services SET requires_email = 0 WHERE requires_email IS NULL"
            )
            await db.execute(
                "UPDATE services SET referral_deadline_days = 0 WHERE referral_deadline_days IS NULL"
            )
            
            # --- Coupons ---
            await db.execute("UPDATE coupons SET used_count = 0 WHERE used_count IS NULL")
            await db.execute("UPDATE coupons SET is_active = 1 WHERE is_active IS NULL")
            
            # --- Users ---
            await db.execute("UPDATE users SET bonus_balance = 0 WHERE bonus_balance IS NULL")
            await db.execute("UPDATE users SET is_blocked = 0 WHERE is_blocked IS NULL")
            await db.execute("UPDATE users SET language = 'uz' WHERE language IS NULL")
            
            # --- Orders ---
            await db.execute("UPDATE orders SET discount = 0 WHERE discount IS NULL")
            await db.execute("UPDATE orders SET final_price = price WHERE final_price IS NULL")
            await db.execute("UPDATE orders SET quantity = 1 WHERE quantity IS NULL")
            await db.execute("UPDATE orders SET bonus_used = 0 WHERE bonus_used IS NULL")
            await db.execute("UPDATE orders SET cashback_awarded = 0 WHERE cashback_awarded IS NULL")
            await db.execute("UPDATE orders SET required_referrals = 0 WHERE required_referrals IS NULL")
            await db.execute("UPDATE orders SET current_referrals = 0 WHERE current_referrals IS NULL")
            await db.execute("UPDATE orders SET referral_status = 'not_required' WHERE referral_status IS NULL OR referral_status = ''")
            await db.execute("UPDATE orders SET activation_status = 'pending' WHERE activation_status IS NULL OR activation_status = ''")
            await db.execute("UPDATE orders SET payment_status = 'pending' WHERE payment_status IS NULL OR payment_status = ''")
            await db.execute("UPDATE orders SET status = 'payment_waiting' WHERE status IS NULL OR status = ''")

            await db.commit()
        except Exception:
            pass

        # --- coupon per-user tracking table ---
        try:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS coupon_user_uses "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, coupon_id INTEGER NOT NULL, "
                "user_id INTEGER NOT NULL, used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
            await db.commit()
        except Exception:
            pass

        # --- coupon_user_uses legacy UNIQUE(coupon_id,user_id) migration ---
        try:
            idx_rows = await (await db.execute("PRAGMA index_list(coupon_user_uses)")).fetchall()
            has_unique_coupon_user = any(row[2] for row in idx_rows)
            if has_unique_coupon_user:
                await db.execute(
                    "CREATE TABLE IF NOT EXISTS coupon_user_uses_new "
                    "(id INTEGER PRIMARY KEY AUTOINCREMENT, coupon_id INTEGER NOT NULL, "
                    "user_id INTEGER NOT NULL, used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                )
                await db.execute(
                    "INSERT INTO coupon_user_uses_new (coupon_id, user_id, used_at) "
                    "SELECT coupon_id, user_id, used_at FROM coupon_user_uses"
                )
                await db.execute("DROP TABLE coupon_user_uses")
                await db.execute("ALTER TABLE coupon_user_uses_new RENAME TO coupon_user_uses")
                await db.commit()
        except Exception:
            pass

        # --- referral campaigns table ---
        try:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS referral_campaigns "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "name TEXT NOT NULL, "
                "description TEXT, "
                "required_referrals INTEGER NOT NULL DEFAULT 5, "
                "reward_type TEXT NOT NULL DEFAULT 'bonus', "
                "reward_value INTEGER NOT NULL DEFAULT 0, "
                "is_active INTEGER DEFAULT 1, "
                "deadline TEXT, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
            await db.execute(
                "CREATE TABLE IF NOT EXISTS referral_campaign_participants "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "campaign_id INTEGER NOT NULL, "
                "user_id INTEGER NOT NULL, "
                "current_referrals INTEGER DEFAULT 0, "
                "reward_given INTEGER DEFAULT 0, "
                "joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE(campaign_id, user_id))"
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ref_campaign_user ON referral_campaign_participants(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ref_campaign_id ON referral_campaign_participants(campaign_id)")
            await db.commit()
        except Exception:
            pass

        # --- campaign participant migrations ---
        camp_part_migrations = [
            ("referral_campaign_participants", "customer_email", "TEXT"),
            ("referral_campaign_participants", "activation_status", "TEXT DEFAULT 'pending'"),
            ("referral_campaign_participants", "activated_at", "TIMESTAMP"),
        ]
        for table, col, col_type in camp_part_migrations:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                await db.commit()
            except Exception:
                pass

        # Normalize existing NULL activation_status
        try:
            await db.execute("UPDATE referral_campaign_participants SET activation_status = 'pending' WHERE activation_status IS NULL")
            await db.commit()
        except Exception:
            pass

        # --- campaign reward_description migration ---
        try:
            await db.execute("ALTER TABLE referral_campaigns ADD COLUMN reward_description TEXT")
            await db.commit()
        except Exception:
            pass

        # --- referral campaign invites table (anti-fraud) ---
        try:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS referral_campaign_invites "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "campaign_id INTEGER NOT NULL, "
                "inviter_id INTEGER NOT NULL, "
                "invited_id INTEGER NOT NULL, "
                "invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE(campaign_id, invited_id))"
            )
            await db.commit()
        except Exception:
            pass


        try:
            await db.execute("CREATE INDEX IF NOT EXISTS idx_referral_invites_order ON referral_invites(order_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_referral_invites_owner ON referral_invites(owner_user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_referral_invites_invited ON referral_invites(invited_user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_referral_code ON orders(referral_code)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_referral_status ON orders(referral_status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_activation_status ON orders(activation_status)")
            await db.commit()
        except Exception:
            pass


def normalize_service(row) -> dict:
    """Convert a sqlite3.Row / aiosqlite.Row / dict into a plain dict with safe defaults.

    Guarantees every field the bot reads is present and has a usable value,
    even when the underlying DB row comes from a legacy schema that predates
    Stars, descriptions, or stock columns.

    This is a **pure** function ? it never writes back to the DB.
    """
    if row is None:
        return None

    d = dict(row) if not isinstance(row, dict) else dict(row)  # shallow copy

    # --- text fields ---
    d["name"] = (d.get("name") or "").strip() or "Nomsiz xizmat"
    d["description"] = d.get("description") or ""
    d["description_uz"] = d.get("description_uz") or d["description"] or ""
    d["description_ru"] = d.get("description_ru") or d.get("description_uz") or d["description"] or ""

    # --- numeric fields ---
    d["price"] = int(d["price"]) if d.get("price") is not None else 0
    d["stock"] = int(d["stock"]) if d.get("stock") is not None else -1
    d["active"] = 1 if d.get("active") is None else int(d.get("active"))
    d["stars_price"] = int(d["stars_price"]) if d.get("stars_price") is not None else 0
    d["supports_stars"] = int(d["supports_stars"]) if d.get("supports_stars") is not None else 0
    d["required_referrals"] = int(d.get("required_referrals") or 0)
    d["requires_email"] = int(d.get("requires_email") or 0)
    d["referral_deadline_days"] = int(d.get("referral_deadline_days") or 0)

    # Self-heal: stars enabled but price missing ? disable
    if d["supports_stars"] and d["stars_price"] <= 0:
        d["supports_stars"] = 0

    # --- optional fields that handlers read with subscript access ---
    d.setdefault("image_file_id", None)
    d.setdefault("delivery_content", None)
    d.setdefault("form_instruction", None)
    d.setdefault("category_id", None)
    d.setdefault("promo_active", 0)
    d.setdefault("cashback_percent", 0.0)
    d.setdefault("promo_title", None)
    d["auto_deliver"] = int(d.get("auto_deliver") or 0)
    d["flash_discount"] = int(d.get("flash_discount") or 0)
    d.setdefault("flash_expire_at", None)
    d["delivery_mode"] = (d.get("delivery_mode") or "manual").strip() or "manual"

    return d


def normalize_category(row) -> dict:
    if row is None:
        return None
    d = dict(row) if not isinstance(row, dict) else dict(row)
    d["name"] = str(d.get("name") or "Nomsiz kategoriya").strip()
    return d


def normalize_user(row) -> dict:
    if row is None:
        return None
    d = dict(row) if not isinstance(row, dict) else dict(row)
    d["username"] = d.get("username") or ""
    d["full_name"] = str(d.get("full_name") or "Foydalanuvchi").strip()
    d["phone"] = d.get("phone") or ""
    lang = d.get("language") or "uz"
    d["language"] = lang if lang in ("uz", "ru") else "uz"
    d["bonus_balance"] = int(d.get("bonus_balance") or 0)
    d["is_blocked"] = int(d.get("is_blocked") or 0)
    d.setdefault("referral_code", None)
    d.setdefault("referred_by", None)
    return d


def normalize_coupon(row) -> dict:
    if row is None:
        return None
    d = dict(row) if not isinstance(row, dict) else dict(row)
    d["code"] = str(d.get("code") or "").strip().upper()
    d["discount_percent"] = int(d.get("discount_percent") or 0)
    d["max_uses"] = int(d.get("max_uses") or 0)
    d["used_count"] = int(d.get("used_count") or 0)
    d["is_active"] = 1 if d.get("is_active") is None else int(d.get("is_active"))
    d["max_per_user"] = int(d.get("max_per_user") or 0)
    d.setdefault("service_id", None)
    return d


def normalize_order(row) -> dict:
    if row is None:
        return None
    d = dict(row) if not isinstance(row, dict) else dict(row)
    d["service_name"] = str(d.get("service_name") or "Noma'lum xizmat").strip()
    d["price"] = int(d.get("price") or 0)
    d["status"] = d.get("status") or "pending"
    d["quantity"] = int(d.get("quantity") or 1)
    d["discount"] = int(d.get("discount") or 0)
    d["final_price"] = int(d.get("final_price") or (d["price"] * d["quantity"]))
    d["bonus_used"] = int(d.get("bonus_used") or 0)
    d["cashback_awarded"] = int(d.get("cashback_awarded") or 0)
    d["payment_status"] = d.get("payment_status") or "pending"
    d["payment_method"] = d.get("payment_method") or "manual"
    d["required_referrals"] = int(d.get("required_referrals") or 0)
    d["current_referrals"] = int(d.get("current_referrals") or 0)
    d.setdefault("note", None)
    d.setdefault("receipt_file_id", None)
    d.setdefault("coupon_code", None)
    d.setdefault("invoice_payload", None)
    d.setdefault("telegram_payment_charge_id", None)
    d.setdefault("paid_at", None)
    d.setdefault("customer_email", None)
    d["referral_status"] = d.get("referral_status") or "not_required"
    d.setdefault("referral_code", None)
    d.setdefault("referral_link", None)
    d.setdefault("referral_deadline_at", None)
    d["activation_status"] = d.get("activation_status") or "pending"
    d.setdefault("activation_ready_at", None)
    d.setdefault("activated_at", None)
    d["fulfillment_status"] = d.get("fulfillment_status") or "pending"
    return d


# PROMOS

async def add_promo(title: str, text: str, image_file_id: str = None, url: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO promos (title, text, image_file_id, url) VALUES (?, ?, ?, ?)",
            (title, text, image_file_id, url),
        )
        await db.commit()

async def get_promos():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM promos ORDER BY id DESC")
        return await cursor.fetchall()

async def delete_promo(promo_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM promos WHERE id=?", (promo_id,))
        await db.commit()


# SERVICES

async def add_service(name, description, price, category_id=None, image_file_id=None, delivery_content=None, stock=0, description_uz=None, description_ru=None, stars_price=0, supports_stars=0, delivery_mode="manual", required_referrals=0, requires_email=0, referral_deadline_days=0, icon_emoji_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO services (name, description, description_uz, description_ru, price, category_id, image_file_id, delivery_content, stock, stars_price, supports_stars, delivery_mode, required_referrals, requires_email, referral_deadline_days, icon_emoji_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                name, description, description_uz or description, description_ru or description,
                price, category_id, image_file_id, delivery_content, stock, stars_price, supports_stars,
                delivery_mode, required_referrals, requires_email, referral_deadline_days, icon_emoji_id,
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def set_flash_sale(service_id: int, discount: int, expire_at: str):
    """Set flash sale for a service. expire_at format: 'YYYY-MM-DD HH:MM:SS' or None"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE services SET flash_discount=?, flash_expire_at=? WHERE id=?",
            (discount, expire_at, service_id)
        )
        await db.commit()


async def update_stock(service_id: int, new_stock: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE services SET stock=? WHERE id=?", (new_stock, service_id))
        await db.commit()


async def decrease_stock(service_id: int, amount: int = 1):
    """Decrease finite stock. stock=-1 means unlimited and must stay untouched."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE services
            SET stock = CASE
                WHEN stock = -1 THEN -1
                ELSE MAX(0, COALESCE(stock, 0) - ?)
            END
            WHERE id=?
            """,
            (amount, service_id),
        )
        await db.commit()


async def increase_stock(service_id: int, amount: int = 1):
    """Return finite stock. stock=-1 means unlimited and must stay untouched."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE services
            SET stock = CASE
                WHEN stock = -1 THEN -1
                ELSE COALESCE(stock, 0) + ?
            END
            WHERE id=?
            """,
            (amount, service_id),
        )
        await db.commit()


async def set_service_delivery(service_id, delivery_content):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE services SET delivery_content=? WHERE id=?",
            (delivery_content, service_id),
        )
        await db.commit()


async def set_service_form_instruction(service_id, form_instruction):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE services SET form_instruction=? WHERE id=?",
            (form_instruction, service_id),
        )
        await db.commit()


async def get_services(only_active=True, category_id=None, query=None, limit=None, offset=0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conditions = []
        params = []
        conditions.append("(s.is_deleted IS NULL OR s.is_deleted=0)")
        if only_active:
            conditions.append("s.active=1")
        if category_id is not None:
            conditions.append("s.category_id=?")
            params.append(category_id)
        if query:
            conditions.append("LOWER(s.name) LIKE LOWER(?)")
            params.append(f"%{query}%")
            
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        
        # Left join with service_promotions to get active cashback
        sql = f"""
            SELECT s.*, 
                   p.cashback_percent, p.title as promo_title, p.is_active as promo_active 
            FROM services s 
            LEFT JOIN service_promotions p ON s.id = p.service_id AND p.is_active = 1
            {where} 
            ORDER BY s.id DESC
        """
        
        if limit is not None:
            sql += f" LIMIT {limit} OFFSET {offset}"
            
        cursor = await db.execute(sql, params)
        return await cursor.fetchall()


async def get_services_count(only_active=True, category_id=None, query=None):
    async with aiosqlite.connect(DB_PATH) as db:
        conditions = ["(is_deleted IS NULL OR is_deleted=0)"]
        params = []
        if only_active:
            conditions.append("active=1")
        if category_id is not None:
            conditions.append("category_id=?")
            params.append(category_id)
        if query:
            conditions.append("LOWER(name) LIKE LOWER(?)")
            params.append(f"%{query}%")
            
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        cursor = await db.execute(f"SELECT COUNT(*) FROM services {where}", params)
        row = await cursor.fetchone()
        return row[0]


async def get_service(service_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = """
            SELECT s.*, 
                   p.cashback_percent, p.title as promo_title, p.is_active as promo_active 
            FROM services s 
            LEFT JOIN service_promotions p ON s.id = p.service_id AND p.is_active = 1
            WHERE s.id=?
        """
        cursor = await db.execute(sql, (service_id,))
        return await cursor.fetchone()


async def get_public_service(service_id):
    """User/Mini-App safe service lookup: active and not soft-deleted only."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = """
            SELECT s.*,
                   p.cashback_percent, p.title as promo_title, p.is_active as promo_active
            FROM services s
            LEFT JOIN service_promotions p ON s.id = p.service_id AND p.is_active = 1
            WHERE s.id=? AND s.active=1 AND (s.is_deleted IS NULL OR s.is_deleted=0)
        """
        cursor = await db.execute(sql, (service_id,))
        return await cursor.fetchone()


async def update_service(service_id, name, description, price, description_ru=None, stars_price=0, supports_stars=0, delivery_mode="manual", required_referrals=0, requires_email=0, referral_deadline_days=0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE services SET name=?, description=?, description_uz=?, description_ru=?, price=?, stars_price=?, supports_stars=?, delivery_mode=?, required_referrals=?, requires_email=?, referral_deadline_days=? WHERE id=?",
            (
                name, description, description, description_ru or description, price,
                stars_price, supports_stars, delivery_mode, required_referrals,
                requires_email, referral_deadline_days, service_id,
            ),
        )
        await db.commit()


async def update_service_category(service_id, category_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE services SET category_id=? WHERE id=?",
            (category_id, service_id),
        )
        await db.commit()


async def toggle_service(service_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE services SET active = CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?",
            (service_id,),
        )
        await db.commit()


async def delete_service(service_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE services SET active=0, is_deleted=1 WHERE id=?", (service_id,))
        await db.commit()


# SERVICE PROMOTIONS (CASHBACK)

async def get_service_promo_admin(service_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM service_promotions WHERE service_id=?", (service_id,))
        return await cursor.fetchone()

async def get_service_promo_admin_by_id(promo_id: int):
    """Fetch a service_promotion row by its own primary key (promo id)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM service_promotions WHERE id=?", (promo_id,))
        return await cursor.fetchone()

async def create_or_update_service_promo(service_id: int, title: str, percent: float, starts_at=None, ends_at=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM service_promotions WHERE service_id=?", (service_id,))
        exists = await cursor.fetchone()
        if exists:
            await db.execute(
                "UPDATE service_promotions SET title=?, cashback_percent=?, starts_at=?, ends_at=? WHERE service_id=?",
                (title, percent, starts_at, ends_at, service_id)
            )
        else:
            await db.execute(
                "INSERT INTO service_promotions (service_id, title, cashback_percent, starts_at, ends_at) VALUES (?, ?, ?, ?, ?)",
                (service_id, title, percent, starts_at, ends_at)
            )
        await db.commit()

async def toggle_service_promo(promo_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE service_promotions SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?", (promo_id,))
        await db.commit()

async def delete_service_promo(promo_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM service_promotions WHERE id=?", (promo_id,))
        await db.commit()

async def list_all_service_promotions():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT p.*, s.name as service_name "
            "FROM service_promotions p "
            "JOIN services s ON p.service_id = s.id "
            "ORDER BY p.id DESC"
        )
        return await cursor.fetchall()


async def add_bonus_transaction(user_id: int, order_id: int, amount: int, reason: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO bonus_transactions (user_id, order_id, amount, reason) VALUES (?, ?, ?, ?)",
            (user_id, order_id, amount, reason)
        )
        await db.execute(
            "UPDATE users SET bonus_balance = bonus_balance + ? WHERE id=?",
            (amount, user_id)
        )
        await db.commit()

async def mark_order_cashback_awarded(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET cashback_awarded=1 WHERE id=?", (order_id,))
        await db.commit()

async def get_user_total_cashback(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT SUM(amount) FROM bonus_transactions WHERE user_id=? AND reason LIKE 'Cashback%'", (user_id,))
        res = await cursor.fetchone()
        return res[0] or 0


# CATEGORIES

async def add_category(name):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        await db.commit()
        return cursor.lastrowid


async def get_categories():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM categories ORDER BY id")
        rows = await cursor.fetchall()
        return [normalize_category(r) for r in rows]


async def get_category_min_prices():
    """Return dict {category_id: min_price} for active services."""
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT category_id, MIN(price) as min_price FROM services "
            "WHERE active=1 AND (is_deleted IS NULL OR is_deleted=0) "
            "GROUP BY category_id"
        )
        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}


async def get_category(cat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM categories WHERE id=?", (cat_id,))
        row = await cursor.fetchone()
        return normalize_category(row)


async def update_category(cat_id, name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE categories SET name=? WHERE id=?", (name, cat_id))
        await db.commit()


async def delete_category(cat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        await db.commit()


# USERS

async def save_user(user_id, username, full_name, referred_by=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        existing = await (await db.execute("SELECT * FROM users WHERE id=?", (user_id,))).fetchone()
        if existing:
            if not existing["referral_code"]:
                ref_code = secrets.token_hex(4)
                await db.execute(
                    "UPDATE users SET username=?, full_name=?, referral_code=? WHERE id=?",
                    (username, full_name, ref_code, user_id),
                )
            else:
                await db.execute(
                    "UPDATE users SET username=?, full_name=? WHERE id=?",
                    (username, full_name, user_id),
                )
        else:
            ref_code = secrets.token_hex(4)
            await db.execute(
                "INSERT INTO users (id, username, full_name, referral_code, referred_by) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, full_name, ref_code, referred_by),
            )
        await db.commit()


async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        row = await cursor.fetchone()
        return normalize_user(row)


# NEW FEATURE: Top services ranking
async def get_top_services(limit: int = 3):
    """
    Return the most ordered services along with their order count.

    Args:
        limit (int): Maximum number of services to return. Defaults to 3.

    Returns:
        List[aiosqlite.Row]: Each row contains service id, name and order_count.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Count the number of orders per service. We use LEFT JOIN so that services with
        # zero orders still appear in the ranking; however, they will sort after those
        # with orders due to descending order_count.
        cursor = await db.execute(
            """
            SELECT s.id, s.name, COUNT(o.id) AS order_count
            FROM services s
            LEFT JOIN orders o ON o.service_id = s.id
            GROUP BY s.id
            ORDER BY order_count DESC
            LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()


async def set_user_language(user_id, lang):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language=? WHERE id=?", (lang, user_id))
        await db.commit()


async def block_user(user_id, blocked):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_blocked=? WHERE id=?", (blocked, user_id))
        await db.commit()


async def get_all_user_ids(only_active=True):
    async with aiosqlite.connect(DB_PATH) as db:
        if only_active:
            cursor = await db.execute("SELECT id FROM users WHERE is_blocked != 1")
        else:
            cursor = await db.execute("SELECT id FROM users")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_user_by_referral(ref_code):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE referral_code=?", (ref_code,))
        row = await cursor.fetchone()
        return normalize_user(row)


async def get_referral_count(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,))
        row = await cursor.fetchone()
        return row[0]


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [normalize_user(r) for r in rows]


async def get_user_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0]


# ORDERS

async def create_order(user_id, service_id, service_name, price, note="",
                       discount=0, final_price=None, coupon_code=None, bonus_used=0, quantity=1,
                       customer_email=None, required_referrals=0, current_referrals=0,
                       referral_status="not_required", referral_code=None, referral_link=None,
                       referral_deadline_at=None, activation_status="pending",
                       activation_ready_at=None, activated_at=None, status="payment_waiting"):
    if final_price is None:
        final_price = price * quantity - (price * quantity * discount // 100)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO orders (user_id, service_id, service_name, price, note, discount, final_price, coupon_code, bonus_used, quantity, customer_email, required_referrals, current_referrals, referral_status, referral_code, referral_link, referral_deadline_at, activation_status, activation_ready_at, activated_at, status)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id, service_id, service_name, price, note, discount, final_price, coupon_code,
                bonus_used, quantity, customer_email, required_referrals, current_referrals,
                referral_status, referral_code, referral_link, referral_deadline_at,
                activation_status, activation_ready_at, activated_at, status,
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_order_by_referral(order_id, referral_code):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders WHERE id=? AND referral_code=?",
            (order_id, referral_code),
        )
        row = await cursor.fetchone()
        return normalize_order(row)


async def set_order_referral_email(order_id: int, email: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET customer_email=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (email, order_id),
        )
        await db.commit()


async def set_order_referral_link(order_id: int, referral_link: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET referral_link=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (referral_link, order_id),
        )
        await db.commit()


async def update_order_referral_progress(order_id: int, current_referrals: int, referral_status: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if referral_status is None:
            await db.execute(
                "UPDATE orders SET current_referrals=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (current_referrals, order_id),
            )
        else:
            await db.execute(
                "UPDATE orders SET current_referrals=?, referral_status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (current_referrals, referral_status, order_id),
            )
        await db.commit()


async def mark_referral_ready(order_id: int, referral_status: str = "target_met"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET referral_status=?, activation_status='ready', activation_ready_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (referral_status, order_id),
        )
        await db.commit()


async def mark_referral_activated(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET activation_status='activated', activated_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (order_id,),
        )
        await db.commit()


async def cancel_referral_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET referral_status='cancelled', activation_status='failed', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (order_id,),
        )
        await db.commit()


async def set_referral_deadline(order_id: int, deadline_at: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET referral_deadline_at=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (deadline_at, order_id),
        )
        await db.commit()


async def expire_referral_order_if_needed(order_id: int):
    order = await get_order(order_id)
    if not order:
        return None
    if order["referral_status"] in ("target_met", "expired", "cancelled"):
        return order
    deadline_at = order.get("referral_deadline_at")
    if not deadline_at:
        return order
    try:
        deadline_dt = datetime.strptime(str(deadline_at)[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return order
    if datetime.now() <= deadline_dt:
        return order
    if order["current_referrals"] >= order["required_referrals"]:
        return order
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET referral_status='expired', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (order_id,),
        )
        await db.commit()
    return await get_order(order_id)


async def create_referral_invite(order_id: int, service_id: int, owner_user_id: int, invited_user_id: int, referral_code: str, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO referral_invites (order_id, service_id, owner_user_id, invited_user_id, referral_code, status) VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, service_id, owner_user_id, invited_user_id, referral_code, status),
        )
        await db.commit()
        return cursor.lastrowid


async def get_referral_invite_for_order_user(order_id: int, invited_user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM referral_invites WHERE order_id=? AND invited_user_id=? ORDER BY id DESC LIMIT 1",
            (order_id, invited_user_id),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_referral_invites(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM referral_invites WHERE order_id=? ORDER BY created_at DESC, id DESC",
            (order_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_all_campaign_participants(campaign_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT p.*, u.username, u.full_name "
            "FROM referral_campaign_participants p "
            "LEFT JOIN users u ON p.user_id = u.id "
            "WHERE p.campaign_id = ? "
            "ORDER BY p.reward_given DESC, p.current_referrals DESC",
            (campaign_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def record_campaign_invite(campaign_id: int, inviter_id: int, invited_id: int) -> bool:
    """
    Records an invite and returns True if successful (meaning it's a new invite for this campaign).
    Returns False if the invited_id has already been invited to this campaign.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO referral_campaign_invites (campaign_id, inviter_id, invited_id) VALUES (?, ?, ?)",
                (campaign_id, inviter_id, invited_id)
            )
            await db.commit()
            return True
    except Exception:
        # IntegrityError typically means they were already invited
        return False


async def get_user_completed_campaign_ids(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT campaign_id FROM referral_campaign_participants WHERE user_id = ? AND reward_given = 1",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def get_referral_orders(referral_status=None, activation_status=None, limit=100):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conditions = ["s.delivery_mode='referral_activation'"]
        params = []
        if referral_status:
            conditions.append("o.referral_status=?")
            params.append(referral_status)
        if activation_status:
            conditions.append("o.activation_status=?")
            params.append(activation_status)
        where = " AND ".join(conditions)
        cursor = await db.execute(
            f"""
            SELECT o.*, u.username, u.full_name, s.delivery_mode
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN services s ON o.service_id = s.id
            WHERE {where}
            ORDER BY o.created_at DESC, o.id DESC
            LIMIT ?
            """,
            (*params, limit),
        )
        rows = await cursor.fetchall()
        return [normalize_order(r) for r in rows]


def build_referral_deadline(days: int):
    if not days or int(days) <= 0:
        return None
    return (datetime.now() + timedelta(days=int(days))).strftime("%Y-%m-%d %H:%M:%S")


async def set_order_receipt(order_id, file_id):
    """Attach manual receipt and move the order into admin verification queue."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE orders
            SET receipt_file_id=?,
                payment_method='manual',
                payment_status='submitted',
                status='paid_waiting_admin',
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (file_id, order_id),
        )
        await db.commit()


async def update_order_status(order_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, order_id))
        await db.commit()


async def update_fulfillment_status(order_id, fulfillment_status):
    async with aiosqlite.connect(DB_PATH) as db:
        extra = ", delivered_at=CURRENT_TIMESTAMP" if fulfillment_status == "delivered" else ""
        status_extra = ""
        if fulfillment_status == "processing":
            status_extra = ", status='processing'"
        elif fulfillment_status == "delivered":
            status_extra = ", status='delivered'"
        await db.execute(
            f"UPDATE orders SET fulfillment_status=?, updated_at=CURRENT_TIMESTAMP{extra}{status_extra} WHERE id=?",
            (fulfillment_status, order_id)
        )
        await db.commit()


async def confirm_order_for_processing(order_id: int):
    """Admin confirmation: mark payment accepted and move order to delivery processing."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE orders
            SET status='processing',
                payment_status='paid',
                fulfillment_status='processing',
                paid_at=COALESCE(paid_at, CURRENT_TIMESTAMP),
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (order_id,),
        )
        await db.commit()


async def set_order_stars_invoice(order_id: int, payload: str):
    """Remember Stars invoice payload before payment is completed."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE orders
            SET payment_method='stars',
                invoice_payload=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND COALESCE(payment_status, 'pending') != 'paid'
            """,
            (payload, order_id),
        )
        await db.commit()


async def mark_order_paid_with_stars(order_id: int, charge_id: str, payload: str):
    """Idempotently marks an order as paid via Telegram Stars and logs details."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Check idempotency
        cursor = await db.execute("SELECT payment_status FROM orders WHERE id=?", (order_id,))
        order = await cursor.fetchone()
        if order and order["payment_status"] == "paid":
            return False # already paid
        
        await db.execute(
            """UPDATE orders 
               SET payment_method='stars', payment_status='paid', status='paid_waiting_admin', telegram_payment_charge_id=?,
                   invoice_payload=?, paid_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (charge_id, payload, order_id)
        )
        await db.commit()
        return True


async def get_order(order_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        row = await cursor.fetchone()
        return normalize_order(row)


async def get_user_orders(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [normalize_order(r) for r in rows]


async def get_user_total_spent(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COALESCE(SUM(final_price), 0) FROM orders WHERE user_id=? AND status IN ('confirmed','processing','delivered')",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row[0] or 0


async def get_confirmed_customers(limit=50, offset=0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                u.id,
                u.username,
                u.full_name,
                u.bonus_balance,
                COUNT(o.id) AS confirmed_orders_count,
                SUM(COALESCE(o.final_price, o.price)) AS total_spent,
                MAX(o.created_at) AS last_confirmed_at,
                (
                    SELECT o2.id
                    FROM orders o2
                    WHERE o2.user_id = u.id AND o2.status IN ('confirmed','processing','delivered')
                    ORDER BY o2.created_at DESC, o2.id DESC
                    LIMIT 1
                ) AS last_order_id,
                (
                    SELECT s.name
                    FROM orders o3
                    LEFT JOIN services s ON s.id = o3.service_id
                    WHERE o3.user_id = u.id AND o3.status IN ('confirmed','processing','delivered')
                    ORDER BY o3.created_at DESC, o3.id DESC
                    LIMIT 1
                ) AS last_service_name
            FROM users u
            JOIN orders o
              ON o.user_id = u.id
             AND o.status IN ('confirmed','processing','delivered')
            GROUP BY u.id, u.username, u.full_name, u.bonus_balance
            ORDER BY MAX(o.created_at) DESC, MAX(o.id) DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [normalize_user(r) for r in rows]


async def get_confirmed_customers_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT o.user_id
                FROM orders o
                WHERE o.status IN ('confirmed','processing','delivered')
                GROUP BY o.user_id
            ) t
            """
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_confirmed_customer_detail(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                u.id,
                u.username,
                u.full_name,
                u.bonus_balance,
                COUNT(o.id) AS confirmed_orders_count,
                SUM(COALESCE(o.final_price, o.price)) AS total_spent,
                MAX(o.created_at) AS last_confirmed_at,
                (
                    SELECT o2.id
                    FROM orders o2
                    WHERE o2.user_id = u.id AND o2.status IN ('confirmed','processing','delivered')
                    ORDER BY o2.created_at DESC, o2.id DESC
                    LIMIT 1
                ) AS last_order_id,
                (
                    SELECT s.name
                    FROM orders o3
                    LEFT JOIN services s ON s.id = o3.service_id
                    WHERE o3.user_id = u.id AND o3.status IN ('confirmed','processing','delivered')
                    ORDER BY o3.created_at DESC, o3.id DESC
                    LIMIT 1
                ) AS last_service_name
            FROM users u
            JOIN orders o
              ON o.user_id = u.id
             AND o.status IN ('confirmed','processing','delivered')
            WHERE u.id = ?
            GROUP BY u.id, u.username, u.full_name, u.bonus_balance
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        return normalize_user(row)


async def get_pending_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT o.*, u.username, u.full_name FROM orders o "
            "LEFT JOIN users u ON o.user_id = u.id "
            "WHERE o.status IN ('pending', 'payment_waiting', 'paid_waiting_admin') ORDER BY o.created_at DESC"
        )
        rows = await cursor.fetchall()
        return [normalize_order(r) for r in rows]


async def get_all_orders(limit=50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT o.*, u.username, u.full_name FROM orders o "
            "LEFT JOIN users u ON o.user_id = u.id "
            "ORDER BY o.created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [normalize_order(r) for r in rows]


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        total_orders = (await (await db.execute("SELECT COUNT(*) FROM orders")).fetchone())[0]
        pending = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE status IN ('pending','payment_waiting','paid_waiting_admin')")).fetchone())[0]
        confirmed = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE status IN ('confirmed','processing','delivered')")).fetchone())[0]
        rejected = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE status='rejected'")).fetchone())[0]
        revenue_row = await (await db.execute("SELECT SUM(final_price) FROM orders WHERE status IN ('confirmed','processing','delivered')")).fetchone()
        revenue = revenue_row[0] or 0
        
        today_rev = await (await db.execute("SELECT SUM(final_price) FROM orders WHERE status IN ('confirmed','processing','delivered') AND date(created_at) = date('now', 'localtime')")).fetchone()
        today_revenue = today_rev[0] or 0
        
        conversion = round((confirmed / total_orders) * 100, 1) if total_orders > 0 else 0

        return {
            "users": users, "total_orders": total_orders, "pending": pending,
            "confirmed": confirmed, "rejected": rejected, "revenue": revenue,
            "today_revenue": today_revenue, "conversion": conversion,
        }


async def get_analytics():
    """Advanced analytics: weekly/monthly revenue, top services, top customers."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row

        # Weekly revenue (last 7 days)
        row = await (await conn.execute(
            "SELECT COALESCE(SUM(final_price), 0) as rev, COUNT(*) as cnt "
            "FROM orders WHERE status IN ('confirmed','processing','delivered') AND created_at >= datetime('now', '-7 days', 'localtime')"
        )).fetchone()
        week_revenue = row["rev"] or 0
        week_orders = row["cnt"] or 0

        # Monthly revenue (last 30 days)
        row = await (await conn.execute(
            "SELECT COALESCE(SUM(final_price), 0) as rev, COUNT(*) as cnt "
            "FROM orders WHERE status IN ('confirmed','processing','delivered') AND created_at >= datetime('now', '-30 days', 'localtime')"
        )).fetchone()
        month_revenue = row["rev"] or 0
        month_orders = row["cnt"] or 0

        # Top 5 services by confirmed sales
        top_services = await (await conn.execute(
            "SELECT service_name, COUNT(*) as cnt, SUM(final_price) as rev "
            "FROM orders WHERE status IN ('confirmed','processing','delivered') "
            "GROUP BY service_id ORDER BY cnt DESC LIMIT 5"
        )).fetchall()

        # Top 5 customers by total spent
        top_customers = await (await conn.execute(
            "SELECT o.user_id, u.username, u.full_name, COUNT(*) as cnt, SUM(o.final_price) as spent "
            "FROM orders o LEFT JOIN users u ON o.user_id = u.id "
            "WHERE o.status IN ('confirmed','processing','delivered') "
            "GROUP BY o.user_id ORDER BY spent DESC LIMIT 5"
        )).fetchall()

        # Daily revenue for last 7 days
        daily_rows = await (await conn.execute(
            "SELECT date(created_at) as d, COALESCE(SUM(final_price), 0) as rev, COUNT(*) as cnt "
            "FROM orders WHERE status IN ('confirmed','processing','delivered') AND created_at >= datetime('now', '-7 days', 'localtime') "
            "GROUP BY date(created_at) ORDER BY d DESC"
        )).fetchall()

        # Average order value
        avg_row = await (await conn.execute(
            "SELECT AVG(final_price) as avg_val FROM orders WHERE status IN ('confirmed','processing','delivered') AND final_price > 0"
        )).fetchone()
        avg_order = int(avg_row["avg_val"] or 0)

        # Expired orders count (last 30 days)
        expired_row = await (await conn.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE status='expired' AND created_at >= datetime('now', '-30 days', 'localtime')"
        )).fetchone()
        expired_count = expired_row["cnt"] or 0

        return {
            "week_revenue": week_revenue, "week_orders": week_orders,
            "month_revenue": month_revenue, "month_orders": month_orders,
            "top_services": [dict(r) for r in top_services],
            "top_customers": [dict(r) for r in top_customers],
            "daily": [dict(r) for r in daily_rows],
            "avg_order": avg_order, "expired_count": expired_count,
        }


async def get_crm_segments():
    """Segment users into CRM categories based on order history."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row

        # Get all users with their order stats
        rows = await (await conn.execute("""
            SELECT u.id, u.username, u.full_name, u.created_at as user_created,
                   COUNT(o.id) as order_count,
                   COALESCE(SUM(CASE WHEN o.status IN ('confirmed','processing','delivered') THEN o.final_price ELSE 0 END), 0) as total_spent,
                   MAX(o.created_at) as last_order_at,
                   SUM(CASE WHEN o.status IN ('confirmed','processing','delivered') THEN 1 ELSE 0 END) as confirmed_count
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            GROUP BY u.id
        """)).fetchall()

        segments = {
            "vip": {"users": [], "count": 0, "total_spent": 0},
            "active": {"users": [], "count": 0, "total_spent": 0},
            "new": {"users": [], "count": 0, "total_spent": 0},
            "returning": {"users": [], "count": 0, "total_spent": 0},
            "churned": {"users": [], "count": 0, "total_spent": 0},
            "one_time": {"users": [], "count": 0, "total_spent": 0},
        }

        from datetime import datetime, timedelta
        now = datetime.now()

        for r in rows:
            r = dict(r)
            confirmed = r["confirmed_count"] or 0
            spent = r["total_spent"] or 0
            orders = r["order_count"] or 0
            last_order = None
            if r["last_order_at"]:
                try:
                    last_order = datetime.strptime(str(r["last_order_at"])[:19], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

            days_since_last = (now - last_order).days if last_order else 9999
            user_info = {"id": r["id"], "username": r["username"], "full_name": r["full_name"],
                         "confirmed": confirmed, "spent": spent, "days_since": days_since_last}

            if confirmed >= 5 or spent >= 500000:
                seg = "vip"
            elif orders == 0:
                seg = "new"
            elif days_since_last <= 30:
                seg = "active"
            elif confirmed == 1 and days_since_last > 30:
                seg = "one_time"
            elif days_since_last > 90:
                seg = "churned"
            else:
                seg = "returning"

            segments[seg]["users"].append(user_info)
            segments[seg]["count"] += 1
            segments[seg]["total_spent"] += spent

        return segments


# ??? SUPPORT TICKETS ???

async def create_ticket(user_id, username, full_name, message_text):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO support_tickets (user_id, username, full_name, message) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, message_text)
        )
        await db.commit()
        return cursor.lastrowid


async def reply_ticket(ticket_id, admin_id, reply_text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE support_tickets SET status='answered', admin_reply=?, replied_by=?, replied_at=CURRENT_TIMESTAMP WHERE id=?",
            (reply_text, admin_id, ticket_id)
        )
        await db.commit()


async def close_ticket(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE support_tickets SET status='closed' WHERE id=?", (ticket_id,))
        await db.commit()


async def get_open_tickets():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM support_tickets WHERE status='open' ORDER BY created_at DESC"
        )
        return await cursor.fetchall()


async def get_ticket(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM support_tickets WHERE id=?", (ticket_id,))
        return await cursor.fetchone()


async def get_ticket_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        open_cnt = (await (await db.execute("SELECT COUNT(*) FROM support_tickets WHERE status='open'")).fetchone())[0]
        answered_cnt = (await (await db.execute("SELECT COUNT(*) FROM support_tickets WHERE status='answered'")).fetchone())[0]
        total = (await (await db.execute("SELECT COUNT(*) FROM support_tickets")).fetchone())[0]
        avg_row = await (await db.execute(
            "SELECT AVG((julianday(replied_at) - julianday(created_at)) * 24 * 60) "
            "FROM support_tickets WHERE replied_at IS NOT NULL"
        )).fetchone()
        avg_response_min = int(avg_row[0] or 0)
        return {"open": open_cnt, "answered": answered_cnt, "total": total, "avg_response_min": avg_response_min}


# ??? PAYMENTS ???

async def create_payment(order_id, user_id, method="manual", amount=0, receipt_file_id=None, charge_id=None, payload=None, status="pending", paid_at=None):
    if paid_at == "CURRENT_TIMESTAMP":
        paid_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO payments (order_id, user_id, method, status, amount, receipt_file_id, charge_id, payload, paid_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (order_id, user_id, method, status, amount, receipt_file_id, charge_id, payload, paid_at)
        )
        await db.commit()
        return cursor.lastrowid


async def update_payment_status(payment_id, status, paid_at=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if paid_at:
            await db.execute("UPDATE payments SET status=?, paid_at=? WHERE id=?", (status, paid_at, payment_id))
        else:
            await db.execute("UPDATE payments SET status=? WHERE id=?", (status, payment_id))
        await db.commit()


async def get_payments_by_order(order_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM payments WHERE order_id=? ORDER BY created_at DESC", (order_id,))
        return await cursor.fetchall()

# REVIEWS

async def add_review(order_id, user_id, service_id, rating, comment=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reviews (order_id, user_id, service_id, rating, comment) VALUES (?, ?, ?, ?, ?)",
            (order_id, user_id, service_id, rating, comment),
        )
        await db.commit()


async def get_order_review(order_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM reviews WHERE order_id=?", (order_id,))
        return await cursor.fetchone()


async def get_service_reviews(service_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT r.*, u.full_name, u.username FROM reviews r "
            "LEFT JOIN users u ON r.user_id = u.id "
            "WHERE r.service_id=? ORDER BY r.created_at DESC LIMIT 20",
            (service_id,),
        )
        return await cursor.fetchall()


async def get_service_avg_rating(service_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT AVG(rating), COUNT(*) FROM reviews WHERE service_id=?",
            (service_id,),
        )
        row = await cursor.fetchone()
        return round(row[0] or 0, 1), row[1] or 0


async def get_recent_reviews(limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT r.*, u.full_name, u.username, s.name as service_name FROM reviews r "
            "LEFT JOIN users u ON r.user_id = u.id "
            "LEFT JOIN services s ON r.service_id = s.id "
            "ORDER BY r.created_at DESC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


async def review_exists(order_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM reviews WHERE order_id=?", (order_id,))
        return await cursor.fetchone() is not None


# COUPONS

async def add_coupon(code, discount_percent, max_uses, service_id=None, max_per_user=0):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO coupons (code, discount_percent, max_uses, service_id, max_per_user) VALUES (?, ?, ?, ?, ?)",
            (code.upper(), discount_percent, max_uses, service_id, max_per_user),
        )
        await db.commit()
        return cursor.lastrowid


async def get_coupon(code, service_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT *
            FROM coupons
            WHERE code=?
              AND is_active=1
              AND used_count < max_uses
              AND (service_id IS NULL OR service_id=?)
            """,
            (code.upper(), service_id),
        )
        row = await cursor.fetchone()
        return normalize_coupon(row)


async def get_available_coupons_for_service(service_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT *
            FROM coupons
            WHERE is_active=1
              AND used_count < max_uses
              AND (service_id IS NULL OR service_id=?)
            ORDER BY
              CASE WHEN service_id IS NULL THEN 1 ELSE 0 END,
              discount_percent DESC,
              id DESC
            """,
            (service_id,),
        )
        rows = await cursor.fetchall()
        return [normalize_coupon(r) for r in rows]


async def use_coupon(code):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE coupons SET used_count = used_count + 1 WHERE code=?",
            (code.upper(),),
        )
        await db.commit()


async def check_coupon_user_limit(coupon_id: int, user_id: int, max_per_user: int) -> bool:
    """Return True if user can use this coupon (hasn't exceeded limit). 0 = unlimited."""
    if max_per_user <= 0:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM coupon_user_uses WHERE coupon_id=? AND user_id=?",
            (coupon_id, user_id),
        )
        row = await cursor.fetchone()
        return (row[0] or 0) < max_per_user


async def record_coupon_use(coupon_id: int, user_id: int):
    """Record one coupon use. Multiple rows are allowed for max_per_user > 1."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO coupon_user_uses (coupon_id, user_id) VALUES (?, ?)",
            (coupon_id, user_id),
        )
        await db.commit()


async def set_auto_deliver(service_id: int, value: int):
    """Toggle auto-delivery for a service (1 = auto, 0 = manual)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE services SET auto_deliver=? WHERE id=?", (value, service_id))
        await db.commit()


async def get_all_coupons():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT c.*, s.name AS service_name
            FROM coupons c
            LEFT JOIN services s ON s.id = c.service_id
            ORDER BY c.id DESC
            """
        )
        rows = await cursor.fetchall()
        return [normalize_coupon(r) for r in rows]


async def delete_coupon(coupon_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM coupons WHERE id=?", (coupon_id,))
        await db.commit()


# BONUS

async def add_bonus(user_id, amount, description=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET bonus_balance = bonus_balance + ? WHERE id=?",
            (amount, user_id),
        )
        await db.execute(
            "INSERT INTO bonus_log (user_id, amount, type, description) VALUES (?, ?, 'credit', ?)",
            (user_id, amount, description),
        )
        await db.commit()


async def use_bonus(user_id, amount, description=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET bonus_balance = MAX(0, bonus_balance - ?) WHERE id=?",
            (amount, user_id),
        )
        await db.execute(
            "INSERT INTO bonus_log (user_id, amount, type, description) VALUES (?, ?, 'debit', ?)",
            (user_id, amount, description),
        )
        await db.commit()


async def get_bonus_log(user_id, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bonus_log WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return await cursor.fetchall()


async def get_user_confirmed_orders_count(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id=? AND status IN ('confirmed','processing','delivered')",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row[0]
async def get_active_service_promotions():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = """
            SELECT p.*, s.name as service_name, s.price 
            FROM service_promotions p 
            JOIN services s ON p.service_id = s.id 
            WHERE p.is_active = 1
            ORDER BY p.id DESC
        """
        cursor = await db.execute(sql)
        return await cursor.fetchall()


# BULK PRICING

async def get_bulk_prices(service_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM service_bulk_prices WHERE service_id=? ORDER BY min_quantity ASC", (service_id,))
        return await cursor.fetchall()

async def get_price_for_quantity(service_id: int, quantity: int, base_price: int):
    tiers = await get_bulk_prices(service_id)
    applicable_price = base_price
    for t in tiers:
        if quantity >= t["min_quantity"]:
            applicable_price = t["price_per_unit"]
    return applicable_price

async def add_bulk_price(service_id: int, min_qty: int, price: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO service_bulk_prices (service_id, min_quantity, price_per_unit) VALUES (?, ?, ?)", (service_id, min_qty, price))
        await db.execute("UPDATE service_bulk_prices SET price_per_unit=? WHERE service_id=? AND min_quantity=?", (price, service_id, min_qty))
        await db.commit()

async def delete_bulk_price(price_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM service_bulk_prices WHERE id = ?", (price_id,))
        await db.commit()

async def get_expiring_subscriptions(days: int = 3):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM subscriptions WHERE is_active = 1 "
            "AND date(end_date) = date('now', '+' || ? || ' days')", (days,)
        )
        return await cursor.fetchall()


# CART SYSTEM

async def add_to_cart(user_id: int, service_id: int, price: int, quantity: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if already exists then update quantity
        cursor = await db.execute("SELECT id, quantity FROM cart_items WHERE user_id=? AND service_id=?", (user_id, service_id))
        row = await cursor.fetchone()
        if row:
            await db.execute("UPDATE cart_items SET quantity = quantity + ? WHERE id=?", (quantity, row[0]))
        else:
            await db.execute(
                "INSERT INTO cart_items (user_id, service_id, price, quantity) VALUES (?, ?, ?, ?)",
                (user_id, service_id, price, quantity)
            )
        await db.commit()

async def get_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT c.id, c.service_id, c.quantity, c.price, s.name as service_name
            FROM cart_items c
            JOIN services s ON c.service_id = s.id
            WHERE c.user_id = ?
            ORDER BY c.added_at ASC
            """,
            (user_id,)
        )
        return await cursor.fetchall()

async def update_cart_quantity(cart_id: int, user_id: int, quantity: int):
    async with aiosqlite.connect(DB_PATH) as db:
        if quantity > 0:
            await db.execute("UPDATE cart_items SET quantity=? WHERE id=? AND user_id=?", (quantity, cart_id, user_id))
        else:
            await db.execute("DELETE FROM cart_items WHERE id=? AND user_id=?", (cart_id, user_id))
        await db.commit()

async def remove_from_cart(cart_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart_items WHERE id=? AND user_id=?", (cart_id, user_id))
        await db.commit()

async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart_items WHERE user_id=?", (user_id,))
        await db.commit()


# ═══════════════════════════════════════════════════
# REFERRAL CAMPAIGNS
# ═══════════════════════════════════════════════════

async def create_referral_campaign(name: str, description: str, required_referrals: int,
                                   reward_type: str, reward_value: int, reward_description: str = None, deadline: str = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO referral_campaigns (name, description, required_referrals, reward_type, reward_value, reward_description, deadline) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, description, required_referrals, reward_type, reward_value, reward_description, deadline)
        )
        await db.commit()
        return cursor.lastrowid


async def get_active_referral_campaigns():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM referral_campaigns WHERE is_active=1 ORDER BY id DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_all_referral_campaigns():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM referral_campaigns ORDER BY id DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_referral_campaign(campaign_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM referral_campaigns WHERE id=?", (campaign_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def toggle_referral_campaign(campaign_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE referral_campaigns SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?",
            (campaign_id,)
        )
        await db.commit()


async def delete_referral_campaign(campaign_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM referral_campaigns WHERE id=?", (campaign_id,))
        await db.execute("DELETE FROM referral_campaign_participants WHERE campaign_id=?", (campaign_id,))
        await db.commit()


async def get_campaign_participant(campaign_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM referral_campaign_participants WHERE campaign_id=? AND user_id=?",
            (campaign_id, user_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def join_campaign(campaign_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO referral_campaign_participants (campaign_id, user_id) VALUES (?, ?)",
                (campaign_id, user_id)
            )
            await db.commit()
            return True
        except Exception:
            return False


async def increment_campaign_referral(campaign_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE referral_campaign_participants SET current_referrals = current_referrals + 1 "
            "WHERE campaign_id=? AND user_id=?",
            (campaign_id, user_id)
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT current_referrals FROM referral_campaign_participants WHERE campaign_id=? AND user_id=?",
            (campaign_id, user_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def mark_campaign_reward_given(campaign_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE referral_campaign_participants SET reward_given=1 WHERE campaign_id=? AND user_id=?",
            (campaign_id, user_id)
        )
        await db.commit()


async def get_campaign_stats(campaign_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        total = (await (await db.execute(
            "SELECT COUNT(*) FROM referral_campaign_participants WHERE campaign_id=?", (campaign_id,)
        )).fetchone())[0]
        rewarded = (await (await db.execute(
            "SELECT COUNT(*) FROM referral_campaign_participants WHERE campaign_id=? AND reward_given=1", (campaign_id,)
        )).fetchone())[0]
        total_refs = (await (await db.execute(
            "SELECT COALESCE(SUM(current_referrals),0) FROM referral_campaign_participants WHERE campaign_id=?", (campaign_id,)
        )).fetchone())[0]
        in_progress = total - rewarded
        return {"total_participants": total, "participants": total, "rewarded": rewarded, "in_progress": in_progress, "total_referrals": total_refs}


async def get_user_active_campaigns(user_id: int):
    """Returns campaigns user is participating in with their progress."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT c.*, p.current_referrals, p.reward_given, p.joined_at
            FROM referral_campaigns c
            JOIN referral_campaign_participants p ON c.id = p.campaign_id
            WHERE p.user_id=? AND c.is_active=1
            ORDER BY c.id DESC
            """,
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def set_campaign_participant_email(campaign_id: int, user_id: int, email: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE referral_campaign_participants SET customer_email=? WHERE campaign_id=? AND user_id=?",
            (email, campaign_id, user_id)
        )
        await db.commit()


async def mark_campaign_participant_activated(campaign_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE referral_campaign_participants SET activation_status='activated', activated_at=CURRENT_TIMESTAMP WHERE campaign_id=? AND user_id=?",
            (campaign_id, user_id)
        )
        await db.commit()


async def set_campaign_participant_activation_status(campaign_id: int, user_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE referral_campaign_participants SET activation_status=? WHERE campaign_id=? AND user_id=?",
            (status, campaign_id, user_id)
        )
        await db.commit()


async def get_campaign_completed_participants(campaign_id: int):
    """Get participants who completed the target (reward_given=1)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT p.*, u.username, u.full_name FROM referral_campaign_participants p "
            "LEFT JOIN users u ON p.user_id = u.id "
            "WHERE p.campaign_id=? AND p.reward_given=1 ORDER BY p.activated_at DESC, p.id DESC",
            (campaign_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_all_pending_campaign_activations():
    """Get all completed participants awaiting admin activation."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT p.*, c.name as campaign_name, c.required_referrals, c.reward_type, c.reward_value, "
            "u.username, u.full_name "
            "FROM referral_campaign_participants p "
            "JOIN referral_campaigns c ON p.campaign_id = c.id "
            "LEFT JOIN users u ON p.user_id = u.id "
            "WHERE p.reward_given=1 AND (p.activation_status IS NULL OR p.activation_status='pending' OR p.activation_status='ready') "
            "ORDER BY p.id DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def execute_sql(query: str, params: tuple = ()):
    """Generic helper for simple UPDATE/INSERT queries."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(query, params)
        await db.commit()


async def get_bonus_monitoring():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c1 = await db.execute("SELECT SUM(bonus_balance) as total_bonus FROM users WHERE bonus_balance > 0")
        total_bonus_row = await c1.fetchone()
        total_bonus = total_bonus_row['total_bonus'] if total_bonus_row and total_bonus_row['total_bonus'] else 0
        
        c2 = await db.execute("SELECT id, username, full_name, bonus_balance FROM users WHERE bonus_balance > 0 ORDER BY bonus_balance DESC LIMIT 10")
        top_users_rows = await c2.fetchall()
        top_users = [dict(r) for r in top_users_rows]
        
        c3 = await db.execute("SELECT user_id, amount, reason, created_at FROM bonus_transactions ORDER BY created_at DESC LIMIT 5")
        recent_txs_rows = await c3.fetchall()
        recent_txs = [dict(r) for r in recent_txs_rows]
        
        return {
            'total_bonus': total_bonus,
            'top_users': top_users,
            'recent_txs': recent_txs
        }
