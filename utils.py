"""
Utils module - UPDATED to use SQLite database instead of CSV files
"""
import hashlib
import base64
import logging

# Lazy import to avoid circular dependency
def _get_db():
    """Get database connection - lazy import to avoid circular dependency."""
    from app.models.database import get_db
    return get_db()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Secret key for encryption (in a real application, this should be stored securely)
SECRET_KEY = "VSB_FEEDBACK_SYSTEM_SECRET_KEY"

def normalize_regno(regno):
    """Normalize a registration number by removing leading zeros."""
    try:
        return str(int(regno))
    except (ValueError, TypeError):
        return regno

def encrypt_regno(regno):
    """
    Encrypt a registration number using a one-way hash function.
    """
    if not regno:
        logging.error("Empty registration number")
        return ""
    
    normalized_regno = normalize_regno(regno)
    input_str = normalized_regno + SECRET_KEY
    hash_obj = hashlib.sha256(input_str.encode())
    hash_str = base64.b64encode(hash_obj.digest()).decode('utf-8')
    return hash_str[:32]

def is_encrypted(value):
    """Check if a value is already encrypted."""
    if not value:
        return False
    try:
        if len(value) == 32:
            return all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in value)
    except Exception as e:
        logging.error(f"Error checking encryption: {e}")
    return False

def read_csv_as_list(filename):
    """
    UPDATED: Return a list of values from the database instead of CSV file.
    Kept for backward compatibility.
    """
    with _get_db() as conn:
        cursor = conn.cursor()
        
        # Determine which table to query based on filename
        if 'departments' in filename.lower():
            cursor.execute('SELECT name FROM departments ORDER BY name')
        elif 'semesters' in filename.lower():
            cursor.execute('SELECT name FROM semesters ORDER BY name')
        elif 'staff' in filename.lower():
            cursor.execute('SELECT name FROM staff ORDER BY name')
        elif 'subject' in filename.lower():
            cursor.execute('SELECT name FROM subjects ORDER BY name')
        else:
            return []
        
        return [row[0] for row in cursor.fetchall()]

def load_admin_mapping(department, semester):
    """
    UPDATED: Return a list of mapping dictionaries from database.
    """
    mappings = []
    dep_norm = department.strip()
    sem_norm = semester.strip()
    
    # Normalize semester (remove "Semester" prefix if present)
    if sem_norm.lower().startswith("semester"):
        sem_norm = sem_norm[len("semester"):].strip()
    
    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT department, semester, staff, subject 
            FROM admin_mappings 
            WHERE department = ? AND semester = ?
        ''', (dep_norm, sem_norm))
        
        for row in cursor.fetchall():
            mappings.append({
                'department': row[0],
                'semester': row[1],
                'staff': row[2],
                'subject': row[3]
            })
    
    return mappings

def update_admin_mappings(department, semester, new_mappings):
    """
    UPDATED: Overwrite existing mappings in database.
    """
    dep_norm = department.strip()
    sem_norm = semester.strip()
    
    # Normalize semester
    if sem_norm.lower().startswith("semester"):
        sem_norm = sem_norm[len("semester"):].strip()
    
    with _get_db() as conn:
        cursor = conn.cursor()
        
        # Delete existing mappings for this department/semester
        cursor.execute('''
            DELETE FROM admin_mappings 
            WHERE department = ? AND semester = ?
        ''', (dep_norm, sem_norm))
        
        # Insert new mappings
        for mapping in new_mappings:
            cursor.execute('''
                INSERT INTO admin_mappings (department, semester, staff, subject) 
                VALUES (?, ?, ?, ?)
            ''', (
                mapping.get('department', dep_norm),
                mapping.get('semester', sem_norm),
                mapping.get('staff', ''),
                mapping.get('subject', '')
            ))

def append_ratings(rating_rows):
    """
    UPDATED: Append rating rows to database instead of CSV.
    """
    with _get_db() as conn:
        cursor = conn.cursor()
        
        for row in rating_rows:
            # Insert rating
            cursor.execute('''
                INSERT INTO ratings 
                (registerno, department, semester, staff, subject, 
                 q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, average) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['registerno'],
                row['department'],
                row['semester'],
                row['staff'],
                row['subject'],
                float(row['q1']),
                float(row['q2']),
                float(row['q3']),
                float(row['q4']),
                float(row['q5']),
                float(row['q6']),
                float(row['q7']),
                float(row['q8']),
                float(row['q9']),
                float(row['q10']),
                float(row['average'])
            ))
            
            # Mark as submitted
            cursor.execute('''
                INSERT OR IGNORE INTO submitted_feedback (registerno) 
                VALUES (?)
            ''', (row['registerno'],))

def get_student_info(registerno):
    """
    UPDATED: Return student info from database by registration number.
    """
    logging.info(f"Validating {registerno}")
    reg_num = normalize_regno(registerno)
    
    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT registerno, department, semester 
            FROM students 
            WHERE registerno = ?
        ''', (reg_num,))
        
        row = cursor.fetchone()
        if row:
            logging.info(f"Validated {registerno} [Status: OK]")
            return {
                'registerno': row[0],
                'department': row[1],
                'semester': row[2]
            }
    
    logging.info(f"Validated {registerno} [Status: FAILED]")
    return None

def has_submitted_feedback(registerno):
    """
    UPDATED: Return True if the student has already submitted feedback (from database).
    """
    reg_num = normalize_regno(registerno)
    
    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM submitted_feedback 
            WHERE registerno = ?
        ''', (reg_num,))
        
        result = cursor.fetchone()
        if result:
            logging.info(f"Feedback found for {registerno}")
            return True
    
    return False

def update_mainratings():
    """
    UPDATED: Aggregate ratings from database.
    This function is kept for compatibility but now works with database.
    """
    aggregated = {}
    
    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT department, semester, staff, subject, 
                   q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, average 
            FROM ratings
        ''')
        
        for row in cursor.fetchall():
            dep, sem, staff, subject = row[0], row[1], row[2], row[3]
            key = (dep, sem, staff, subject)
            
            if key not in aggregated:
                aggregated[key] = {
                    'q_sums': [0.0] * 10,
                    'count': 0,
                    'total_avg': 0.0
                }
            
            # Add individual question ratings
            for i in range(10):
                aggregated[key]['q_sums'][i] += row[4 + i]
            
            aggregated[key]['total_avg'] += row[14]  # average
            aggregated[key]['count'] += 1
    
    # Store aggregated results (you can save this to a table if needed)
    return aggregated

def normalize_semester(semester):
    """Normalize semester string by removing 'semester' prefix if present."""
    semester = semester.strip()
    if semester.lower().startswith("semester"):
        semester = semester[len("semester"):].strip()
    return semester
