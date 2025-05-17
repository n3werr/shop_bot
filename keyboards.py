from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

def get_payment_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="confirm_payment")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")]
    ])
    return keyboard

def get_payment_method_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить онлайн", callback_data="pay_online")],
        [InlineKeyboardButton(text="👤 Оплатить администратору", callback_data="pay_admin")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_product")]
    ])
    return keyboard

def get_main_menu():
    buttons = [
        [KeyboardButton(text="📦 Товары")],
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