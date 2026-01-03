# database.py
import sqlite3
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import logging
import os
import re

logger = logging.getLogger(__name__)

def adapt_datetime(dt):
    return dt.isoformat()

def convert_datetime(b):
    return datetime.fromisoformat(b.decode())

sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("datetime", convert_datetime)

conn = sqlite3.connect('data/anonchat.db', detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
cursor = conn.cursor()

def initialize_database():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        language_code TEXT,
        encrypted_name TEXT,
        encrypted_username TEXT,
        tag_enabled INTEGER DEFAULT 0,
        tag_text TEXT,
        custom_tag TEXT,
        custom_tag_enabled INTEGER DEFAULT 0,
        admin_tag_enabled INTEGER DEFAULT 0,
        creator_tag_enabled INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        is_creator INTEGER DEFAULT 0,
        is_coowner INTEGER DEFAULT 0,
        protect_content INTEGER DEFAULT 0,
        autodel_time INTEGER DEFAULT 0,
        banned INTEGER DEFAULT 0,
        muted_until DATETIME,
        warnings INTEGER DEFAULT 0,
        last_message_text TEXT,
        last_message_time DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
        message_count INTEGER DEFAULT 0,
        captcha_passed INTEGER DEFAULT 0
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        message_id INTEGER,
        user_id INTEGER,
        original_message_id INTEGER,
        original_sender_id INTEGER,
        message_type TEXT,
        content TEXT,
        tag_enabled INTEGER,
        tag_text TEXT,
        custom_tag TEXT,
        custom_tag_enabled INTEGER,
        admin_tag INTEGER DEFAULT 0,
        creator_tag INTEGER DEFAULT 0,
        coowner_tag INTEGER DEFAULT 0,
        protect_content INTEGER DEFAULT 0,
        paid_media INTEGER DEFAULT 0,
        paid_stars INTEGER DEFAULT 0,
        is_reply INTEGER DEFAULT 0,
        reply_to_message_id INTEGER,
        is_edited INTEGER DEFAULT 0,
        edited_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (message_id, user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS message_map (
        user_message_id INTEGER,
        target_user_id INTEGER,
        target_message_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_message_id, target_user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ignored_users (
        user_id INTEGER,
        ignored_user_id INTEGER,
        PRIMARY KEY (user_id, ignored_user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stats (
        date TEXT PRIMARY KEY,
        message_count INTEGER DEFAULT 0
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id INTEGER,
        date TEXT,
        message_count INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, date)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS warnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        admin_id INTEGER,
        reason TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS paid_media_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        media_owner_id INTEGER,
        buyer_id INTEGER,
        stars_count INTEGER,
        payload TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_original ON messages(original_message_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_map ON message_map(user_message_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ignored_users ON ignored_users(user_id)')

    CREATOR_ID = int(os.getenv('CREATOR_ID', '8326355672'))
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (CREATOR_ID,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (user_id, is_creator, created_at, last_active, captcha_passed)
            VALUES (?, 1, ?, ?, 1)
        ''', (CREATOR_ID, datetime.now(), datetime.now()))
    else:
        cursor.execute('UPDATE users SET is_creator = 1 WHERE user_id = ?', (CREATOR_ID,))
    
    cursor.execute('SELECT value FROM bot_settings WHERE key = ?', ('bot_start_time',))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO bot_settings (key, value) VALUES (?, ?)', 
                      ('bot_start_time', datetime.now().isoformat()))

    conn.commit()

def encrypt_text(text):
    if not text:
        return ''
    return base64.b64encode(text.encode()).decode()

def decrypt_text(encrypted):
    if not encrypted:
        return ''
    return base64.b64decode(encrypted.encode()).decode()

def get_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        return {
            'user_id': row[0],
            'language_code': row[1],
            'encrypted_name': row[2],
            'encrypted_username': row[3],
            'tag_enabled': bool(row[4]),
            'tag_text': row[5],
            'custom_tag': row[6],
            'custom_tag_enabled': bool(row[7]),
            'admin_tag_enabled': bool(row[8]),
            'creator_tag_enabled': bool(row[9]),
            'is_admin': bool(row[10]),
            'is_creator': bool(row[11]),
            'is_coowner': bool(row[12]),
            'protect_content': bool(row[13]),
            'autodel_time': row[14],
            'banned': bool(row[15]),
            'muted_until': row[16],
            'warnings': row[17],
            'last_message_text': row[18],
            'last_message_time': row[19],
            'created_at': row[20],
            'last_active': row[21],
            'message_count': row[22],
            'captcha_passed': bool(row[23])
        }
    return None

def update_user(user_id, updates: Dict[str, Any]):
    set_clause = ', '.join([f'{key} = ?' for key in updates.keys()])
    values = list(updates.values())
    values.append(user_id)
    cursor.execute(f'UPDATE users SET {set_clause} WHERE user_id = ?', values)
    conn.commit()

def update_stats(user_id):
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        INSERT INTO stats (date, message_count) 
        VALUES (?, 1)
        ON CONFLICT(date) DO UPDATE SET 
        message_count = message_count + 1
    ''', (today,))
    cursor.execute('''
        INSERT INTO user_stats (user_id, date, message_count) 
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, date) DO UPDATE SET 
        message_count = message_count + 1
    ''', (user_id, today))
    cursor.execute('UPDATE users SET last_active = ?, message_count = message_count + 1 WHERE user_id = ?', 
                  (datetime.now(), user_id))
    conn.commit()

def get_active_users():
    cursor.execute('SELECT user_id FROM users WHERE banned = 0 AND captcha_passed = 1')
    return [row[0] for row in cursor.fetchall()]

def get_admin_users():
    cursor.execute('SELECT user_id FROM users WHERE (is_admin = 1 OR is_creator = 1 OR is_coowner = 1) AND banned = 0 AND captcha_passed = 1')
    return [row[0] for row in cursor.fetchall()]

def save_message(message_data: Dict[str, Any]):
    cursor.execute('''
        INSERT INTO messages 
        (message_id, user_id, original_message_id, original_sender_id, message_type, content, 
         tag_enabled, tag_text, custom_tag, custom_tag_enabled, admin_tag, creator_tag, coowner_tag,
         protect_content, paid_media, paid_stars, is_reply, reply_to_message_id, is_edited, edited_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        message_data['message_id'],
        message_data['user_id'],
        message_data['original_message_id'],
        message_data['original_sender_id'],
        message_data['message_type'],
        message_data['content'],
        message_data['tag_enabled'],
        message_data['tag_text'],
        message_data['custom_tag'],
        message_data['custom_tag_enabled'],
        message_data['admin_tag'],
        message_data['creator_tag'],
        message_data['coowner_tag'],
        message_data['protect_content'],
        message_data['paid_media'],
        message_data['paid_stars'],
        message_data['is_reply'],
        message_data['reply_to_message_id'],
        message_data.get('is_edited', 0),
        message_data.get('edited_at')
    ))
    conn.commit()

def save_message_map(user_message_id, target_user_id, target_message_id):
    cursor.execute('INSERT OR REPLACE INTO message_map (user_message_id, target_user_id, target_message_id) VALUES (?, ?, ?)', 
                  (user_message_id, target_user_id, target_message_id))
    conn.commit()

def get_message_map(original_message_id, target_user_id):
    cursor.execute('SELECT target_message_id FROM message_map WHERE user_message_id = ? AND target_user_id = ?', 
                  (original_message_id, target_user_id))
    result = cursor.fetchone()
    return result[0] if result else None

def get_original_message_info(message_id, user_id):
    cursor.execute('SELECT original_message_id, original_sender_id FROM messages WHERE message_id = ? AND user_id = ?', 
                  (message_id, user_id))
    return cursor.fetchone()

def get_messages_by_original(original_message_id):
    cursor.execute('SELECT user_id, message_id, message_type, content FROM messages WHERE original_message_id = ?', 
                  (original_message_id,))
    return cursor.fetchall()

def get_message_content(original_message_id, user_id):
    cursor.execute('SELECT content FROM messages WHERE original_message_id = ? AND user_id = ?', 
                  (original_message_id, user_id))
    result = cursor.fetchone()
    return result[0] if result else None

def update_message_content(original_message_id, new_content, is_edited=True):
    if is_edited:
        cursor.execute('UPDATE messages SET content = ?, is_edited = 1, edited_at = ? WHERE original_message_id = ?', 
                      (new_content, datetime.now(), original_message_id))
    else:
        cursor.execute('UPDATE messages SET content = ? WHERE original_message_id = ?', 
                      (new_content, original_message_id))
    conn.commit()

def delete_messages_by_original(original_message_id, exclude_user_id=None):
    if exclude_user_id:
        cursor.execute('DELETE FROM messages WHERE original_message_id = ? AND user_id != ?', 
                      (original_message_id, exclude_user_id))
    else:
        cursor.execute('DELETE FROM messages WHERE original_message_id = ?', (original_message_id,))
    cursor.execute('DELETE FROM message_map WHERE user_message_id = ?', (original_message_id,))
    conn.commit()

def add_ignored_user(user_id, ignored_user_id):
    cursor.execute('INSERT OR IGNORE INTO ignored_users (user_id, ignored_user_id) VALUES (?, ?)', 
                  (user_id, ignored_user_id))
    conn.commit()

def remove_ignored_user(user_id, ignored_user_id):
    cursor.execute('DELETE FROM ignored_users WHERE user_id = ? AND ignored_user_id = ?', 
                  (user_id, ignored_user_id))
    conn.commit()

def is_ignored(user_id, target_user_id):
    cursor.execute('SELECT 1 FROM ignored_users WHERE user_id = ? AND ignored_user_id = ?', 
                  (user_id, target_user_id))
    return cursor.fetchone() is not None

def get_bot_setting(key, default=None):
    cursor.execute('SELECT value FROM bot_settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    return result[0] if result else default

def set_bot_setting(key, value):
    cursor.execute('INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()

def add_warning(user_id, admin_id, reason):
    cursor.execute('INSERT INTO warnings (user_id, admin_id, reason) VALUES (?, ?, ?)', 
                  (user_id, admin_id, reason))
    conn.commit()

def get_top_users(limit=5):
    cursor.execute('''
        SELECT user_id, message_count, encrypted_name, encrypted_username, tag_enabled, tag_text, 
               custom_tag, custom_tag_enabled FROM users 
        WHERE banned = 0 AND captcha_passed = 1
        ORDER BY message_count DESC 
        LIMIT ?
    ''', (limit,))
    return cursor.fetchall()

def get_daily_stats():
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT message_count FROM stats WHERE date = ?', (today,))
    result = cursor.fetchone()
    return result[0] if result else 0

def get_user_daily_stats(user_id):
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT message_count FROM user_stats WHERE user_id = ? AND date = ?', (user_id, today))
    result = cursor.fetchone()
    return result[0] if result else 0

def get_total_users():
    cursor.execute('SELECT COUNT(*) FROM users WHERE banned = 0 AND captcha_passed = 1')
    return cursor.fetchone()[0]

def get_total_messages():
    cursor.execute('SELECT COUNT(*) FROM messages')
    return cursor.fetchone()[0]

def cleanup_old_messages():
    cursor.execute('SELECT user_id, autodel_time FROM users WHERE autodel_time > 0')
    users_with_autodel = cursor.fetchall()
    
    deleted_count = 0
    for user_id, autodel_time in users_with_autodel:
        cutoff_time = datetime.now() - timedelta(minutes=autodel_time)
        
        cursor.execute('''
            SELECT m.user_id, m.message_id 
            FROM messages m
            WHERE m.original_sender_id = ? AND m.created_at < ?
        ''', (user_id, cutoff_time))
        
        old_messages = cursor.fetchall()
        
        cursor.execute('DELETE FROM messages WHERE original_sender_id = ? AND created_at < ?', (user_id, cutoff_time))
        cursor.execute('DELETE FROM message_map WHERE user_message_id IN (SELECT original_message_id FROM messages WHERE original_sender_id = ? AND created_at < ?)', (user_id, cutoff_time))
        deleted_count += len(old_messages)
    
    conn.commit()
    return deleted_count

def delete_user_data(user_id):
    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM messages WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM ignored_users WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM user_stats WHERE user_id = ?', (user_id,))
    conn.commit()

def get_bot_start_time():
    result = get_bot_setting('bot_start_time')
    if result:
        return datetime.fromisoformat(result)
    start_time = datetime.now()
    set_bot_setting('bot_start_time', start_time.isoformat())
    return start_time

def save_paid_media_sale(media_owner_id, buyer_id, stars_count, payload):
    cursor.execute('INSERT INTO paid_media_sales (media_owner_id, buyer_id, stars_count, payload) VALUES (?, ?, ?, ?)', 
                  (media_owner_id, buyer_id, stars_count, payload))
    conn.commit()

def get_original_sender_id(original_message_id):
    cursor.execute('SELECT original_sender_id FROM messages WHERE original_message_id = ? LIMIT 1', (original_message_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def validate_tag_text(text):
    if not text or len(text.strip()) == 0:
        return False
    
    if len(text) > 50:
        return False
    
    pattern = re.compile(r'^[a-zA-Zа-яА-ЯёЁ0-9\s\-_.,!?@#$%^&*()+=:;\'"\[\]{}|<>/\\]+$')
    if not pattern.match(text):
        return False
    
    return True