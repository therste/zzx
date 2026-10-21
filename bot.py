import asyncio
import logging
import re

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, BusinessConnection
from aiogram.enums import ParseMode

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
BOT_TOKEN = "8960916793:AAGtrjgqtsPM22Lv8icNp95SAPSQNoUwq-4"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ============================================================
# УТИЛИТЫ
# ============================================================
def format_gift_name(slug: str, number: str) -> str:
    formatted_slug = re.sub(r'(?<!^)(?=[A-Z])', ' ', slug)
    return f"{formatted_slug} #{number}"

# ============================================================
# БИЗНЕС-ЛОГИКА
# ============================================================
@dp.business_connection()
async def handle_business_connection(connection: BusinessConnection) -> None:
    pass

@dp.business_message(F.text.regexp(r"^-1\s"))
async def handle_offer(message: Message) -> None:
    if not message.business_connection_id:
        return
    bc_id = message.business_connection_id

    sender_name = message.from_user.full_name if message.from_user else "Unknown"

    parts = message.text.strip().split()
    # -1 <link> <amount> <currency>
    if len(parts) < 3:
        return

    link_raw = parts[1]
    amount = parts[2]
    currency = parts[3].lower() if len(parts) > 3 else "stars"

    if not amount.isdigit():
        return

    link_match = re.search(r"(?:https?://)?t\.me/nft/([A-Za-z]+)-(\d+)", link_raw)
    if not link_match:
        return
    slug, number = link_match.group(1), link_match.group(2)

    try:
        await bot.delete_business_messages(
            business_connection_id=str(bc_id),
            message_ids=[message.message_id]
        )
    except Exception:
        pass

    await asyncio.sleep(3)

    gift_name = format_gift_name(slug, number)
    amount_fmt = f"{int(amount):,}"
    cur_title = "GRАM" if currency == "gram" else "Stаrs"

    text = (
        f"Пoльзoвaтeль ({sender_name}) oтпpaвил(a) вaм пpeдлoжeниe o пoкyпкe "
        f"{gift_name} зa колво {amount_fmt} {cur_title}.\n\n"
        f"Пpeдлoжeние дeйcтвyeт eщё 12ч. 0 мин."
    )

    try:
        await bot.send_message(
            chat_id=message.chat.id,
            text=text,
            business_connection_id=str(bc_id),
        )
    except Exception as e:
        logger.error(f"[offer-send] Ошибка: {e}")

# ============================================================
# ЗАПУСК
# ============================================================
async def main():
    logger.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
