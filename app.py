import os
import logging
from rich.logging import RichHandler
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import matplotlib
matplotlib.use("Agg")

# Initialize database before importing routes
from app.models import init_db, get_db
from app.models.student import Student
from routes.hod_routes import hod_bp
from routes.admin_routes import admin_bp

from utils import (
    encrypt_regno,
    is_encrypted,
    normalize_regno,
)
from config import (
    FEEDBACK_QUESTIONS,
    UPLOAD_FOLDER,
)
from asgiref.wsgi import WsgiToAsgi

# Configure rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logging.root.handlers = [
    RichHandler(rich_tracebacks=True, show_path=True, tracebacks_show_locals=False,
                log_time_format="[%b %d, %Y, %I:%M:%S %p]",
                )
]
logger = logging.getLogger("feedback_system")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_change_in_production')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload size

# Register blueprints
app.register_blueprint(hod_bp)
app.register_blueprint(admin_bp)

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

asgi_app = WsgiToAsgi(app)


def get_student_info_db(registerno):
    """Get student info from database by registration number."""
    reg_num = normalize_regno(registerno)
    student = Student.get_by_regno(reg_num)
    return student


def has_submitted_feedback_db(registerno):
    """Check if student has submitted feedback."""
    reg_num = normalize_regno(registerno)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM submitted_feedback 
            WHERE registerno = ?
        ''', (reg_num,))
        
        return cursor.fetchone() is not None


def load_admin_mapping_db(department, semester):
    """Load admin mappings from database."""
    # Normalize semester to match database format (handle inconsistencies)
    sem_variations = [
        semester,
        f"Semester {semester}",
        f"Semester Semester {semester}",
        semester.replace("Semester", "").strip()
    ]
    
    with get_db() as conn:
        cursor = conn.cursor()
        # Try multiple semester formats
        placeholders = ', '.join(['?'] * len(sem_variations))
        cursor.execute(f'''
            SELECT DISTINCT department, semester, staff, subject 
            FROM admin_mappings 
            WHERE department = ? AND semester IN ({placeholders})
        ''', (department, *sem_variations))
        
        mappings = []
        for row in cursor.fetchall():
            mappings.append({
                'department': row[0],
                'semester': row[1],
                'staff': row[2],
                'subject': row[3]
            })
        
        return mappings


def append_ratings_db(rating_rows):
    """Append ratings to database."""
    with get_db() as conn:
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


@app.route("/add_staff", methods=["POST"])
def add_staff():
    staff_name = request.form.get("staff_name", "").strip()
    if staff_name:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM staff WHERE name = ?', (staff_name,))
            
            if cursor.fetchone():
                flash("Staff already exists", "danger")
            else:
                cursor.execute('INSERT INTO staff (name) VALUES (?)', (staff_name,))
                flash("Staff added successfully!", "success")
                return {"success": True, "message": "Staff added successfully!"}
    return {"success": False, "message": "Staff name is required"}


@app.route("/add_subject", methods=["POST"])
def add_subject():
    subject_name = request.form.get("subject_name", "").strip()
    if subject_name:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM subjects WHERE name = ?', (subject_name,))
            
            if cursor.fetchone():
                flash("Subject already exists", "danger")
            else:
                cursor.execute('INSERT INTO subjects (name) VALUES (?)', (subject_name,))
                flash("Subject added successfully!", "success")
                return {"success": True, "message": "Subject added successfully!"}
    return {"success": False, "message": "Subject name is required"}


@app.route("/validate_regno", methods=["POST"])
def validate_regno():
    registerno = request.form.get("registerno", "").strip()
    if not registerno:
        return jsonify({
            "valid": False,
            "message": "Please enter a registration number"
        })

    try:
        registerno = ''.join(filter(str.isdigit, registerno))
        
        if not registerno:
            return jsonify({
                "valid": False,
                "message": "Registration number must contain at least one digit"
            })

        reg_num = int(registerno)
        if reg_num < 1:
            return jsonify({
                "valid": False,
                "message": "Registration number must be a positive number"
            })

        student_info = get_student_info_db(registerno)
        if not student_info:
            return jsonify({
                "valid": False,
                "message": "Registration number not found"
            })

        if has_submitted_feedback_db(registerno):
            return jsonify({
                "valid": False,
                "message": "Feedback already submitted for this registration number"
            })

        # Check registration number range
        department = student_info.get("department")
        semester = student_info.get("semester")
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT registerno FROM students 
                WHERE department = ? AND semester = ?
            ''', (department, semester))
            
            reg_nums = [int(row[0]) for row in cursor.fetchall()]

        if reg_nums:
            min_reg = min(reg_nums)
            max_reg = max(reg_nums)
            if (max_reg - min_reg) > 600:
                return jsonify({
                    "valid": False,
                    "message": "Registration number range exceeds limit for your batch"
                })

        return jsonify({
            "valid": True,
            "message": "Registration number validated successfully!"
        })

    except ValueError:
        return jsonify({
            "valid": False,
            "message": "Invalid registration number format"
        })


@app.route("/", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        registerno = request.form.get("registerno", "")
        if not registerno:
            flash("Please enter your registration number.", "danger")
            return render_template("student_login.html")
        
        registerno = ''.join(filter(str.isdigit, registerno))
        
        if not registerno:
            flash("Registration number must contain at least one digit.", "danger")
            return render_template("student_login.html")
        
        try:
            reg_num = int(registerno)
            if reg_num < 1:
                flash("Registration number must be a positive number.", "danger")
                return render_template("student_login.html")
            
            student_info = get_student_info_db(registerno)
            if not student_info:
                flash("Registration number not found. Please try again.", "danger")
                return render_template("student_login.html")
            
            department = student_info.get("department")
            semester = student_info.get("semester")
            
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT registerno FROM students 
                    WHERE department = ? AND semester = ?
                ''', (department, semester))
                
                reg_nums = [int(row[0]) for row in cursor.fetchall()]
            
            if reg_nums:
                min_reg = min(reg_nums)
                max_reg = max(reg_nums)
                if (max_reg - min_reg) > 600:
                    flash("Registration number range exceeds limit for your batch.", "danger")
                    return render_template("student_login.html")
            
            if has_submitted_feedback_db(registerno):
                flash("Feedback already submitted for this registration number.", "info")
                return render_template("student_login.html")
            
            flash("Registration number validated successfully!", "success")
            return redirect(
                url_for(
                    "feedback",
                    department=department,
                    semester=semester,
                    registerno=registerno,
                )
            )
            
        except ValueError:
            flash("Invalid registration number format.", "danger")
            return render_template("student_login.html")
    
    return render_template("student_login.html")


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == "vsbec":
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Incorrect password.", "danger")
            return redirect(url_for("admin_login"))
    return render_template("admin_login.html")


@app.route("/admin_dashboard")
def admin_dashboard():
    return render_template("admin_dashboard.html")


@app.route("/admin_students")
def admin_students():
    """Student management page - FIXED to use actual student data"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get departments from students table (actual data)
        cursor.execute('SELECT DISTINCT department FROM students ORDER BY department')
        departments = [row[0] for row in cursor.fetchall()]
        
        # Get semesters from students table (actual data) - stored as numbers
        cursor.execute('SELECT DISTINCT semester FROM students ORDER BY CAST(semester AS INTEGER)')
        semesters = [row[0] for row in cursor.fetchall()]
    
    return render_template(
        "admin_students.html", departments=departments, semesters=semesters
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
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

    if request.method == "POST":
        department = request.form.get("department")
        semester = request.form.get("semester")
        staff_list = request.form.getlist("staff")
        subject_list = request.form.getlist("subject")
        
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
                
                # Delete existing mappings
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
            return redirect(url_for("admin"))

    return render_template(
        "admin_mapping.html",
        departments=departments,
        semesters=semesters,
        staffs=staffs,
        subjects=subjects,
    )


@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    department = request.args.get("department")
    semester = request.args.get("semester")
    registerno = request.args.get("registerno")

    if not department or not semester or not registerno:
        flash("Missing department, semester, or registration number.", "danger")
        return redirect(url_for("student_login"))

    if has_submitted_feedback_db(registerno):
        flash("Feedback already submitted. You have already registered.", "info")
        return redirect(url_for("student_login"))

    mappings = load_admin_mapping_db(department, semester)
    if not mappings:
        return (
            f"<h2>No staff/subject mappings found for {department} - {semester}.</h2>"
        )

    if request.method == "POST":
        if has_submitted_feedback_db(registerno):
            flash("Feedback already submitted. You have already registered.", "info")
            return redirect(url_for("student_login"))

        rating_rows = []
        error_flag = False

        for idx, mapping in enumerate(mappings):
            ratings_dict = {}
            ratings = []
            for q in range(1, 11):
                key = f"rating-{idx}-{q}"
                value = request.form.get(key)
                if not value:
                    flash(
                        f"Please fill all rating boxes for {mapping['staff']}.",
                        "danger",
                    )
                    error_flag = True
                    break
                try:
                    score = float(value)
                except ValueError:
                    flash(f"Invalid rating value for {mapping['staff']}.", "danger")
                    error_flag = True
                    break
                ratings.append(score)
                ratings_dict[f"q{q}"] = f"{score:.2f}"

            if error_flag:
                break

            average = sum(ratings) / len(ratings)
            row_data = {
                "registerno": registerno,  # Store registerno without encryption
                "department": department,
                "semester": semester,
                "staff": mapping["staff"],
                "subject": mapping["subject"],
                "average": f"{average:.2f}",
            }
            row_data.update(ratings_dict)
            rating_rows.append(row_data)

        if error_flag:
            return redirect(
                url_for(
                    "feedback",
                    department=department,
                    semester=semester,
                    registerno=registerno,
                )
            )
        else:
            append_ratings_db(rating_rows)
            flash("Feedback submitted successfully. Thank you!", "success")
            return redirect(url_for("student_login"))

    return render_template(
        "feedback.html",
        department=department,
        semester=semester,
        mappings=mappings,
        questions=FEEDBACK_QUESTIONS,
    )


if __name__ == "__main__":
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")
    
    # Check if data migration is needed
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--migrate':
        logger.info("Running data migration...")
        from migrate_to_sqlite import main as migrate_main
        migrate_main()
    
    import uvicorn
    import socket
    host_ip = socket.gethostbyname(socket.gethostname())
    logger.info(f"Starting server on {host_ip}:80")
    uvicorn.run(asgi_app, host=host_ip, port=80, log_config=None)
