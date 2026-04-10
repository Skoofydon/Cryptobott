import os

# ==================== ОСНОВНЫЕ НАСТРОЙКИ ====================

# Токен бота от @id199142634 (@BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8054662227:AAFCEUkLrAtk0fgBjuDAqoeTPoiq2Vu1idk")

# Токен API от Crypto Pay → Создать приложение
CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN", "562330:AAEmCmEd1QJks9H1I88KCIVyQdj93Z16EAe")

# ==================== АДМИНЫ ====================

# Telegram ID админов (узнать у @getmyid_bot)
admin_ids_str = os.getenv("ADMIN_IDS", "8343022613")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]

# ==================== ПОДДЕРЖКА ====================

# Юзернейм поддержки БЕЗ символа @
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "CryptoSupportANON")

# ==================== КОМИССИИ ====================

# Комиссия на вывод в процентах
WITHDRAW_FEE_PERCENT = float(os.getenv("WITHDRAW_FEE_PERCENT", "5"))

# ==================== ТЕКСТЫ ====================

DEPOSIT_TEXT = """
📥 **Пополнение баланса**

1️⃣ Создайте чек в @CryptoBot на нужную сумму
2️⃣ Отправьте ссылку на чек администратору: @{support}
3️⃣ Обязательно укажите ваш ID: `{user_id}`

⚠️ После проверки чека администратор зачислит USDT на ваш баланс.
"""
