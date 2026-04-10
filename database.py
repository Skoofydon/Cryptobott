import sqlite3
from typing import List, Tuple, Optional
from datetime import datetime

DB_NAME = "wallet.db"

def init_db() -> None:
    """Создает таблицы если их нет"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Таблица юзеров с балансом
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  balance REAL DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Таблица заявок на вывод
    c.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  user_id INTEGER, 
                  amount REAL, 
                  address TEXT, 
                  status TEXT DEFAULT 'pending',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Таблица истории транзакций
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  type TEXT,
                  amount REAL,
                  description TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

# ==================== БАЛАНС ПОЛЬЗОВАТЕЛЯ ====================

def get_balance(user_id: int) -> float:
    """Возвращает баланс пользователя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0

def add_balance(user_id: int, amount: float, description: str = "Пополнение") -> bool:
    """Начисляет баланс пользователю"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Создаем юзера если нет
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    
    # Пишем в историю
    c.execute("INSERT INTO transactions (user_id, type, amount, description) VALUES (?, 'deposit', ?, ?)",
              (user_id, amount, description))
    
    conn.commit()
    conn.close()
    return True

def subtract_balance(user_id: int, amount: float, description: str = "Списание") -> bool:
    """Списывает баланс пользователя (проверяет достаточно ли средств)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance - ? WHERE user_id=? AND balance >= ?", 
              (amount, user_id, amount))
    success = c.rowcount > 0
    
    if success:
        c.execute("INSERT INTO transactions (user_id, type, amount, description) VALUES (?, 'withdraw', ?, ?)",
                  (user_id, -amount, description))
    
    conn.commit()
    conn.close()
    return success

def user_exists(user_id: int) -> bool:
    """Проверяет существует ли пользователь"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

# ==================== ЗАЯВКИ НА ВЫВОД ====================

def add_withdraw_request(user_id: int, amount: float, address: str) -> int:
    """Создает заявку на вывод, возвращает ID заявки"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO withdraw_requests (user_id, amount, address) VALUES (?, ?, ?)", 
              (user_id, amount, address))
    req_id = c.lastrowid
    conn.commit()
    conn.close()
    return req_id

def get_pending_requests() -> List[Tuple]:
    """Возвращает список необработанных заявок на вывод"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''SELECT id, user_id, amount, address, created_at 
                 FROM withdraw_requests 
                 WHERE status='pending' 
                 ORDER BY created_at''')


rows = c.fetchall()
    conn.close()
    return rows

def mark_request_done(req_id: int) -> bool:
    """Отмечает заявку как выполненную"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE withdraw_requests SET status='done' WHERE id=?", (req_id,))
    success = c.rowcount > 0
    conn.commit()
    conn.close()
    return success

def mark_request_cancelled(req_id: int) -> bool:
    """Отмечает заявку как отмененную"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE withdraw_requests SET status='cancelled' WHERE id=?", (req_id,))
    success = c.rowcount > 0
    conn.commit()
    conn.close()
    return success

def get_request_by_id(req_id: int) -> Optional[Tuple]:
    """Возвращает заявку по ID"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, user_id, amount, address, status, created_at FROM withdraw_requests WHERE id=?", (req_id,))
    row = c.fetchone()
    conn.close()
    return row

# ==================== ПОЛЬЗОВАТЕЛИ ====================

def get_all_users() -> List[Tuple]:
    """Возвращает всех пользователей (для админа)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, balance, created_at FROM users ORDER BY balance DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_users_count() -> int:
    """Возвращает количество пользователей"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_total_balance() -> float:
    """Возвращает сумму балансов всех пользователей"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT SUM(balance) FROM users")
    total = c.fetchone()[0]
    conn.close()
    return total or 0.0

# ==================== ИСТОРИЯ ТРАНЗАКЦИЙ ====================

def get_user_transactions(user_id: int, limit: int = 10) -> List[Tuple]:
    """Возвращает историю транзакций пользователя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''SELECT type, amount, description, created_at 
                 FROM transactions 
                 WHERE user_id=? 
                 ORDER BY created_at DESC 
                 LIMIT ?''', (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_transactions(limit: int = 50) -> List[Tuple]:
    """Возвращает последние транзакции всех пользователей (для админа)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''SELECT user_id, type, amount, description, created_at 
                 FROM transactions 
                 ORDER BY created_at DESC 
                 LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_user_stats(user_id: int) -> dict:
    """Возвращает статистику пользователя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Баланс
    c.execute("SELECT balance, created_at FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row:
        return {"exists": False}
    
    balance, created_at = row
    
    # Сумма пополнений
    c.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='deposit'", (user_id,))
    total_deposit = c.fetchone()[0] or 0
    
    # Сумма выводов
    c.execute("SELECT SUM(ABS(amount)) FROM transactions WHERE user_id=? AND type='withdraw'", (user_id,))
    total_withdraw = c.fetchone()[0] or 0
    
    # Количество транзакций
    c.execute("SELECT COUNT(*) FROM transactions WHERE user_id=?", (user_id,))
    tx_count = c.fetchone()[0]
    
    conn.close()
    
    return {
        "exists": True,
        "balance": balance,
        "created_at": created_at,
        "total_deposit": total_deposit,
        "total_withdraw": total_withdraw,
        "tx_count": tx_count
    }

# ==================== ОЧИСТКА И СБРОС ====================

def reset_database() -> None:


"""Полностью сбрасывает базу данных (ОСТОРОЖНО!)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS users")
    c.execute("DROP TABLE IF EXISTS withdraw_requests")
    c.execute("DROP TABLE IF EXISTS transactions")
    conn.commit()
    conn.close()
    init_db()
    print("⚠️ База данных сброшена!")

def delete_user(user_id: int) -> bool:
    """Удаляет пользователя и все его данные"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    c.execute("DELETE FROM withdraw_requests WHERE user_id=?", (user_id,))
    c.execute("DELETE FROM transactions WHERE user_id=?", (user_id,))
    success = c.rowcount > 0
    conn.commit()
    conn.close()
    return success

# ==================== СТАТИСТИКА ====================

def get_global_stats() -> dict:
    """Возвращает общую статистику"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Пользователи
    c.execute("SELECT COUNT(*), SUM(balance) FROM users")
    users_count, total_balance = c.fetchone()
    
    # Заявки на вывод
    c.execute("SELECT COUNT(*) FROM withdraw_requests WHERE status='pending'")
    pending_withdraws = c.fetchone()[0]
    
    # Транзакции
    c.execute("SELECT COUNT(*), SUM(amount) FROM transactions WHERE type='deposit'")
    tx_count, total_deposits = c.fetchone()
    
    c.execute("SELECT SUM(ABS(amount)) FROM transactions WHERE type='withdraw'")
    total_withdraws = c.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "users_count": users_count or 0,
        "total_balance": total_balance or 0,
        "pending_withdraws": pending_withdraws,
        "total_deposits": total_deposits or 0,
        "total_withdraws": total_withdraws,
        "profit": (total_withdraws - total_deposits) if total_deposits else 0
    }

# ==================== ЗАПУСК ПРИ ИМПОРТЕ ====================

# Автоматически создаем таблицы при импорте модуля
init_db()