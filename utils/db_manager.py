# -*- coding: utf-8 -*
# utils/db_manager.py
import sqlite3
import json
import os
from datetime import datetime

# 数据库文件路径 (会自动在项目根目录创建 snowboard_data.db)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "snowboard_data.db")


def init_db():
    """初始化数据库：如果表不存在，就创建它"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建 records 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        brand TEXT,
        model TEXT,
        condition_score REAL,
        price_low INTEGER,
        price_high INTEGER,
        suggest_price INTEGER,
        expert_review TEXT,
        calculation_json TEXT
    )
    ''')
    conn.commit()
    conn.close()


def save_record(data: dict):
    """
    保存一条鉴定记录
    data 参数应包含: brand, model, score, price_low, price_high, review, calc_process
    """
    try:
        # 确保数据库存在
        init_db()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 插入数据
        cursor.execute('''
        INSERT INTO records (
            timestamp, brand, model, condition_score, 
            price_low, price_high, suggest_price, 
            expert_review, calculation_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("brand", "UNKNOWN"),
            data.get("model", ""),
            data.get("condition_score", 0),
            data.get("price_low", 0),
            data.get("price_high", 0),
            data.get("suggest_price", 0),
            data.get("expert_review", ""),
            json.dumps(data.get("calculation_process", []))  # 列表转 JSON 字符串存
        ))

        conn.commit()
        conn.close()
        print("✅ 数据已保存到 SQLite")
    except Exception as e:
        print(f"❌ 数据库保存失败: {e}")


def get_recent_records(limit=10):
    """读取最近的记录"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM records ORDER BY id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()

    # 转成字典列表返回
    results = []
    for row in rows:
        results.append({
            "id": row[0],
            "timestamp": row[1],
            "brand": row[2],
            "model": row[3],
            "score": row[4],
            "price": f"¥{row[5]} - ¥{row[6]}",
            "review": row[8]
        })

    conn.close()
    return results