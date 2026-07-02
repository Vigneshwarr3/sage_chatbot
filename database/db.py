"""
database/db.py
--------------
MySQL connection pool. Connection settings are read from environment
variables (see .env.example) so the same code works locally and in Docker.
"""

import os

from dotenv import load_dotenv
from mysql.connector import pooling

load_dotenv()

_pool = pooling.MySQLConnectionPool(
    pool_name="Sage_pool",
    pool_size=5,
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", "3307")),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DATABASE", "ai_chatbot"),
    charset="utf8mb4",
)


def get_connection():
    return _pool.get_connection()
