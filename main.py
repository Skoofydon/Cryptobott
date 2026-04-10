import telebot
from telebot import types
import config
import database as db
from cryptobot import CryptoBotClient
from cryptobot.models import Asset

# Инициализация
bot = telebot.TeleBot(config.BOT_TOKEN)
db.init_db()
crypto_client = CryptoBotClient(api_token=config.CRYPTO_PAY_TOKEN, is_mainnet=True)

# ==================== КОНСТАНТЫ ====================
WITHDRAW_FEE_PERCENT = 5  # Комиссия на вывод 5%

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

def create_usdt_check(amount: float, user_id: int = None) -> str:
    """Создает чек USDT через CryptoBot API"""
    try:
        if user_id:
            check = crypto_client.create_check(
                asset=Asset.USDT,
                amount=amount,
                pin_to_user_id=user_id
            )
        else:
            check = crypto_client.create_check(
                asset=Asset.USDT,
                amount=amount
            )
        return check.bot_check_url
    except Exception as e:
        print(f"Ошибка создания чека: {e}")
        return None

def notify_admins(text: str, markup=None):
    for admin_id in config.ADMIN_IDS:
        try:
            bot.send_message(admin_id, text, reply_markup=markup)
        except:
            pass

# ==================== КЛАВИАТУРЫ ====================

def main_menu(user_id: int) -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💰 Баланс", "📋 История")
    markup.add("📥 Пополнить", "📤 Вывести")
    if is_admin(user_id):
        markup.add("🛠 Админ-панель")
    return markup

def admin_panel() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ Начислить баланс")
    markup.add("📋 Заявки на вывод")
    markup.add("👥 Пользователи")
    markup.add("🔙 Назад")
    return markup

def cancel_keyboard() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Отмена")
    return markup

# ==================== КОМАНДЫ ПОЛЬЗОВАТЕЛЯ ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    welcome_text = f"""
👋 Привет, {user_name}!

💎 Кошелек с обменом через чеки CryptoBot

💰 Твой ID: `{user_id}`
💵 Баланс: {db.get_balance(user_id)} USDT

📥 Пополнение: пришли чек админу → получишь баланс
📤 Вывод: создай заявку → получишь чек (комиссия {WITHDRAW_FEE_PERCENT}%)
"""
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=main_menu(user_id))

@bot.message_handler(func=lambda m: m.text == "💰 Баланс")
def show_balance(message):
    user_id = message.from_user.id
    balance = db.get_balance(user_id)
    bot.send_message(message.chat.id, f"💎 Ваш баланс: **{balance} USDT**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📋 История")
def show_history(message):
    user_id = message.from_user.id
    transactions = db.get_user_transactions(user_id, limit=10)
    if not transactions:
        bot.send_message(message.chat.id, "📭 История пуста")
        return
    text = "📋 **Последние операции:**\n\n"
    for tx_type, amount, desc, date in transactions:
        sign = "+" if tx_type == "deposit" else "-"
        text += f"{sign}{abs(amount)} USDT — {desc}\n└ _{date}_\n\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📥 Пополнить")
def deposit_info(message):
    user_id = message.from_user.id
    text = f"""
📥 **Пополнение баланса**

1️⃣ Создайте чек в @CryptoBot на нужную сумму
2️⃣ Отправьте ссылку на чек администратору: @{config.SUPPORT_USERNAME}
3️⃣ Обязательно укажите ваш ID: `{user_id}`

После проверки чека администратор зачислит USDT на ваш внутренний баланс.
"""
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📤 Вывести")
def withdraw_start(message):
    user_id = message.from_user.id
    balance = db.get_balance(user_id)
    if balance <= 0:
        bot.send_message(message.chat.id, "❌ У вас нулевой баланс")
        return
    
    text = f"""
📤 **Вывод средств**

Ваш баланс: {balance} USDT
Комиссия: {WITHDRAW_FEE_PERCENT}%

Введите сумму для вывода в USDT:
"""
    msg = bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(msg, process_withdraw_amount)

def process_withdraw_amount(message):
    if message.text == "❌ Отмена":
        bot.send_message(message.chat.id, "❌ Вывод отменен", reply_markup=main_menu(message.from_user.id))
        return
    
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
        
        user_id = message.from_user.id
        balance = db.get_balance(user_id)
        
        fee = amount * WITHDRAW_FEE_PERCENT / 100
        total_debit = amount + fee
        user_receives = amount
        
        if balance < total_debit:
            bot.send_message(message.chat.id, 
                f"❌ Недостаточно средств.\nБаланс: {balance} USDT\nТребуется: {total_debit} USDT (включая комиссию {fee} USDT)")
            return
        
        text = f"""
📤 **Детали вывода:**

Сумма к получению: {user_receives} USDT
Комиссия ({WITHDRAW_FEE_PERCENT}%): {fee} USDT
**Будет списано с баланса: {total_debit} USDT**

Всё верно? Напишите 👌 **ОК** для подтверждения:
"""
        msg = bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, confirm_withdraw, amount, user_receives, fee)
        
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ Неверная сумма. Введите число:", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_withdraw_amount)

def confirm_withdraw(message, amount, user_receives, fee):
    if message.text == "❌ Отмена":
        bot.send_message(message.chat.id, "❌ Вывод отменен", reply_markup=main_menu(message.from_user.id))
        return
    
    if message.text.upper() not in ["ОК", "OK", "ДА", "YES"]:
        msg = bot.send_message(message.chat.id, "❌ Напишите ОК для подтверждения или Отмена:", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, confirm_withdraw, amount, user_receives, fee)
        return
    
    user_id = message.from_user.id
    total_debit = amount + fee
    
    if not db.subtract_balance(user_id, total_debit, f"Вывод {user_receives} USDT (комиссия {fee})"):
        bot.send_message(message.chat.id, "❌ Ошибка списания", reply_markup=main_menu(user_id))
        return
    
    req_id = db.add_withdraw_request(user_id, user_receives, f"Вывод {user_receives} USDT")
    
    bot.send_message(message.chat.id, 
        f"✅ Заявка на вывод {user_receives} USDT создана.\nС баланса списано: {total_debit} USDT\nОжидайте чек от администратора.",
        reply_markup=main_menu(user_id))
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Выдал чек", callback_data=f"done_withdraw_{req_id}_{user_id}_{user_receives}"))
    
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {user_id}"
    notify_admins(
        f"📤 **Новая заявка на вывод #{req_id}**\n"
        f"👤 {user_info}\n"
        f"💰 Сумма к выдаче: {user_receives} USDT\n"
        f"💸 Комиссия: {fee} USDT\n\n"
        f"Отправьте пользователю чек на {user_receives} USDT и нажмите «Выдал чек»",
        markup
    )

@bot.message_handler(func=lambda m: m.text == "❌ Отмена")
def cancel_action(message):
    """Отмена текущего действия"""
    bot.send_message(message.chat.id, "❌ Действие отменено", reply_markup=main_menu(message.from_user.id))

# ==================== АДМИН-ПАНЕЛЬ====================

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель" and is_admin(m.from_user.id))
def admin_menu(message):
    bot.send_message(message.chat.id, "🛠 Админ-панель", reply_markup=admin_panel())

@bot.message_handler(func=lambda m: m.text == "🔙 Назад")
def back_to_main_menu(message):
    bot.send_message(message.chat.id, "Главное меню", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "➕ Начислить баланс" and is_admin(m.from_user.id))
def admin_add_start(message):
    msg = bot.send_message(message.chat.id, "Введите ID пользователя и сумму через пробел:")
    bot.register_next_step_handler(msg, admin_add_process)

def admin_add_process(message):
    try:
        parts = message.text.split()
        user_id = int(parts[0])
        amount = float(parts[1])
        
        db.add_balance(user_id, amount, f"Пополнение через админа")
        bot.send_message(message.chat.id, f"✅ Баланс пользователя {user_id} пополнен на {amount} USDT")
        
        try:
            bot.send_message(user_id, f"✅ Ваш баланс пополнен на {amount} USDT")
        except:
            pass
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}\nФормат: ID Сумма")

@bot.message_handler(func=lambda m: m.text == "📋 Заявки на вывод" and is_admin(m.from_user.id))
def admin_requests(message):
    reqs = db.get_pending_requests()
    if not reqs:
        bot.send_message(message.chat.id, "Нет активных заявок")
        return
    
    for req in reqs:
        req_id, user_id, amount, address, created_at = req
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Выдал чек", callback_data=f"done_withdraw_{req_id}_{user_id}_{amount}"))
        bot.send_message(message.chat.id, 
            f"🆔 #{req_id}\n👤 ID: {user_id}\n💰 К выдаче: {amount} USDT\n📅 {created_at}",
            reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("done_withdraw_"))
def done_withdraw(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return
    
    _, req_id, user_id, amount = call.data.split("_")
    req_id = int(req_id)
    user_id = int(user_id)
    amount = float(amount)
    
    check_link = create_usdt_check(amount, user_id)
    
    if not check_link:
        bot.answer_callback_query(call.id, "❌ Ошибка создания чека")
        return
    
    db.mark_request_done(req_id)
    
    bot.answer_callback_query(call.id, "✅ Чек создан!")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(call.message.chat.id, f"✅ Заявка #{req_id} обработана\n🔗 Чек: {check_link}")
    
    try:
        bot.send_message(user_id, 
            f"✅ Ваша заявка на вывод {amount} USDT выполнена!\n\n"
            f"🔗 Активируйте чек: {check_link}\n\n"
            f"⚠️ Чек привязан к вашему аккаунту")
    except:
        bot.send_message(call.message.chat.id, f"⚠️ Не удалось уведомить пользователя. Отправьте чек вручную:\n{check_link}")

@bot.message_handler(func=lambda m: m.text == "👥 Пользователи" and is_admin(m.from_user.id))
def admin_all_users(message):
    users = db.get_all_users()
    if not users:
        bot.send_message(message.chat.id, "Нет пользователей")
        return
    
    text = "👥 **Пользователи:**\n\n"
    total = 0
    for user_id, balance, created_at in users[:30]:
        text += f"`{user_id}` — {balance} USDT\n"
        total += balance
    
    text += f"\nВсего: {len(users)} | Сумма: {total} USDT"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
