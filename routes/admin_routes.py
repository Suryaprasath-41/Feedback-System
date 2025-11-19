from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import logging
from app.models.database import get_db
from app.models.student import Student
from app.services.excel_service import process_student_excel, create_sample_excel
from app.services.mapping_service import (
    process_mapping_excel, create_sample_mapping_excel,
    bulk_add_staff, bulk_add_subjects
)
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from utils import normalize_regno

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'vsbec':
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash("Incorrect password.", "danger")
            return redirect(url_for('admin.admin_login'))
    return render_template('admin_login.html')

@admin_bp.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@admin_bp.route('/admin/students', methods=['GET'])
def admin_students():
    """Display the student management page."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get departments from students table (actual data)
        cursor.execute('SELECT DISTINCT department FROM students ORDER BY department')
        departments = [row[0] for row in cursor.fetchall()]
        
        # Get semesters from students table (actual data) - these are stored as numbers
        cursor.execute('SELECT DISTINCT semester FROM students ORDER BY CAST(semester AS INTEGER)')
        semesters = [row[0] for row in cursor.fetchall()]
    
    return render_template('admin_students.html',
                         departments=departments,
                         semesters=semesters)

@admin_bp.route('/admin/students/list', methods=['GET'])
def list_students():
    """Get list of students filtered by department and semester."""
    department = request.args.get('department', '').strip()
    semester = request.args.get('semester', '').strip()
    
    if not department or not semester:
        return jsonify({
            'success': False,
            'message': 'Department and semester are required'
        })
    
    try:
        students = Student.get_by_dept_sem(department, semester)
        return jsonify({
            'success': True,
            'students': students,
            'count': len(students)
        })
    except Exception as e:
        logger.error(f"Error listing students: {e}")
        return jsonify({
            'success': False,
            'message': f'Error fetching students: {str(e)}'
        })

@admin_bp.route('/admin/students/add', methods=['POST'])
def add_students():
    """Add students via registration number range."""
    try:
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', '').strip()
        start_reg = request.form.get('startReg', '').strip()
        end_reg = request.form.get('endReg', '').strip()
        
        # Validate inputs
        if not all([department, semester, start_reg, end_reg]):
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            })
        
        # Convert to integers
        start_num = int(start_reg)
        end_num = int(end_reg)
        
        if start_num > end_num:
            return jsonify({
                'success': False,
                'message': 'Start registration number must be less than or equal to end number'
            })
        
        if (end_num - start_num + 1) > 600:
            return jsonify({
                'success': False,
                'message': 'The range should not exceed 600 students'
            })
        
        # Prepare student data
        students_data = []
        for reg_no in range(start_num, end_num + 1):
            students_data.append((str(reg_no), department, semester))
        
        # Add students
        added_count, duplicate_count, duplicates = Student.bulk_add(students_data)
        
        if added_count > 0:
            message = f"Successfully added {added_count} students."
            if duplicate_count > 0:
                message += f" {duplicate_count} duplicates were skipped."
            return jsonify({
                'success': True,
                'message': message,
                'added': added_count,
                'duplicates': duplicate_count
            })
        else:
            return jsonify({
                'success': False,
                'message': f'All {duplicate_count} students already exist'
            })
    
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid registration number format'
        })
    except Exception as e:
        logger.error(f"Error adding students: {e}")
        return jsonify({
            'success': False,
            'message': f'Error adding students: {str(e)}'
        })

@admin_bp.route('/admin/students/upload', methods=['POST'])
def upload_students_excel():
    """Upload students via Excel file."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No file uploaded'
            })
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            })
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': 'Invalid file type. Please upload an Excel file (.xlsx or .xls)'
            })
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'message': f'File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB'
            })
        
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Process file
        success, message, stats = process_student_excel(filepath)
        
        # Clean up uploaded file
        try:
            os.remove(filepath)
        except:
            pass
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'stats': stats
            })
        else:
            return jsonify({
                'success': False,
                'message': message,
                'stats': stats
            })
    
    except Exception as e:
        logger.error(f"Error uploading Excel: {e}")
        return jsonify({
            'success': False,
            'message': f'Error processing file: {str(e)}'
        })

@admin_bp.route('/admin/students/delete', methods=['POST'])
def delete_student():
    """Delete a student."""
    try:
        registerno = request.form.get('registerno', '').strip()
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', '').strip()
        
        if not all([registerno, department, semester]):
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            })
        
        # Normalize registration number
        registerno = normalize_regno(registerno)
        
        # Delete student
        deleted = Student.delete(registerno, department, semester)
        
        if deleted:
            return jsonify({
                'success': True,
                'message': f'Student {registerno} deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Student not found'
            })
    
    except Exception as e:
        logger.error(f"Error deleting student: {e}")
        return jsonify({
            'success': False,
            'message': f'Error deleting student: {str(e)}'
        })

@admin_bp.route('/admin/students/download-sample')
def download_sample():
    """Download a sample Excel file."""
    try:
        sample_path = os.path.join(UPLOAD_FOLDER, 'sample_students.xlsx')
        create_sample_excel(sample_path)
        return send_file(sample_path, as_attachment=True, download_name='sample_students.xlsx')
    except Exception as e:
        logger.error(f"Error creating sample file: {e}")
        flash('Error creating sample file', 'danger')
        return redirect(url_for('admin.admin_students'))

@admin_bp.route('/admin', methods=['GET', 'POST'])
def admin():
    """Admin mapping page."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT name FROM departments ORDER BY name')
        departments = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT name FROM semesters ORDER BY name')
        semesters = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT name FROM staff ORDER BY name')
        staffs = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT name FROM subjects ORDER BY name')
        subjects = [row[0] for row in cursor.fetchall()]
    
    if request.method == 'POST':
        department = request.form.get('department')
        semester = request.form.get('semester')
        staff_list = request.form.getlist('staff')
        subject_list = request.form.getlist('subject')
        
        new_mappings = [
            (department, semester, staff.strip(), subject.strip())
            for staff, subject in zip(staff_list, subject_list)
            if staff.strip() and subject.strip()
        ]
        
        if not new_mappings:
            flash("Please enter at least one valid staff–subject mapping.", "danger")
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Delete existing mappings for this dept/semester
                cursor.execute('''
                    DELETE FROM admin_mappings 
                    WHERE department = ? AND semester = ?
                ''', (department, semester))
                
                # Insert new mappings
                cursor.executemany('''
                    INSERT INTO admin_mappings (department, semester, staff, subject) 
                    VALUES (?, ?, ?, ?)
                ''', new_mappings)
            
            flash("Mapping(s) saved successfully.", "success")
            return redirect(url_for('admin.admin'))
    
    return render_template('admin_mapping.html',
                         departments=departments,
                         semesters=semesters,
                         staffs=staffs,
                         subjects=subjects)

@admin_bp.route('/admin/add_staff', methods=['POST'])
def add_staff():
    """Add a new staff member."""
    try:
        staff_name = request.form.get('staff_name', '').strip()
        if not staff_name:
            return jsonify({
                'success': False,
                'message': 'Staff name cannot be empty'
            })
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO staff (name) VALUES (?)', (staff_name,))
            
            if cursor.rowcount > 0:
                return jsonify({
                    'success': True,
                    'message': f'Successfully added staff: {staff_name}',
                    'staff_name': staff_name
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Staff name already exists'
                })
    
    except Exception as e:
        logger.error(f"Error adding staff: {e}")
        return jsonify({
            'success': False,
            'message': f'Error adding staff: {str(e)}'
        })

@admin_bp.route('/admin/add_subject', methods=['POST'])
def add_subject():
    """Add a new subject."""
    try:
        subject_name = request.form.get('subject_name', '').strip()
        if not subject_name:
            return jsonify({
                'success': False,
                'message': 'Subject name cannot be empty'
            })
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO subjects (name) VALUES (?)', (subject_name,))
            
            if cursor.rowcount > 0:
                return jsonify({
                    'success': True,
                    'message': f'Successfully added subject: {subject_name}',
                    'subject_name': subject_name
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Subject already exists'
                })
    
    except Exception as e:
        logger.error(f"Error adding subject: {e}")
        return jsonify({
            'success': False,
            'message': f'Error adding subject: {str(e)}'
        })

@admin_bp.route('/admin/get_lists', methods=['GET'])
def get_lists():
    """Get staff and subject lists."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT name FROM staff ORDER BY name')
            staffs = [row[0] for row in cursor.fetchall()]
            
            cursor.execute('SELECT name FROM subjects ORDER BY name')
            subjects = [row[0] for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'staffs': staffs,
            'subjects': subjects
        })
    except Exception as e:
        logger.error(f"Error getting lists: {e}")
        return jsonify({
            'success': False,
            'message': f'Error fetching lists: {str(e)}'
        })

@admin_bp.route('/admin/mappings/view', methods=['GET'])
def view_mappings():
    """View all staff-subject mappings."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get departments and semesters for filtering
        cursor.execute('SELECT name FROM departments ORDER BY name')
        departments = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT name FROM semesters ORDER BY name')
        semesters = [row[0] for row in cursor.fetchall()]
    
    return render_template('admin_view_mappings.html',
                         departments=departments,
                         semesters=semesters)

@admin_bp.route('/admin/mappings/list', methods=['GET'])
def list_mappings():
    """Get list of mappings filtered by department and semester."""
    department = request.args.get('department', '').strip()
    semester = request.args.get('semester', '').strip()
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            if department and semester:
                cursor.execute('''
                    SELECT id, department, semester, staff, subject 
                    FROM admin_mappings 
                    WHERE department = ? AND semester = ?
                    ORDER BY staff, subject
                ''', (department, semester))
            elif department:
                cursor.execute('''
                    SELECT id, department, semester, staff, subject 
                    FROM admin_mappings 
                    WHERE department = ?
                    ORDER BY semester, staff, subject
                ''', (department,))
            elif semester:
                cursor.execute('''
                    SELECT id, department, semester, staff, subject 
                    FROM admin_mappings 
                    WHERE semester = ?
                    ORDER BY department, staff, subject
                ''', (semester,))
            else:
                cursor.execute('''
                    SELECT id, department, semester, staff, subject 
                    FROM admin_mappings 
                    ORDER BY department, semester, staff, subject
                    LIMIT 500
                ''')
            
            mappings = []
            for row in cursor.fetchall():
                mappings.append({
                    'id': row[0],
                    'department': row[1],
                    'semester': row[2],
                    'staff': row[3],
                    'subject': row[4]
                })
        
        return jsonify({
            'success': True,
            'mappings': mappings,
            'count': len(mappings)
        })
    except Exception as e:
        logger.error(f"Error listing mappings: {e}")
        return jsonify({
            'success': False,
            'message': f'Error fetching mappings: {str(e)}'
        })

@admin_bp.route('/admin/mappings/delete', methods=['POST'])
def delete_mapping():
    """Delete a specific mapping."""
    try:
        mapping_id = request.form.get('mapping_id', '').strip()
        
        if not mapping_id:
            return jsonify({
                'success': False,
                'message': 'Mapping ID is required'
            })
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM admin_mappings WHERE id = ?', (mapping_id,))
            
            if cursor.rowcount > 0:
                return jsonify({
                    'success': True,
                    'message': 'Mapping deleted successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Mapping not found'
                })
    
    except Exception as e:
        logger.error(f"Error deleting mapping: {e}")
        return jsonify({
            'success': False,
            'message': f'Error deleting mapping: {str(e)}'
        })

@admin_bp.route('/admin/mappings/delete-all', methods=['POST'])
def delete_all_mappings():
    """Delete all mappings for a department and semester."""
    try:
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', '').strip()
        
        if not department or not semester:
            return jsonify({
                'success': False,
                'message': 'Department and semester are required'
            })
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM admin_mappings 
                WHERE department = ? AND semester = ?
            ''', (department, semester))
            
            deleted_count = cursor.rowcount
            
            return jsonify({
                'success': True,
                'message': f'Deleted {deleted_count} mappings successfully',
                'count': deleted_count
            })
    
    except Exception as e:
        logger.error(f"Error deleting mappings: {e}")
        return jsonify({
            'success': False,
            'message': f'Error deleting mappings: {str(e)}'
        })

@admin_bp.route('/admin/mappings/upload', methods=['POST'])
def upload_mapping_excel():
    """Upload staff-subject mappings via Excel file."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No file uploaded'
            })
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            })
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': 'Invalid file type. Please upload an Excel file (.xlsx or .xls)'
            })
        
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'message': f'File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB'
            })
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        replace_existing = request.form.get('replace_existing', 'false').lower() == 'true'
        
        success, message, stats = process_mapping_excel(filepath, replace_existing)
        
        try:
            os.remove(filepath)
        except:
            pass
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'stats': stats
            })
        else:
            return jsonify({
                'success': False,
                'message': message,
                'stats': stats
            })
    
    except Exception as e:
        logger.error(f"Error uploading mapping Excel: {e}")
        return jsonify({
            'success': False,
            'message': f'Error processing file: {str(e)}'
        })

@admin_bp.route('/admin/mappings/download-sample')
def download_mapping_sample():
    """Download a sample Excel file for mappings."""
    try:
        sample_path = os.path.join(UPLOAD_FOLDER, 'sample_mapping.xlsx')
        create_sample_mapping_excel(sample_path)
        return send_file(sample_path, as_attachment=True, download_name='sample_staff_mapping.xlsx')
    except Exception as e:
        logger.error(f"Error creating sample mapping file: {e}")
        flash('Error creating sample file', 'danger')
        return redirect(url_for('admin.admin'))

@admin_bp.route('/admin/bulk-add', methods=['GET', 'POST'])
def bulk_add():
    """Page for bulk adding staff and subjects."""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_staff':
            staff_text = request.form.get('staff_text', '').strip()
            staff_list = [s.strip() for s in staff_text.split('\n') if s.strip()]
            
            if not staff_list:
                flash('Please enter at least one staff name', 'danger')
            else:
                added, duplicates = bulk_add_staff(staff_list)
                if added > 0:
                    message = f'Successfully added {added} staff members.'
                    if duplicates > 0:
                        message += f' {duplicates} duplicates were skipped.'
                    flash(message, 'success')
                else:
                    flash(f'No new staff added. All {duplicates} were duplicates.', 'warning')
        
        elif action == 'add_subjects':
            subjects_text = request.form.get('subjects_text', '').strip()
            subjects_list = [s.strip() for s in subjects_text.split('\n') if s.strip()]
            
            if not subjects_list:
                flash('Please enter at least one subject name', 'danger')
            else:
                added, duplicates = bulk_add_subjects(subjects_list)
                if added > 0:
                    message = f'Successfully added {added} subjects.'
                    if duplicates > 0:
                        message += f' {duplicates} duplicates were skipped.'
                    flash(message, 'success')
                else:
                    flash(f'No new subjects added. All {duplicates} were duplicates.', 'warning')
        
        return redirect(url_for('admin.bulk_add'))
    
    return render_template('admin_bulk_add.html')
