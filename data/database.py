import sqlite3
import os
def init_db():
    os.makedirs('data', exist_ok=True)  # Создаёт папку если её нет
    conn = sqlite3.connect(os.path.join('data', 'orders.db'))
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item TEXT,
        size TEXT,
        price_uah INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def save_order(user_id, item, size, price_uah):
    conn = sqlite3.connect('data/orders.db')
    c = conn.cursor()
    c.execute("INSERT INTO orders (user_id, item, size, price_uah) VALUES (?, ?, ?, ?)",
              (user_id, item, size, price_uah))
    conn.commit()
    conn.close()
