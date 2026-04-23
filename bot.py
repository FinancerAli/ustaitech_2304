import asyncio
import os
import socket
import logging
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import TelegramObject, Message, Update

import database as db
from config import BOT_TOKEN, ADMIN_IDS, USE_REDIS, REDIS_URL
from handlers import user, admin
from locales import t

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)


class BlockCheckMiddleware:
    """Reject updates from blocked users."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        user_id = None
        if isinstance(event, Update):
            if event.message:
                user_id = event.message.from_user.id
            elif event.callback_query:
                user_id = event.callback_query.from_user.id

        if user_id:
            db_user = await db.get_user(user_id)
            if db_user and db_user["is_blocked"]:
                if isinstance(event, Update) and event.message:
                    from locales import t
                    lang = db_user["language"] or "uz"
                    try:
                        await event.message.answer(t(lang, "blocked"))
                    except Exception:
                        pass
                return

        return await handler(event, data)


async def subscription_checker(bot: Bot):
    while True:
        try:
            subs = await db.get_expiring_subscriptions(3)
            for sub in subs:
                user_id = sub["user_id"]
                user = await db.get_user(user_id)
                lang = user["language"] if user and user["language"] else "uz"
                try:
                    await bot.send_message(user_id, t(lang, "sub_expire_warning", days=3), parse_mode="HTML")
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"Subscription checker error: {e}")
            
        await asyncio.sleep(86400) # Check once a day

async def scheduled_backup(bot: Bot):
    """Send DB backup to admin daily at 03:00."""
    from utils.backup import send_backup
    while True:
        now = datetime.now()
        target = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            for admin_id in ADMIN_IDS:
                await send_backup(bot, admin_id)
        except Exception as e:
            logging.error(f"Scheduled backup error: {e}")


async def daily_report(bot: Bot):
    """Send daily stats report to admin at 22:00."""
    while True:
        now = datetime.now()
        target = now.replace(hour=22, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            stats = await db.get_stats()
            analytics = await db.get_analytics()
            segments = await db.get_crm_segments()
            ticket_stats = await db.get_ticket_stats()

            # ── Section 1: Basic Stats ──
            text = (
                "📊 <b>Kunlik hisobot — 22:00</b>\n\n"
                f"👥 Foydalanuvchilar: <b>{stats['users']}</b>\n"
                f"📦 Jami buyurtmalar: <b>{stats['total_orders']}</b>\n"
                f"⏳ Kutilayotgan: <b>{stats['pending']}</b>\n"
                f"✅ Tasdiqlangan: <b>{stats['confirmed']}</b>\n"
                f"❌ Rad etilgan: <b>{stats['rejected']}</b>\n\n"
            )

            # ── Section 2: Revenue ──
            text += (
                "💰 <b>Daromad:</b>\n"
                f"  📅 Bugun: <b>{stats['today_revenue']:,} so'm</b>\n"
                f"  📅 Hafta: <b>{analytics['week_revenue']:,} so'm</b> ({analytics['week_orders']} ta)\n"
                f"  📆 Oy: <b>{analytics['month_revenue']:,} so'm</b> ({analytics['month_orders']} ta)\n"
                f"  🧾 O'rtacha chek: <b>{analytics['avg_order']:,} so'm</b>\n"
                f"  📈 Konversiya: <b>{stats['conversion']}%</b>\n\n"
            )

            # ── Section 3: CRM Summary ──
            total_u = sum(s["count"] for s in segments.values())
            text += (
                "👥 <b>CRM:</b>\n"
                f"  👑 VIP: {segments['vip']['count']} | "
                f"🟢 Faol: {segments['active']['count']} | "
                f"🆕 Yangi: {segments['new']['count']}\n"
                f"  🔄 Qaytgan: {segments['returning']['count']} | "
                f"1️⃣ 1-martalik: {segments['one_time']['count']} | "
                f"💤 Yo'qolgan: {segments['churned']['count']}\n\n"
            )

            # ── Section 4: Tickets & Problems ──
            text += (
                "🎫 <b>Support:</b>\n"
                f"  📬 Ochiq: <b>{ticket_stats['open']}</b> | "
                f"✅ Javob berilgan: {ticket_stats['answered']}\n"
                f"  ⏱ O'rtacha javob: {ticket_stats['avg_response_min']} daq\n"
                f"  ⏰ Expired (oy): {analytics['expired_count']}\n"
            )

            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, text, parse_mode="HTML")
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"Daily report error: {e}")


async def stock_monitor(bot: Bot):
    """Check stock levels every hour and alert admin when stock reaches 0."""
    while True:
        await asyncio.sleep(3600)  # Check every hour
        try:
            services = await db.get_services(only_active=True)
            for s in services:
                stock = s.get("stock", -1)
                if stock == 0:
                    text = (
                        f"⚠️ <b>Stock ogohlantirish!</b>\n\n"
                        f"📦 <b>{s['name']}</b> — stock 0 ga tushdi!\n"
                        f"Iltimos, qoldiqni yangilang yoki xizmatni o'chiring."
                    )
                    for admin_id in ADMIN_IDS:
                        try:
                            await bot.send_message(admin_id, text, parse_mode="HTML")
                        except Exception:
                            pass
        except Exception as e:
            logging.error(f"Stock monitor error: {e}")


async def main():
    await db.init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    if USE_REDIS:
        storage = RedisStorage.from_url(REDIS_URL)
        logging.info("Using RedisStorage for FSM")
    else:
        storage = MemoryStorage()
        logging.info("Using MemoryStorage for FSM")
        
    dp = Dispatcher(storage=storage)

    dp.update.outer_middleware(BlockCheckMiddleware())

    dp.include_router(admin.router)
    dp.include_router(user.router)

    app_env = os.getenv("APP_ENV", "production")
    host = socket.gethostname()
    pid = os.getpid()
    bot_me = await bot.get_me()

    print(f"STARTUP_CHECK env={app_env} host={host} pid={pid} username=@{bot_me.username}", flush=True)
    logging.info(
        "Bot ishga tushdi! env=%s host=%s pid=%s username=@%s",
        app_env,
        host,
        pid,
        bot_me.username,
    )
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(subscription_checker(bot))
    asyncio.create_task(scheduled_backup(bot))
    asyncio.create_task(daily_report(bot))
    asyncio.create_task(stock_monitor(bot))
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
