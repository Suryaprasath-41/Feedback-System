# Database configuration
DATABASE_PATH = 'data/feedback.db'

# File paths (kept for backward compatibility during migration)
DEPARTMENTS_FILE = 'departments.csv'
SEMESTERS_FILE = 'semesters.csv'
STAFFS_FILE = 'staffs.csv'
SUBJECTS_FILE = 'subjects.csv'
ADMIN_MAPPING_FILE = 'admin_mapping.csv'
RATING_FILE = 'ratings.csv'
STUDENT_FILE = 'students.csv'  # Contains: registerno,department,semester
MAINRATING_FILE = 'mainrating.csv'  # New aggregated ratings file

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Required CSV files and their headers
REQUIRED_FILES = {
    DEPARTMENTS_FILE: ['Department'],
    SEMESTERS_FILE: ['Semester'],
    STAFFS_FILE: ['Staff'],  # Changed from 'staff_name' to match actual header
    SUBJECTS_FILE: ['Subject'],
    ADMIN_MAPPING_FILE: ['department', 'semester', 'staff', 'subject'],
    RATING_FILE: ['registerno', 'department', 'semester', 'staff', 'subject', 'q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10', 'average'],
    STUDENT_FILE: ['registerno', 'department', 'semester']
}

# Feedback questions
FEEDBACK_QUESTIONS = [
    "How is the faculty's approach?",
    "How has the faculty prepared for the classes?",
    "Does the faculty inform you about your expected competencies, course outcomes?",
    "How often does the faculty illustrate the concepts through examples and practical applications?",
    "Whether faculty covers syllabus in time?",
    "Do you agree that the faculty teaches content beyond syllabus?",
    "How does the faculty communicate?",
    "Whether faculty returns answer scripts in time and produces helpful comments?",
    "How does the faculty identify your strengths and encourage you with high level of challenges?",
    "How does the faculty counsel & encourage the students?"
]