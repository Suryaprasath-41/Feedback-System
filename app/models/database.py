import sqlite3
import os
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'feedback.db')

def get_db_path():
    """Get the database path and ensure the directory exists."""
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    return DATABASE_PATH

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize the database with all required tables."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registerno TEXT NOT NULL,
                department TEXT NOT NULL,
                semester TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(registerno, department, semester)
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_students_regno 
            ON students(registerno)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_students_dept_sem 
            ON students(department, semester)
        ''')
        
        # Departments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Semesters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semesters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Staff table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Subjects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Admin mappings table (staff-subject mappings)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department TEXT NOT NULL,
                semester TEXT NOT NULL,
                staff TEXT NOT NULL,
                subject TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(department, semester, staff, subject)
            )
        ''')
        
        # Ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registerno TEXT NOT NULL,
                department TEXT NOT NULL,
                semester TEXT NOT NULL,
                staff TEXT NOT NULL,
                subject TEXT NOT NULL,
                q1 REAL NOT NULL,
                q2 REAL NOT NULL,
                q3 REAL NOT NULL,
                q4 REAL NOT NULL,
                q5 REAL NOT NULL,
                q6 REAL NOT NULL,
                q7 REAL NOT NULL,
                q8 REAL NOT NULL,
                q9 REAL NOT NULL,
                q10 REAL NOT NULL,
                average REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ratings_regno 
            ON ratings(registerno)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ratings_dept_sem_staff_subj 
            ON ratings(department, semester, staff, subject)
        ''')
        
        # Submitted feedback tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submitted_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registerno TEXT NOT NULL UNIQUE,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")

def drop_all_tables():
    """Drop all tables - use with caution!"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
        conn.commit()
        logger.warning("All tables dropped")
