import sqlite3
from typing import List, Tuple, Optional

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
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
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

def get_all_users() -> List[Tuple]:
    """Возвращает всех пользователей (для админа)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, balance, created_


at FROM users ORDER BY balance DESC")
    rows = c.fetchall()
    conn.close()
    return rows

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

# Автоматически создаем таблицы при импорте модуля
init_db()




