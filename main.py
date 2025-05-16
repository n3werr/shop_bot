import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InputFile, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import get_main_menu, remove_menu, get_product_nav, get_payment_confirmation_keyboard
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Состояния для FSM
class PaymentStates(StatesGroup):
    WAITING_PAYMENT_PROOF = State()
    ADMIN_CONFIRMATION = State()


def load_config():
    config = {'BOT_TOKEN': '', 'ADMINS': [], 'PAYMENT_DETAILS': ''}
    try:
        with open('config.txt', 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line.startswith('BOT_TOKEN='):
                    config['BOT_TOKEN'] = line.split('=')[1].strip()
                elif line.startswith('ADMINS='):
                    admins = line.split('=')[1].strip().split(',')
                    config['ADMINS'] = [int(admin_id.strip()) for admin_id in admins if admin_id.strip().isdigit()]
                elif line.startswith('PAYMENT_DETAILS='):
                    config['PAYMENT_DETAILS'] = line.split('=')[1].strip()
    except FileNotFoundError:
        logger.error("Файл config.txt не найден!")
        raise
    except Exception as e:
        logger.error(f"Ошибка при чтении конфига: {e}")
        raise
    if not config['BOT_TOKEN']:
        raise ValueError("Токен бота не указан в config.txt")
    if not config['PAYMENT_DETAILS']:
        raise ValueError("Реквизиты для оплаты не указаны в config.txt")
    return config


try:
    config = load_config()
    BOT_TOKEN = config['BOT_TOKEN']
    ADMINS = config['ADMINS']
    PAYMENT_DETAILS = config['PAYMENT_DETAILS']
except Exception as e:
    logger.critical(f"Не удалось загрузить конфигурацию: {e}")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище временных данных о заказах
pending_orders: Dict[int, Dict] = {}  # {user_id: {product_id: int, product_name: str, price: float}}


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

#Регистрация пользователя
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    username = message.from_user.username
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT tg_id FROM users WHERE tg_id = ?", (user_id,))
        existing_user = cursor.fetchone()

        if not existing_user:
            cursor.execute(
                "INSERT INTO users (tg_id, username, full_name) VALUES (?, ?, ?)",
                (user_id, username, user_name)
            )
            conn.commit()
            logger.info(f"Добавлен новый пользователь: {user_name} (ID: {user_id})")
        else:
            logger.info(f"Пользователь уже существует: {user_name} (ID: {user_id})")

    except sqlite3.Error as e:
        logger.error(f"Ошибка при работе с БД: {e}")
    finally:
        conn.close()

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


@dp.callback_query(F.data.startswith("prev_") | F.data.startswith("next_"))
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

    try:
        await callback.message.edit_media()
    except:
        print('Ошибка получения данных')

    await show_product(callback.message, new_index)
    await callback.answer()


@dp.callback_query(F.data.startswith("buy_"))
async def handle_buy_product(callback: types.CallbackQuery):
    product_index = int(callback.data.split("_")[1])
    products = get_products()

    if not products:
        await callback.answer("Товары отсутствуют")
        return

    product = products[product_index % len(products)]
    user_id = callback.from_user.id

    pending_orders[user_id] = {
        'product_id': product[0],
        'product_name': product[1],
        'price': product[3],
        'username': callback.from_user.username,
        'full_name': callback.from_user.full_name
    }

    payment_message = (
        f"💳 <b>Оплата товара:</b> {product[1]}\n"
        f"💰 Сумма к оплате: <b>{product[3]} руб.</b>\n\n"
        f"📝 <b>Реквизиты для оплаты:</b>\n"
        f"{PAYMENT_DETAILS}\n\n"
        f"После оплаты нажмите кнопку 'Я оплатил' и пришлите скриншот чека."
    )

    await callback.message.answer(
        payment_message,
        reply_markup=get_payment_confirmation_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@dp.callback_query(F.data == "confirm_payment")
async def handle_payment_confirmation(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Пожалуйста, пришлите скриншот подтверждения оплаты.",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(PaymentStates.WAITING_PAYMENT_PROOF)
    await callback.answer()


@dp.message(PaymentStates.WAITING_PAYMENT_PROOF, F.photo)
async def handle_payment_proof(message: Message, state: FSMContext):
    user_id = message.from_user.id
    order_info = pending_orders.get(user_id)

    if not order_info:
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте оформить заказ снова.")
        await state.clear()
        return

    # Отправляем администратору уведомление о новом заказе
    admin_message = (
        f"🛒 <b>Новый заказ!</b>\n\n"
        f"👤 Пользователь: {order_info['full_name']} (@{order_info['username']})\n"
        f"🆔 ID: {user_id}\n\n"
        f"📦 Товар: {order_info['product_name']}\n"
        f"💰 Сумма: {order_info['price']} руб.\n\n"
        f"Подтвердите получение оплаты:"
    )

    admin_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{user_id}"),
            types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{user_id}")
        ]
    ])

    # Отправляем фото и информацию администраторам
    for admin_id in ADMINS:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=message.photo[-1].file_id,
                caption=admin_message,
                reply_markup=admin_keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {e}")

    await message.answer(
        "Спасибо! Ваш платеж отправлен на проверку администратору. "
        "Мы уведомим вас, как только платеж будет подтвержден.",
        reply_markup=get_main_menu()
    )
    await state.clear()


@dp.callback_query(F.data.startswith("admin_confirm_") | F.data.startswith("admin_reject_"))
async def handle_admin_decision(callback: CallbackQuery):
    action, user_id = callback.data.split("_")[1], int(callback.data.split("_")[2])
    order_info = pending_orders.get(user_id)

    if not order_info:
        await callback.answer("Заказ не найден!")
        return

    if action == "confirm":
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"✅ Ваш платеж за товар '{order_info['product_name']}' подтвержден! "
                     f"Спасибо за покупку!",
                reply_markup=get_main_menu()
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")

        await callback.answer("Платеж подтвержден!")
        await callback.message.edit_caption(
            caption=f"✅ Платеж подтвержден администратором {callback.from_user.full_name}",
            reply_markup=None
        )
    else:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"❌ Ваш платеж за товар '{order_info['product_name']}' отклонен администратором. "
                     f"Пожалуйста, свяжитесь с поддержкой для уточнения деталей.",
                reply_markup=get_main_menu()
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")

        await callback.answer("Платеж отклонен!")
        await callback.message.edit_caption(
            caption=f"❌ Платеж отклонен администратором {callback.from_user.full_name}",
            reply_markup=None
        )

    if user_id in pending_orders:
        del pending_orders[user_id]


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
    logger.info("Start")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())