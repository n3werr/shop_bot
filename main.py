import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InputFile
from aiogram.enums import ParseMode
from keyboards import get_main_menu, remove_menu, get_product_nav

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config():
    config = {'BOT_TOKEN': '', 'ADMINS': []}
    try:
        with open('config.txt', 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line.startswith('BOT_TOKEN='):
                    config['BOT_TOKEN'] = line.split('=')[1].strip()
                elif line.startswith('ADMINS='):
                    admins = line.split('=')[1].strip().split(',')
                    config['ADMINS'] = [int(admin_id.strip()) for admin_id in admins if admin_id.strip().isdigit()]
    except FileNotFoundError:
        logger.error("Файл config.txt не найден!")
        raise
    except Exception as e:
        logger.error(f"Ошибка при чтении конфига: {e}")
        raise
    if not config['BOT_TOKEN']:
        raise ValueError("Токен бота не указан в config.txt")
    return config


try:
    config = load_config()
    BOT_TOKEN = config['BOT_TOKEN']
    ADMINS = config['ADMINS']
except Exception as e:
    logger.critical(f"Не удалось загрузить конфигурацию: {e}")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def get_products():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, price, photo FROM products")
    products = cursor.fetchall()
    conn.close()
    return products


async def show_product(message: types.Message, product_index: int = 0):
    products = get_products()
    if not products:
        await message.answer("Товары отсутствуют", reply_markup=get_main_menu())
        return

    product_index = product_index % len(products)
    product = products[product_index]

    caption = (
        f"📛 <b>{product[1]}</b>\n\n"
        f"📝 <i>{product[2]}</i>\n\n"
        f"💰 Цена: <b>{product[3]} руб.</b>\n"
        f"🆔 ID: {product[0]}"
    )

    photo_path = product[4] if len(product) > 4 else None

    if photo_path and os.path.exists(photo_path):
        try:
            with open(photo_path, 'rb') as photo_file:
                await message.answer_photo(
                    types.BufferedInputFile(photo_file.read(), filename="product.jpg"),
                    caption=caption,
                    reply_markup=get_product_nav(product_index, len(products)),
                    parse_mode=ParseMode.HTML
                )
                return
        except Exception as e:
            logger.error(f"Ошибка при загрузке фото: {e}")

    await message.answer(
        text=caption,
        reply_markup=get_product_nav(product_index, len(products)),
        parse_mode=ParseMode.HTML
    )


async def is_admin(user_id: int):
    return user_id in ADMINS


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_name = message.from_user.full_name
    await message.answer(
        f"Привет, {user_name}! 👋\n\nДобро пожаловать в наш магазин.",
        reply_markup=get_main_menu()
    )


@dp.message(F.text == "📦 Товары")
async def handle_products(message: Message):
    await show_product(message)


@dp.message(F.text == "📋 Мои заказы")
async def handle_orders(message: Message):
    await message.answer("У вас пока нет заказов", reply_markup=get_main_menu())


@dp.message(F.text == "👤 Личный кабинет")
async def handle_profile(message: Message):
    user = message.from_user
    profile_text = (
        f"👤 Ваш профиль:\n\n"
        f"Имя: {user.full_name}\n"  
        f"Username: @{user.username if user.username else 'не указан'}\n"
        f"ID: {user.id}"
    )
    await message.answer(profile_text, reply_markup=get_main_menu())


@dp.callback_query(F.data.startswith("prev_") | F.data.startswith("next_") | F.data.startswith("buy_"))
async def handle_product_nav(callback: types.CallbackQuery):
    action, index = callback.data.split("_")
    index = int(index)
    products = get_products()

    if not products:
        await callback.answer("Товары отсутствуют")
        return

    if action == "prev":
        new_index = (index - 1) % len(products)
    elif action == "next":
        new_index = (index + 1) % len(products)
    elif action == "buy":
        await callback.answer("Товар добавлен в заказы!")
        return

    try:
        await callback.message.edit_media()
    except:
        pass

    await show_product(callback.message, new_index)
    await callback.answer()


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда только для администраторов!", reply_markup=get_main_menu())
        return
    await message.answer("🛡️ Вы администратор этого бота!", reply_markup=get_main_menu())


@dp.message(Command("hide"))
async def cmd_hide(message: Message):
    await message.answer("Меню скрыто", reply_markup=remove_menu())


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=get_main_menu())


async def main():
    logger.info("Starting bot...")
    logger.info(f"Loaded configuration: {len(ADMINS)} admins")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())