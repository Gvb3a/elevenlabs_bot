import sqlite3
from datetime import datetime

def sql_launch():
    connection = sqlite3.connect('elevenlabs_database.db')
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
        tg_name TEXT,
        tg_id INTEGER PRIMARY KEY,
        stability FLOAT,
        similarity FLOAT,
        style_exaggeration FLOAT,
        speaker_boost BIT,
        dubbing_source_language TEXT,
        dubbing_target_language TEXT
        )
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message (
        name TEXT,
        message TEXT,
        time TEXT
        )
        ''')
    connection.commit()
    connection.close()
