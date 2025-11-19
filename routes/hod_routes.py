from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, make_response, current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from utils import read_csv_as_list, update_mainratings, normalize_semester
from config import (DEPARTMENTS_FILE, SEMESTERS_FILE, MAINRATING_FILE,
                   RATING_FILE, STUDENT_FILE, REQUIRED_FILES, ADMIN_MAPPING_FILE)
from app.models.database import get_db
import subprocess
from report_non_submission import generate_non_submission_report
import os
import csv
import io
import base64
import matplotlib.pyplot as plt
from datetime import datetime
import textwrap
from report_generator import generate_feedback_report
import shutil

hod_bp = Blueprint('hod', __name__)

def create_empty_csv(file_path, headers):
    """Create a new CSV file with only headers."""
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

def safe_move_file(src, dst):
    """Move file if it exists, create empty one if it doesn't."""
    if os.path.exists(src):
        shutil.copy2(src, dst)  # Copy with metadata

@hod_bp.route('/hod', methods=['GET', 'POST'])
def hod_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin':
            return redirect(url_for('hod.hod_select'))
        else:
            flash("Incorrect credentials.", "danger")
            return redirect(url_for('hod.hod_login'))
    return render_template('hod_login.html')

@hod_bp.route('/hod/select', methods=['GET', 'POST'])
def hod_select():
    departments = read_csv_as_list(DEPARTMENTS_FILE)
    semesters = read_csv_as_list(SEMESTERS_FILE)
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        department = request.form.get('department')
        semester = request.form.get('semester')
        
        if not department or not semester:
            flash("Please select both department and semester.", "danger")
            return redirect(url_for('hod.hod_select'))
        
        if action in ['view_pdf', 'download_pdf']:
            try:
                normalized_input_semester = normalize_semester(semester)
                update_mainratings()
                
                feedback_data = {}
                staff_counter = 1
                
                # Query ratings from database and calculate averages
                # Try multiple semester formats since data might be inconsistent
                sem_variations = [
                    normalized_input_semester,
                    f"Semester {normalized_input_semester}",
                    semester.strip()
                ]
                
                with get_db() as conn:
                    cursor = conn.cursor()
                    placeholders = ', '.join(['?'] * len(sem_variations))
                    cursor.execute(f'''
                        SELECT staff, subject,
                               AVG(q1) as q1_avg, AVG(q2) as q2_avg, AVG(q3) as q3_avg,
                               AVG(q4) as q4_avg, AVG(q5) as q5_avg, AVG(q6) as q6_avg,
                               AVG(q7) as q7_avg, AVG(q8) as q8_avg, AVG(q9) as q9_avg,
                               AVG(q10) as q10_avg
                        FROM ratings
                        WHERE department = ? AND semester IN ({placeholders})
                        GROUP BY staff, subject
                    ''', (department.strip(), *sem_variations))
                    
                    for row in cursor.fetchall():
                        staff_name = row[0].strip()
                        subject_name = row[1].strip()
                        scores = [row[i] for i in range(2, 12)]  # q1_avg to q10_avg
                        
                        key = f"{staff_name}_{subject_name}"
                        feedback_data[key] = {
                            'reference': f'S{staff_counter}',
                            'staff_name': staff_name,
                            'subject': subject_name,
                            'scores': scores
                        }
                        staff_counter += 1
                
                if not feedback_data:
                    flash("No rating data found for the selected department and semester.", "danger")
                    return redirect(url_for('hod.hod_select'))
                
                # Generate PDF report
                year = (int(normalized_input_semester) + 1) // 2
                try:
                    pdf_path = generate_feedback_report(
                        academic_year=str(datetime.now().year),
                        branch=department,
                        semester=semester,
                        year=str(year),
                        feedback_data=feedback_data
                    )
                    
                    if not pdf_path or not os.path.exists(pdf_path):
                        raise ValueError("PDF file was not generated properly")
                    
                    # Read the generated PDF
                    with open(pdf_path, 'rb') as f:
                        pdf_content = f.read()
                    
                    # Create response
                    response = make_response(pdf_content)
                    response.headers['Content-Type'] = 'application/pdf'
                    
                    if action == 'download_pdf':
                        response.headers['Content-Disposition'] = f'attachment; filename={os.path.basename(pdf_path)}'
                    else:  # view_pdf
                        response.headers['Content-Disposition'] = f'inline; filename={os.path.basename(pdf_path)}'
                    
                    # Clean up the temporary PDF file
                    try:
                        os.remove(pdf_path)
                    except:
                        pass
                    
                    return response
                
                except Exception as e:
                    current_app.logger.error(f"PDF Generation Error: {str(e)}")
                    flash(f"Error generating PDF report: {str(e)}", "danger")
                    return redirect(url_for('hod.hod_select'))
                
            except Exception as e:
                current_app.logger.error(f"General Error: {str(e)}")
                flash(f"Error processing request: {str(e)}", "danger")
                return redirect(url_for('hod.hod_select'))
        
        elif action == 'non_submission_report':
            try:
                # Generate the non-submission report directly from database
                pdf_path = generate_non_submission_report(department, semester)
                
                if not pdf_path or not os.path.exists(pdf_path):
                    raise ValueError("PDF file was not generated properly")
                
                # Read the generated PDF
                with open(pdf_path, 'rb') as f:
                    pdf_content = f.read()
                
                # Create response
                response = make_response(pdf_content)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'inline; filename={os.path.basename(pdf_path)}'
                
                # Clean up the temporary PDF file
                try:
                    os.remove(pdf_path)
                except:
                    pass
                
                return response
                
            except Exception as e:
                current_app.logger.error(f"Report generation error: {str(e)}")
                flash(f"Error generating report: {str(e)}", "danger")
                return redirect(url_for('hod.hod_select'))
                
        elif action == 'archive':
            try:
                # Create history directory
                if not os.path.exists('history'):
                    os.makedirs('history')
                
                timestamp = datetime.now().strftime("%d-%b-%Y--%H-%M-%S")
                archive_dir = os.path.join('history', timestamp)
                if not os.path.exists(archive_dir):
                    os.makedirs(archive_dir)
                
                # Backup database file
                db_path = os.path.join('data', 'feedback.db')
                if os.path.exists(db_path):
                    archive_db_path = os.path.join(archive_dir, 'feedback_backup.db')
                    shutil.copy2(db_path, archive_db_path)
                    current_app.logger.info(f"Database backed up to: {archive_db_path}")
                
                # Clear specific tables (keep: staff, subjects, semesters, departments)
                with get_db() as conn:
                    cursor = conn.cursor()
                    
                    # Clear ratings table
                    cursor.execute('DELETE FROM ratings')
                    ratings_deleted = cursor.rowcount
                    current_app.logger.info(f"Deleted {ratings_deleted} rows from ratings table")
                    
                    # Clear submitted_feedback table
                    cursor.execute('DELETE FROM submitted_feedback')
                    submitted_deleted = cursor.rowcount
                    current_app.logger.info(f"Deleted {submitted_deleted} rows from submitted_feedback table")
                    
                    # Clear admin_mappings table
                    cursor.execute('DELETE FROM admin_mappings')
                    mappings_deleted = cursor.rowcount
                    current_app.logger.info(f"Deleted {mappings_deleted} rows from admin_mappings table")
                    
                    # Clear students table
                    cursor.execute('DELETE FROM students')
                    students_deleted = cursor.rowcount
                    current_app.logger.info(f"Deleted {students_deleted} rows from students table")
                    
                    conn.commit()
                
                # Delete unnecessary files
                files_to_delete = [
                    'feedback_report.log',
                    'submitted.csv',
                    'students.csv'
                ]
                for file in files_to_delete:
                    if os.path.exists(file):
                        try:
                            os.remove(file)
                            current_app.logger.info(f"Deleted file: {file}")
                        except Exception as e:
                            current_app.logger.warning(f"Could not delete {file}: {e}")
                
                # Delete generated PDF reports
                for file in os.listdir('.'):
                    if file.startswith('feedback_report_') and file.endswith('.pdf'):
                        try:
                            os.remove(file)
                            current_app.logger.info(f"Deleted report: {file}")
                        except Exception as e:
                            current_app.logger.warning(f"Could not delete {file}: {e}")
                    elif file.startswith('non_submission_report_') and file.endswith('.pdf'):
                        try:
                            os.remove(file)
                            current_app.logger.info(f"Deleted report: {file}")
                        except Exception as e:
                            current_app.logger.warning(f"Could not delete {file}: {e}")
                
                flash("Data successfully archived and system reset. Preserved: staff, subjects, semesters, departments.", "success")
                
            except Exception as e:
                current_app.logger.error(f"Error during archival: {str(e)}")
                flash(f"Error during archival process: {str(e)}", "danger")
            
            return redirect(url_for('hod.hod_select'))
    
    return render_template('hod_select.html', 
                         departments=departments,
                         semesters=semesters)
