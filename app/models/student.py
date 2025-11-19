import logging
from .database import get_db
from utils import normalize_regno, encrypt_regno, is_encrypted

logger = logging.getLogger(__name__)

class Student:
    @staticmethod
    def add(registerno, department, semester):
        """Add a new student to the database."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO students (registerno, department, semester)
                VALUES (?, ?, ?)
            ''', (registerno, department, semester))
            return cursor.lastrowid
    
    @staticmethod
    def bulk_add(students):
        """Add multiple students at once.
        students: list of tuples (registerno, department, semester)
        Returns: (added_count, duplicate_count, duplicates_list)
        """
        added = []
        duplicates = []
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            for registerno, department, semester in students:
                try:
                    # Check if student already exists
                    cursor.execute('''
                        SELECT registerno FROM students 
                        WHERE registerno = ? AND department = ? AND semester = ?
                    ''', (registerno, department, semester))
                    
                    if cursor.fetchone():
                        duplicates.append(registerno)
                    else:
                        cursor.execute('''
                            INSERT INTO students (registerno, department, semester)
                            VALUES (?, ?, ?)
                        ''', (registerno, department, semester))
                        added.append(registerno)
                except Exception as e:
                    logger.error(f"Error adding student {registerno}: {e}")
                    duplicates.append(registerno)
        
        return len(added), len(duplicates), duplicates
    
    @staticmethod
    def delete(registerno, department, semester):
        """Delete a student from the database."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM students 
                WHERE registerno = ? AND department = ? AND semester = ?
            ''', (registerno, department, semester))
            return cursor.rowcount > 0
    
    @staticmethod
    def get_by_regno(registerno):
        """Get student info by registration number."""
        reg_num = normalize_regno(registerno)
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT registerno, department, semester 
                FROM students 
                WHERE registerno = ?
            ''', (reg_num,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'registerno': row[0],
                    'department': row[1],
                    'semester': row[2]
                }
            return None
    
    @staticmethod
    def get_by_dept_sem(department, semester):
        """Get all students for a department and semester."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT registerno, department, semester 
                FROM students 
                WHERE department = ? AND semester = ?
                ORDER BY registerno
            ''', (department, semester))
            
            return [{'registerno': row[0], 'department': row[1], 'semester': row[2]} 
                    for row in cursor.fetchall()]
    
    @staticmethod
    def get_all():
        """Get all students."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT registerno, department, semester 
                FROM students 
                ORDER BY department, semester, registerno
            ''')
            
            return [{'registerno': row[0], 'department': row[1], 'semester': row[2]} 
                    for row in cursor.fetchall()]
    
    @staticmethod
    def exists(registerno, department=None, semester=None):
        """Check if a student exists."""
        reg_num = normalize_regno(registerno)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            if department and semester:
                cursor.execute('''
                    SELECT 1 FROM students 
                    WHERE registerno = ? AND department = ? AND semester = ?
                ''', (reg_num, department, semester))
            else:
                cursor.execute('''
                    SELECT 1 FROM students 
                    WHERE registerno = ?
                ''', (reg_num,))
            
            return cursor.fetchone() is not None
    
    @staticmethod
    def count():
        """Get total number of students."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM students')
            return cursor.fetchone()[0]
