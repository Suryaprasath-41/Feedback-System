# VSB Engineering College Faculty Feedback System

A comprehensive web-based faculty feedback management system designed for VSB Engineering College. This system allows students to provide feedback on faculty performance, while administrators and HODs can manage mappings, view reports, and analyze feedback data.

## 🎯 Features

### Student Features
- **Secure Login**: Authentication using college registration number
- **Feedback Submission**: Rate faculty across 10 standardized parameters
- **Visual Feedback**: Color-coded rating indicators (Green/Yellow/Red)
- **One-Time Submission**: Prevents duplicate feedback entries
- **User-Friendly Interface**: Clean, responsive design with intuitive navigation

### Administrator Features
- **Dashboard**: Comprehensive admin panel for system management
- **Staff-Subject Mapping**: 
  - Manual mapping entry
  - Bulk Excel upload (.xlsx/.xls)
  - Download sample templates
  - View and delete existing mappings
- **Bulk Operations**:
  - Add multiple staff members at once
  - Add multiple subjects simultaneously
  - Automatic duplicate detection
- **Student Management**: 
  - Bulk student uploads via Excel
  - View and manage student records
  - Department and semester assignment
- **Report Generation**: Generate comprehensive feedback reports
- **Data Export**: Export data in various formats

### HOD (Head of Department) Features
- **Department Reports**: View department-specific feedback analysis
- **Staff Performance**: Monitor faculty performance metrics
- **Non-Submission Reports**: Track students who haven't submitted feedback
- **Statistical Analysis**: View average ratings and trends

## 🏗️ Architecture

### Technology Stack
- **Backend**: Python Flask (ASGI with Uvicorn)
- **Database**: SQLite 3
- **Frontend**: HTML5, CSS3, JavaScript
- **Styling**: Bootstrap 4, Font Awesome
- **Excel Processing**: openpyxl, pandas
- **Encryption**: Cryptography library
- **Logging**: Rich logging with colored output

### Project Structure
```
Feedback-System/
├── app/
│   ├── models/          # Database models
│   ├── services/        # Business logic services
│   └── utils/           # Helper utilities
├── routes/
│   ├── admin_routes.py  # Admin endpoints
│   ├── hod_routes.py    # HOD endpoints
│   └── student_routes.py # Student endpoints (not integrated)
├── templates/           # HTML templates
├── static/              # CSS, JS, images
├── data/
│   └── feedback.db      # SQLite database
├── uploads/             # Uploaded Excel files
├── logs/                # Application logs
├── backup_csv/          # CSV backups (legacy)
├── app.py               # Main application file
├── config.py            # Configuration settings
├── utils.py             # Utility functions
├── report_generator.py  # Report generation logic
├── report_non_submission.py # Non-submission tracking
├── start_server.py      # Auto-start server script
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variables template

```

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git (optional, for cloning)

### Step 1: Clone or Download
```bash
git clone https://github.com/your-repo/Feedback-System.git
cd Feedback-System
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- Flask
- uvicorn
- asgiref
- matplotlib
- openpyxl
- pandas
- cryptography
- rich

### Step 3: Configure Environment
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` file with your settings:
   ```env
   FLASK_SECRET_KEY=your_secret_key_change_this
   ADMIN_PASSWORD=your_admin_password
   HOD_USERNAME=your_hod_username
   HOD_PASSWORD=your_hod_password
   ENCRYPTION_SECRET_KEY=your_encryption_key
   PORT=5000
   ```

### Step 4: Initialize Database
The database will be automatically created on first run. The system uses SQLite with the following tables:
- `students` - Student information
- `departments` - Department list
- `semesters` - Semester list
- `staffs` - Staff/faculty list
- `subjects` - Subject list
- `admin_mappings` - Staff-subject mappings
- `feedback_ratings` - Feedback data
- `submitted_feedback` - Submission tracking

## 🚀 Running the Application

### Method 1: Automatic Server Starter (Recommended)
```bash
python start_server.py
```

This will:
- Automatically detect your local IP address
- Find an available port (tries 5000, 8080, 8000, 3000, 5001)
- Open your default browser
- Display access URLs for local and network access

### Method 2: Manual Start
```bash
python app.py
```

Then access the application at:
- Local: `http://localhost:5000`
- Network: `http://YOUR_IP:5000`

### Method 3: Using Uvicorn Directly
```bash
uvicorn app:asgi_app --host 0.0.0.0 --port 5000
```

## 📱 Usage

### For Students

1. **Access the System**
   - Navigate to the homepage: `http://your-server:5000`
   - Click on "Student Feedback"

2. **Login**
   - Enter your registration number
   - System validates and loads your profile

3. **Submit Feedback**
   - View list of faculty members assigned to your department/semester
   - Rate each faculty on 10 parameters (scale: 1-10)
   - Submit feedback (one-time only)

### For Administrators

1. **Login**
   - Navigate to: `http://your-server:5000/admin_login`
   - Enter admin password (default: `vsbec`)

2. **Manage Staff-Subject Mappings**
   - **Manual Entry**: Add individual mappings
   - **Excel Upload**: 
     - Download sample template
     - Fill in: department, semester, staff, subject
     - Upload file (replace or append mode)
   - **View/Delete**: Filter and remove mappings

3. **Bulk Operations**
   - Navigate to "Bulk Add Staff/Subjects"
   - Enter multiple names (one per line)
   - System automatically handles duplicates

4. **Student Management**
   - Upload student data via Excel
   - View all registered students
   - Manage student records

5. **Generate Reports**
   - Select department and semester
   - Generate comprehensive feedback reports
   - Download or view online

### For HODs

1. **Login**
   - Navigate to: `http://your-server:5000/hod_login`
   - Enter HOD credentials

2. **View Reports**
   - Department-specific feedback analysis
   - Staff performance metrics
   - Non-submission tracking
   - Statistical summaries

## 🔧 Configuration

### Feedback Questions
Edit `config.py` to customize the 10 feedback questions:
```python
FEEDBACK_QUESTIONS = [
    "How is the faculty's approach?",
    "How has the faculty prepared for the classes?",
    # ... add your questions
]
```

### Database Configuration
Database path is set in `config.py`:
```python
DATABASE_PATH = 'data/feedback.db'
```

### Upload Settings
Configure file upload limits in `config.py`:
```python
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

## 🌐 Deployment

### Local Network Deployment

1. **Run the server**:
   ```bash
   python start_server.py
   ```

2. **Find your IP address**:
   - Windows: `ipconfig`
   - Linux/Mac: `ifconfig` or `ip addr`

3. **Share the URL** with users on the same network:
   ```
   http://YOUR_IP:5000
   ```

### Production Deployment

#### Option 1: Using a Production WSGI Server

1. **Install Gunicorn** (Linux/Mac):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:asgi_app --bind 0.0.0.0:5000
   ```

2. **Or use Waitress** (Windows-compatible):
   ```bash
   pip install waitress
   waitress-serve --port=5000 app:app
   ```

#### Option 2: Using Nginx as Reverse Proxy

1. **Install Nginx**

2. **Configure Nginx** (`/etc/nginx/sites-available/feedback`):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **Enable site**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/feedback /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

#### Option 3: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python", "start_server.py"]
```

Build and run:
```bash
docker build -t feedback-system .
docker run -p 5000:5000 feedback-system
```

### Cloud Deployment

#### Heroku
1. Create `Procfile`:
   ```
   web: python start_server.py
   ```

2. Deploy:
   ```bash
   heroku create your-app-name
   git push heroku main
   ```

#### AWS/Azure/Google Cloud
- Use EC2/VM instance
- Install Python and dependencies
- Configure security groups/firewall
- Run with systemd or supervisor

## 🔒 Security Considerations

### Important Security Steps

1. **Change Default Passwords**
   ```env
   ADMIN_PASSWORD=strong_password_here
   HOD_PASSWORD=strong_password_here
   ```

2. **Use Strong Secret Keys**
   ```python
   import secrets
   print(secrets.token_hex(32))
   ```

3. **Enable HTTPS** in production
   - Use Let's Encrypt for free SSL certificates
   - Configure Nginx with SSL

4. **File Permissions**
   ```bash
   chmod 600 .env
   chmod 700 data/
   ```

5. **Database Backups**
   ```bash
   cp data/feedback.db backups/feedback_$(date +%Y%m%d).db
   ```

6. **Input Validation**
   - All user inputs are validated
   - SQL injection protection via parameterized queries
   - XSS protection in templates

7. **Rate Limiting** (recommended for production)
   ```bash
   pip install Flask-Limiter
   ```

## 📊 Database Schema

### Students Table
```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    registerno TEXT UNIQUE,
    department TEXT,
    semester TEXT
)
```

### Admin Mappings Table
```sql
CREATE TABLE admin_mappings (
    id INTEGER PRIMARY KEY,
    department TEXT,
    semester TEXT,
    staff TEXT,
    subject TEXT
)
```

### Feedback Ratings Table
```sql
CREATE TABLE feedback_ratings (
    id INTEGER PRIMARY KEY,
    registerno TEXT,
    department TEXT,
    semester TEXT,
    staff TEXT,
    subject TEXT,
    q1-q10 REAL,
    average REAL,
    timestamp DATETIME
)
```

### Submitted Feedback Table
```sql
CREATE TABLE submitted_feedback (
    id INTEGER PRIMARY KEY,
    registerno TEXT UNIQUE,
    submission_date DATETIME
)
```

## 🐛 Troubleshooting

### Common Issues

**Issue: Port already in use**
```bash
# Find process using the port
netstat -ano | findstr :5000  # Windows
lsof -i :5000                 # Linux/Mac

# Kill the process or use a different port
```

**Issue: Database locked**
- Close all connections to the database
- Check if another process is accessing the DB
- Restart the application

**Issue: Excel upload fails**
- Ensure file has required columns
- Check file size (max 10MB)
- Verify file format (.xlsx or .xls)

**Issue: Students can't login**
- Verify student exists in database
- Check registration number format
- Ensure database is accessible

**Issue: Permission denied errors**
```bash
# Fix permissions
chmod 755 .
chmod 777 uploads/
chmod 777 logs/
chmod 777 data/
```

## 📝 API Endpoints

### Student Endpoints
- `GET /` - Homepage
- `POST /` - Student login
- `GET /feedback` - Feedback form
- `POST /feedback` - Submit feedback

### Admin Endpoints
- `GET /admin_login` - Admin login page
- `POST /admin_login` - Process admin login
- `GET /admin_dashboard` - Admin dashboard
- `GET /admin` - Staff-subject mapping
- `POST /admin/mappings/upload` - Upload Excel mappings
- `GET /admin/mappings/view` - View mappings
- `POST /admin/mappings/delete` - Delete mapping
- `GET /admin/bulk-add` - Bulk add page
- `POST /admin/bulk-add` - Process bulk add
- `GET /admin_students` - Student management

### HOD Endpoints
- `GET /hod_login` - HOD login page
- `POST /hod_login` - Process HOD login
- `GET /hod_dashboard` - HOD dashboard
- `GET /hod/reports` - Feedback reports

## 📄 Excel File Formats

### Staff-Subject Mapping Template
| department | semester | staff | subject |
|------------|----------|-------|---------|
| Computer Science - A | 2 | Dr. John Doe | Data Structures |
| Computer Science - A | 2 | Prof. Jane Smith | Operating Systems |

### Student Upload Template
| registerno | department | semester |
|------------|------------|----------|
| 23CS001 | Computer Science - A | 2 |
| 23CS002 | Computer Science - A | 2 |

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Credits

**Created and Maintained by GenrecAI**
- Website: [Genrec.AI](https://revolvo-ai.netlify.app)

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: [Your support email]

## 🔄 Version History

### v2.0.0 (Latest)
- Migrated from CSV to SQLite database
- Added Excel upload functionality
- Implemented bulk operations
- Enhanced security features
- Improved UI/UX

### v1.0.0
- Initial release with CSV storage
- Basic feedback collection
- Admin and HOD portals

---

**VSB Engineering College** | Faculty Feedback System
