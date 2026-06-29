"""
database/db.py
--------------
MySQL connection pool. Edit the credentials to match your local MySQL setup.
"""

import mysql.connector
from mysql.connector import pooling

_pool = pooling.MySQLConnectionPool(
    pool_name="naru_pool",
    pool_size=5,
    host="localhost",
    port=3307,          # change if your MySQL runs on 3306
    user="root",
    password="narayananmysql@2006",   # ← change this
    database="ai_chatbot",
    charset="utf8mb4",
)


def get_connection():
    return _pool.get_connection()
