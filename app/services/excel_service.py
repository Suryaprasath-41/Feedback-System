"""
Service for handling Excel file uploads for student data.
"""

import pandas as pd
import logging
from typing import Tuple, List
from app.models.student import Student

logger = logging.getLogger(__name__)

# Required headers for student Excel file
REQUIRED_HEADERS = ['registerno', 'department', 'semester']

def validate_excel_file(file_path: str) -> Tuple[bool, str, pd.DataFrame]:
    """
    Validate the uploaded Excel file.
    
    Returns:
        Tuple of (is_valid, error_message, dataframe)
    """
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Check if file is empty
        if df.empty:
            return False, "Excel file is empty", None
        
        # Convert column names to lowercase for comparison
        df.columns = df.columns.str.strip().str.lower()
        
        # Check for required headers
        missing_headers = [h for h in REQUIRED_HEADERS if h not in df.columns]
        if missing_headers:
            return False, f"Missing required columns: {', '.join(missing_headers)}. Required: {', '.join(REQUIRED_HEADERS)}", None
        
        # Check for empty values
        if df[REQUIRED_HEADERS].isnull().any().any():
            return False, "Excel file contains empty values in required columns", None
        
        # Clean up the data
        df['registerno'] = df['registerno'].astype(str).str.strip()
        df['department'] = df['department'].astype(str).str.strip()
        df['semester'] = df['semester'].astype(str).str.strip()
        
        # Remove any rows where registerno is empty after stripping
        df = df[df['registerno'] != '']
        
        if df.empty:
            return False, "No valid student records found after cleaning", None
        
        return True, "", df
        
    except Exception as e:
        logger.error(f"Error validating Excel file: {e}")
        return False, f"Error reading Excel file: {str(e)}", None

def process_student_excel(file_path: str) -> Tuple[bool, str, dict]:
    """
    Process the uploaded Excel file and add students to database.
    
    Returns:
        Tuple of (success, message, stats_dict)
    """
    # Validate file
    is_valid, error_msg, df = validate_excel_file(file_path)
    if not is_valid:
        return False, error_msg, {}
    
    # Prepare students data
    students_data = []
    for _, row in df.iterrows():
        students_data.append((
            str(row['registerno']),
            str(row['department']),
            str(row['semester'])
        ))
    
    # Add students in bulk
    added_count, duplicate_count, duplicates = Student.bulk_add(students_data)
    
    stats = {
        'total': len(students_data),
        'added': added_count,
        'duplicates': duplicate_count,
        'duplicate_list': duplicates[:20]  # Limit to first 20 for display
    }
    
    if added_count > 0:
        message = f"Successfully added {added_count} students. "
        if duplicate_count > 0:
            message += f"{duplicate_count} duplicates were skipped."
        return True, message, stats
    else:
        return False, f"No new students added. All {duplicate_count} records were duplicates.", stats

def create_sample_excel(output_path: str = 'sample_students.xlsx'):
    """
    Create a sample Excel file with the correct format.
    """
    sample_data = {
        'registerno': ['922524243001', '922524243002', '922524243003'],
        'department': ['Computer Science', 'Computer Science', 'Computer Science'],
        'semester': ['2', '2', '2']
    }
    
    df = pd.DataFrame(sample_data)
    df.to_excel(output_path, index=False)
    logger.info(f"Sample Excel file created: {output_path}")
    return output_path
