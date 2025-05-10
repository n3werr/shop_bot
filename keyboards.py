from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

def get_payment_keyboard(provider_token: str, price: int, currency: str = "RUB"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 Оплатить",
            pay=True
        )],
        [InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_product"
        )]
    ])
def get_main_menu():
    buttons = [
        [KeyboardButton(text="📦 Товары")],
        [KeyboardButton(text="📋 Мои заказы")],
        [KeyboardButton(text="👤 Личный кабинет")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def remove_menu():
    return ReplyKeyboardRemove()

def get_product_nav(current_index, total_products):
    buttons = [
        [
            InlineKeyboardButton(text="⬅️", callback_data=f"prev_{current_index}"),
            InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{current_index}"),
            InlineKeyboardButton(text="➡️", callback_data=f"next_{current_index}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)