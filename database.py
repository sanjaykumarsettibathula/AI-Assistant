import sqlite3
import os
from datetime import datetime

def get_db():
    db = sqlite3.connect('ai_assistant.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            helpful BOOLEAN,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        db.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_input TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        db.commit()

def log_conversation(session_id, user_input, ai_response):
    with get_db() as db:
        db.execute(
            'INSERT INTO conversations (session_id, user_input, ai_response) VALUES (?, ?, ?)',
            (session_id, user_input, ai_response)
        )
        db.commit()

def log_feedback(session_id, query, response, helpful):
    with get_db() as db:
        db.execute(
            'INSERT INTO feedback (session_id, query, response, helpful) VALUES (?, ?, ?, ?)',
            (session_id, query, response, helpful)
        )
        db.commit()

def get_history(session_id):
    with get_db() as db:
        return db.execute(
            'SELECT user_input, ai_response FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT 10',
            (session_id,)
        ).fetchall()