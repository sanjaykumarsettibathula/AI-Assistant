import psycopg2
from psycopg2 import OperationalError, sql
import os
from dotenv import load_dotenv
import time
from functools import wraps

# Load environment variables
load_dotenv()

def handle_db_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        delay = 1
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay)
                delay *= 2  # Exponential backoff
    return wrapper

@handle_db_errors
def get_conn():
    """Establish database connection with enhanced error handling"""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT", "5432"),
            sslmode='require',
            connect_timeout=5
        )
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"❌ Connection failed. Please verify:")
        print(f"- DB_HOST: {os.getenv('DB_HOST')}")
        print(f"- Is the Supabase instance running?")
        print(f"- Have you enabled IPv4 in Supabase settings?")
        print(f"- Is your password correct? (Starts with {os.getenv('DB_PASSWORD','')[0:2]}...)")
        raise

def init_db():
    """Initialize database tables with verification"""
    print("🔄 Initializing database...")
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Create feedback table
                cur.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    helpful BOOLEAN,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                ''')
                
                # Create conversations table
                cur.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                ''')
                
                # Create indexes for better performance
                cur.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON conversations(session_id)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id)')
                
                conn.commit()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

@handle_db_errors
def log_conversation(session_id, user_input, ai_response):
    """Log conversation with retry logic"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('''
            INSERT INTO conversations (session_id, user_input, ai_response)
            VALUES (%s, %s, %s)
            ''', (session_id, user_input, ai_response))
            conn.commit()

@handle_db_errors
def log_feedback(query, response, helpful):
    """Log feedback with error handling"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('''
            INSERT INTO feedback (query, response, helpful)
            VALUES (%s, %s, %s)
            ''', (query, response, helpful))
            conn.commit()

@handle_db_errors
def get_history(session_id, limit=10):
    """Retrieve conversation history with safeguards"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('''
            SELECT user_input, ai_response 
            FROM conversations 
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            ''', (session_id, limit))
            return cur.fetchall()

# Test connection when module loads
if __name__ == "__main__":
    print("🧪 Testing database connection...")
    try:
        init_db()
        print("Connection test successful!")
    except Exception as e:
        print(f"Connection test failed: {e}")
        print("\nTroubleshooting steps:")
        print("1. Verify your .env file contains correct Supabase credentials")
        print("2. Check if your IP is whitelisted in Supabase")
        print("3. Ensure you've enabled IPv4 in Supabase settings")
        print("4. Try using the connection pooler URL instead")