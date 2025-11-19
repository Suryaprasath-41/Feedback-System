import csv
import os
import logging
import sqlite3
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Frame, PageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from datetime import datetime
from app.models.database import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('feedback_report.log'),
        logging.StreamHandler()
    ]
)

def normalize_department_name(department):
    """Normalize department name for consistent matching"""
    if not department:
        return ''
    # Convert to string and normalize
    dept = str(department).strip()
    # Remove extra spaces
    while '  ' in dept:
        dept = dept.replace('  ', ' ')
    # Remove "Semester" prefix if present
    dept = dept.replace('Semester ', '')
    return dept

def normalize_semester(semester):
    """Normalize semester value"""
    if not semester:
        return ''
    # Remove any non-digit characters
    sem = ''.join(filter(str.isdigit, str(semester)))
    return sem

def generate_non_submission_report(department, semester):
    """
    Generate a PDF report of students who have not submitted feedback.
    
    Args:
        department (str): The department to filter by (e.g., "Computer Science and Engineering -A")
        semester (str): The semester to filter by (e.g., "2", "4", "6")
    """
    # Normalize inputs
    department = normalize_department_name(department)
    semester = normalize_semester(semester)
    
    logging.info(f"Processing feedback submissions for '{department}' - Semester '{semester}'")
    
    # Get submitted register numbers from database
    submitted_regnos = set()
    logging.info("Reading submitted feedback from database...")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Get all submitted registration numbers
            cursor.execute('SELECT registerno FROM submitted_feedback')
            for row in cursor.fetchall():
                submitted_regnos.add(row[0].strip())
            
            logging.info(f"Found {len(submitted_regnos)} total submissions in database")
    
    except Exception as e:
        logging.error(f"Error reading submitted feedback: {e}")
        return None
    
    # Get all students from the specified department and semester
    logging.info("Reading students from database...")
    all_students = []
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT registerno, department, semester 
                FROM students 
                WHERE department = ? AND semester = ?
            ''', (department.strip(), semester))
            
            student_count = 0
            for row in cursor.fetchall():
                current_regno = row[0].strip()
                student_info = {
                    'registerno': current_regno,
                    'department': row[1],
                    'semester': row[2]
                }
                all_students.append(student_info)
                student_count += 1
                logging.debug(f"Found student: {current_regno}")
            
            logging.info(f"Found {student_count} students in {department} semester {semester}")
    
    except Exception as e:
        logging.error(f"Error reading students: {e}")
        return None
    
    logging.info("Checking for non-submissions...")
    
    # Find students who haven't submitted
    non_submitted = []
    for student in all_students:
        regno = student['registerno']
        if regno not in submitted_regnos:
            non_submitted.append(student)
            logging.debug(f"Non-submission found: {regno}")
        else:
            logging.debug(f"Submission verified for: {regno}")
    
    logging.info(f"Total students: {len(all_students)}")
    logging.info(f"Total submissions: {len(submitted_regnos)}")
    logging.info(f"Non-submissions: {len(non_submitted)}")
    
    # Generate PDF report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"non_submission_report_{department.replace(' ', '_')}_{semester}_{timestamp}.pdf"
    pdf_path = os.path.join(os.getcwd(), filename)
    
    def add_watermark(canvas, doc):
        canvas.saveState()
        # Create italic style for watermark
        watermark_style = ParagraphStyle(
            'WatermarkStyle',
            parent=styles['Italic'],
            textColor=colors.grey,
            fontSize=8,
            alignment=1  # Center alignment
        )
        watermark_text = Paragraph(
            "THIS REPORT AND SITE IS CREATED AND MANAGED BY GENRECAI",
            watermark_style
        )
        # Draw watermark at bottom of page
        w, h = watermark_text.wrap(doc.width, doc.bottomMargin)
        watermark_text.drawOn(canvas, doc.leftMargin, doc.bottomMargin/3)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    # Create content
    styles = getSampleStyleSheet()
    
    # Set up the template with watermark
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id='normal'
    )
    template = PageTemplate(
        id='watermarked',
        frames=frame,
        onPage=add_watermark
    )
    doc.addPageTemplates([template])
    content = []
    
    # Title
    title_style = styles['Heading1']
    title_style.alignment = 1
    content.append(Paragraph("VSB ENGINEERING COLLEGE", title_style))
    content.append(Spacer(1, 12))
    
    # Subtitle
    subtitle_style = styles['Heading2']
    subtitle_style.alignment = 1
    content.append(Paragraph("Students Who Have Not Submitted Feedback", subtitle_style))
    content.append(Spacer(1, 12))
    
    # Department and Semester
    dept_sem_style = styles['Heading3']
    dept_sem_style.alignment = 1
    content.append(Paragraph(f"Department: {department} | Semester: {semester}", dept_sem_style))
    content.append(Spacer(1, 12))
    
    # Date
    date_style = styles['Normal']
    date_style.alignment = 1
    content.append(Paragraph(f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", date_style))
    content.append(Spacer(1, 24))
    
    # Statistics
    total = len(all_students)
    not_submitted = len(non_submitted)
    submitted = total - not_submitted
    stats = Paragraph(
        f"Total Students: {total} | Submitted: {submitted} | Not Submitted: {not_submitted}",
        styles['Normal']
    )
    stats.alignment = 1
    content.append(stats)
    content.append(Spacer(1, 24))
    
    if non_submitted:
        # Create table
        table_data = [['#', 'Register No.', 'Department', 'Semester']]
        for i, student in enumerate(non_submitted, 1):
            table_data.append([
                i,
                student['registerno'],
                student['department'],
                student['semester']
            ])
        
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        content.append(table)
    else:
        msg = Paragraph("All students have submitted their feedback!", styles['Heading3'])
        msg.alignment = 1
        content.append(msg)
    
    # Generate PDF
    doc.build(content)
    logging.info(f"Report generated: {filename}")
    return pdf_path
