import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
from colorama import init, Fore, Style

from api import next_character_count_reset

init()

defult_monthly_quota = 5000
defult_voice = 'Brittney Hart'
defult_model = 'eleven_multilingual_v2'

def sql_launch():
    connection = sqlite3.connect('elevenlabs_database.db')
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
        name TEXT,
        username TEXT,
        id INTEGER PRIMARY KEY,
        voice TEXT,
        model TEXT,
        last_dubbing_language TEXT,
        monthly_quota INT,
        last_quota_update TEXT,
        character_count INT, 
        number_of_messages INT,
        first_message TEXT,
        last_message TEXT
        )
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
        name TEXT,
        id INT,
        message TEXT,
        character INT,
        time TEXT
        )
        ''')
    
    connection.commit()
    connection.close()


def sql_check(name: str, username: str, id: int) -> None:
    connection = sqlite3.connect('elevenlabs_database.db')
    cursor = connection.cursor()
    
    row = cursor.execute(f"SELECT * FROM users WHERE id = {id}").fetchall()
    
    if row == []:
        cursor.execute(f"INSERT INTO users(name, username, id, voice, model, last_dubbing_language, monthly_quota, last_quota_update, character_count, number_of_messages, first_message, last_message) "
                       f"VALUES ('{name}', '{username}', '{id}', '{defult_voice}', '{defult_model}', 'None', {defult_monthly_quota}, '{datetime.now().strftime('%Y.%m.%d')}', 0, 0, '{datetime.now().strftime('%Y.%m.%d %H:%M')}', '{datetime.now().strftime('%Y.%m.%d, %H:%M')}')")
    
    else:
        if name != row[0][0] or username != row[0][1]:
            cursor.execute("UPDATE users SET name = ? WHERE id = ?", (name, id))
            cursor.execute("UPDATE users SET username = ? WHERE id = ?", (username, id))

    connection.commit()
    connection.close()


def sql_select(variable: str, id: int):
    connection = sqlite3.connect('elevenlabs_database.db')
    cursor = connection.cursor()

    result = cursor.execute(f"SELECT {variable} FROM users WHERE id = {id}").fetchall()[0][0]

    connection.commit()
    connection.close()

    return result


def sql_change(variable: str, new_value: str, id: int):
    connection = sqlite3.connect('elevenlabs_database.db')
    cursor = connection.cursor()
    
    cursor.execute(f"UPDATE users SET '{variable}' = '{new_value}' WHERE id = {id}")
    
    connection.commit()
    connection.close()


def sql_message(name: str, username: str, id: int, message: str, character: int):
    connection = sqlite3.connect('elevenlabs_database.db')
    cursor = connection.cursor()

    sql_check(name=name, username=username, id=id)

    nw = datetime.now().strftime('%Y.%m.%d %H:%M')
    cursor.execute(f"INSERT INTO history(name, id, message, character, time) "
                   f"VALUES (?, ?, ?, ?, ?)", (name, id, message, character, nw))
    cursor.execute("UPDATE users SET last_message = ? WHERE id = ?", (nw, id))
    cursor.execute("UPDATE users SET number_of_messages = number_of_messages + 1 WHERE id = ?", (id,))
    cursor.execute("UPDATE users SET character_count = character_count + ? WHERE id = ?", (character, id))
    cursor.execute("UPDATE users SET monthly_quota = monthly_quota - ? WHERE id = ?", (character, id))

    print(f'{Fore.GREEN}{message}{Style.RESET_ALL} by {name}')

    connection.commit()
    connection.close()


def sql_quota(id: int):
    connection = sqlite3.connect('elevenlabs_database.db')
    cursor = connection.cursor()
    
    last_quota_update = sql_select('last_quota_update', id)
    last_quota_update = datetime.strptime(last_quota_update, '%Y.%m.%d')
    next_reset = next_character_count_reset()

    nw = datetime.now().strftime('%Y.%m.%d')
                                 
    if last_quota_update < (next_reset - relativedelta(months=1)):
        cursor.execute("UPDATE users SET last_quota_update = ? WHERE id = ?", (nw, id))
        cursor.execute("UPDATE users SET monthly_quota = ? WHERE id = ?", (defult_monthly_quota, id))
        quote = defult_monthly_quota

    else:
        quote = sql_select('monthly_quota', id)
    

    connection.commit()
    connection.close()

    return quote


sql_launch()