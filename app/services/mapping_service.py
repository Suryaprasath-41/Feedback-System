"""
Service for handling Excel file uploads for staff-subject mapping data.
"""

import pandas as pd
import logging
from typing import Tuple, List
from app.models.database import get_db

logger = logging.getLogger(__name__)

# Required headers for mapping Excel file
MAPPING_REQUIRED_HEADERS = ['department', 'semester', 'staff', 'subject']

def validate_mapping_excel(file_path: str) -> Tuple[bool, str, pd.DataFrame]:
    """
    Validate the uploaded mapping Excel file.
    
    Returns:
        Tuple of (is_valid, error_message, dataframe)
    """
    try:
        df = pd.read_excel(file_path)
        
        if df.empty:
            return False, "Excel file is empty", None
        
        df.columns = df.columns.str.strip().str.lower()
        
        missing_headers = [h for h in MAPPING_REQUIRED_HEADERS if h not in df.columns]
        if missing_headers:
            return False, f"Missing required columns: {', '.join(missing_headers)}. Required: {', '.join(MAPPING_REQUIRED_HEADERS)}", None
        
        if df[MAPPING_REQUIRED_HEADERS].isnull().any().any():
            return False, "Excel file contains empty values in required columns", None
        
        df['department'] = df['department'].astype(str).str.strip()
        df['semester'] = df['semester'].astype(str).str.strip()
        df['staff'] = df['staff'].astype(str).str.strip()
        df['subject'] = df['subject'].astype(str).str.strip()
        
        df = df[(df['department'] != '') & (df['semester'] != '') & 
                (df['staff'] != '') & (df['subject'] != '')]
        
        if df.empty:
            return False, "No valid mapping records found after cleaning", None
        
        return True, "", df
        
    except Exception as e:
        logger.error(f"Error validating mapping Excel file: {e}")
        return False, f"Error reading Excel file: {str(e)}", None

def process_mapping_excel(file_path: str, replace_existing: bool = False) -> Tuple[bool, str, dict]:
    """
    Process the uploaded Excel file and add mappings to database.
    
    Args:
        file_path: Path to the Excel file
        replace_existing: If True, delete existing mappings for the dept/sem before adding new ones
    
    Returns:
        Tuple of (success, message, stats_dict)
    """
    is_valid, error_msg, df = validate_mapping_excel(file_path)
    if not is_valid:
        return False, error_msg, {}
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            added_count = 0
            skipped_count = 0
            dept_sem_combinations = set()
            
            for _, row in df.iterrows():
                dept = str(row['department'])
                sem = str(row['semester'])
                staff = str(row['staff'])
                subject = str(row['subject'])
                
                dept_sem_key = (dept, sem)
                
                # If replace_existing is True and this is first record for this dept/sem, delete existing
                if replace_existing and dept_sem_key not in dept_sem_combinations:
                    cursor.execute('''
                        DELETE FROM admin_mappings 
                        WHERE department = ? AND semester = ?
                    ''', (dept, sem))
                    dept_sem_combinations.add(dept_sem_key)
                
                # Try to insert the mapping
                try:
                    cursor.execute('''
                        INSERT INTO admin_mappings (department, semester, staff, subject) 
                        VALUES (?, ?, ?, ?)
                    ''', (dept, sem, staff, subject))
                    added_count += 1
                except Exception:
                    skipped_count += 1
            
            conn.commit()
        
        stats = {
            'total': len(df),
            'added': added_count,
            'skipped': skipped_count
        }
        
        if added_count > 0:
            message = f"Successfully added {added_count} mappings. "
            if skipped_count > 0:
                message += f"{skipped_count} duplicates were skipped."
            return True, message, stats
        else:
            return False, f"No new mappings added. All {skipped_count} records were duplicates.", stats
    
    except Exception as e:
        logger.error(f"Error processing mapping Excel: {e}")
        return False, f"Error processing mappings: {str(e)}", {}

def create_sample_mapping_excel(output_path: str = 'sample_mapping.xlsx'):
    """
    Create a sample Excel file with the correct format for mappings.
    """
    sample_data = {
        'department': ['Computer Science -A', 'Computer Science -A', 'Computer Science -A'],
        'semester': ['2', '2', '2'],
        'staff': ['Dr. John Doe', 'Prof. Jane Smith', 'Dr. Robert Brown'],
        'subject': ['Data Structures', 'Operating Systems', 'Database Management']
    }
    
    df = pd.DataFrame(sample_data)
    df.to_excel(output_path, index=False)
    logger.info(f"Sample mapping Excel file created: {output_path}")
    return output_path

def bulk_add_staff(staff_list: List[str]) -> Tuple[int, int]:
    """
    Bulk add staff members.
    
    Returns:
        Tuple of (added_count, duplicate_count)
    """
    added_count = 0
    duplicate_count = 0
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for staff_name in staff_list:
            staff_name = staff_name.strip()
            if not staff_name:
                continue
            
            try:
                cursor.execute('INSERT INTO staff (name) VALUES (?)', (staff_name,))
                if cursor.rowcount > 0:
                    added_count += 1
                else:
                    duplicate_count += 1
            except Exception:
                duplicate_count += 1
        
        conn.commit()
    
    return added_count, duplicate_count

def bulk_add_subjects(subject_list: List[str]) -> Tuple[int, int]:
    """
    Bulk add subjects.
    
    Returns:
        Tuple of (added_count, duplicate_count)
    """
    added_count = 0
    duplicate_count = 0
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for subject_name in subject_list:
            subject_name = subject_name.strip()
            if not subject_name:
                continue
            
            try:
                cursor.execute('INSERT INTO subjects (name) VALUES (?)', (subject_name,))
                if cursor.rowcount > 0:
                    added_count += 1
                else:
                    duplicate_count += 1
            except Exception:
                duplicate_count += 1
        
        conn.commit()
    
    return added_count, duplicate_count
