import logging
import re
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from aiogram.utils import executor
from config import BOT_TOKEN, CHANNEL_ID, REVIEW_LINK, MANAGER_USERNAME, MANAGER_ID, ADMINS, JPY_TO_UAH, USD_MARKUP
from data.database import init_db, save_order

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

user_data = {}
post_log = []
buy_callback = CallbackData("buy", "title", "size")

def escape_md(text):
    return re.sub(r'([_\*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Используй /new09 чтобы создать пост.")

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("Нет доступа.")
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔁 Обновить курс", callback_data="update_rate"),
        InlineKeyboardButton("📊 Текущий курс", callback_data="show_rate"),
        InlineKeyboardButton("📋 Лог постов", callback_data="show_log")
    )
    await message.answer("👑 Панель администратора:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data in ['update_rate', 'show_rate', 'show_log'])
async def admin_callbacks(call: types.CallbackQuery):
    global JPY_TO_UAH
    if call.from_user.id not in ADMINS:
        return await call.answer("Нет доступа", show_alert=True)

    if call.data == 'update_rate':
        await call.message.answer("Введи новый курс \u00a5 -> UAH:")
        user_data[call.from_user.id] = {'awaiting': 'new_rate'}
    elif call.data == 'show_rate':
        await call.message.answer(f"Курс: 1 \u00a5 = {JPY_TO_UAH}₴")
    elif call.data == 'show_log':
        if not post_log:
            await call.message.answer("Лог пуст.")
        else:
            await call.message.answer('\n\n'.join(post_log[-10:]))

@dp.message_handler(lambda message: user_data.get(message.from_user.id, {}).get('awaiting') == 'new_rate')
async def update_rate_handler(message: types.Message):
    global JPY_TO_UAH
    try:
        rate = float(message.text)
        JPY_TO_UAH = rate
        await message.answer(f"✅ Курс обновлён: 1 \u00a5 = {rate}₴")
        user_data.pop(message.from_user.id)
    except:
        await message.answer("Введите корректное число.")

@dp.message_handler(commands=['new09'])
async def new_post_start(message: types.Message):
    user_data[message.from_user.id] = {'step': 'photo'}
    await message.answer("Отправь фото товара:")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    data = user_data.get(message.from_user.id)
    if not data or data.get('step') != 'photo':
        return
    user_data[message.from_user.id]['photo'] = message.photo[-1].file_id
    user_data[message.from_user.id]['step'] = 'title'
    await message.answer("Название одежды:")

@dp.message_handler()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    data = user_data.get(user_id)

    if not data:
        return

    step = data.get('step')

    if step == 'title':
        data['title'] = message.text
        data['step'] = 'size'
        await message.answer("Размеры:")

    elif step == 'size':
        data['size'] = message.text
        data['step'] = 'price'
        await message.answer("Цена в йенах:")

    elif step == 'price':
        try:
            price_jpy = int(message.text)
            price_uah_base = price_jpy * JPY_TO_UAH
            price_usd_base = price_uah_base / 40
            price_usd_final = int(price_usd_base + USD_MARKUP)
            price_uah_final = int(price_usd_final * 40)

            title = escape_md(data['title'].upper())
            size = escape_md(data['size'])
            uah = price_uah_final
            usd = price_usd_final

            post_text = (
                f"🔥 *{title}* 🔥\n\n"
                f"📏 *Размеры в наличии:* `{size}`\n"
                f"💸 *Цена с доставкой:* *{uah}₴* / *${usd}*\n\n"
                f"📦 _Прямо из Китая_\n"
                f"✅ _\\ Как оригинал_\n"
                f"🚀 _Быстрая доставка_\n"
                f"💬 _Есть вопросы\\? Менеджер всё подскажет_\n\n"
                f"👇 *Нажми кнопку ниже, чтобы оформить заказ* 👇"
            )

            kb = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton(
                    "🛒 Купить",
                    callback_data=buy_callback.new(
                        title=data['title'][:30],
                        size=data['size'][:10]
                    )
                ),
                InlineKeyboardButton("Отзывы 📝", url=REVIEW_LINK)
            )

            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=data['photo'],
                caption=post_text,
                parse_mode="MarkdownV2",
                reply_markup=kb
            )

            await message.answer("✅ Пост опубликован!")
            save_order(user_id, data['title'], data['size'], price_uah_final)
            post_log.append(post_text)
            user_data.pop(user_id)

        except ValueError:
            await message.answer("Введите цену в йенах числом.")

@dp.callback_query_handler(buy_callback.filter())
async def handle_buy_callback(call: types.CallbackQuery, callback_data: dict):
    user = call.from_user
    title = callback_data['title']
    size = callback_data['size']

    msg = (
        f"🛍 *Новая заявка!*\n\n"
        f"👤 Покупатель: [{user.full_name}](tg://user?id={user.id})\n"
        f"📦 Товар: *{title}*\n"
        f"📏 Размер: `{size}`\n"
        f"🕒 Время: `{call.message.date}`"
    )

    await call.answer("📨 Заявка отправлена менеджеру!", show_alert=True)
    await bot.send_message(
        chat_id=MANAGER_ID,
        text=msg,
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)
