# Area 311 🏫

**Area 311** is a Django-based Virtual Learning Management System (LMS) platform designed specifically for overseas Pakistani students in the United Arab Emirates (UAE) and the wider Gulf region. The platform incorporates the Punjab Textbook Board curricula for Grades 6 through 12, offering dedicated portals for administrators, teachers, parents, and students.

---

## 🚀 Key Features & Apps

*   **Accounts App (`/accounts`)**: Handles multi-role authentication (Admin, Teacher, Student, Parent), landing pages, user messaging, and role-based permissions.
*   **Courses App (`/courses`)**: Manages course creation, study resources, live classes, fee records, assignments, and includes a demo data seeder.
*   **Students App (`/students`)**: Dedicated portal for students to view enrolled courses, track progress, and update student profiles.
*   **Teachers App (`/teachers`)**: Instructor dashboard for class management and student oversight.

---

## 🛠️ Prerequisites & Setup

### Requirements
*   **Python**: 3.11 or higher
*   **Pip**: Latest version
*   **Virtual Environment**: `venv` recommended

---

## ⚙️ Installation & Running Locally

Follow these steps to run the **Area 311** server locally in VS Code:

### 1. Clone or Open Project
Open the project directory in VS Code:
```bash
cd area311
```

### 2. Create & Activate Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows (CMD / PowerShell):
venv\Scripts\activate

# Activate on Git Bash / macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 4. Configure `.env` File
Create a `.env` file in the project root (`area311/`) alongside `manage.py`:
```env
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

For local development, Django generates a temporary secret key when `DEBUG=True` and `SECRET_KEY` is not set. To generate a persistent key, run:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Set the generated value as `SECRET_KEY` in `.env`. Never use a committed or publicly shared key.

> ⚠️ **Security Warning:** Ensure `.env` is listed in your `.gitignore` file so that sensitive keys and passwords are never pushed to public version control.

### Production configuration
Set a unique, private `SECRET_KEY`, `DEBUG=False`, and `ALLOWED_HOSTS` to the exact public hostname(s), comma-separated, in the production environment. For example:
```env
DEBUG=False
SECRET_KEY=your-generated-private-key
ALLOWED_HOSTS=aimansolutionslms.pythonanywhere.com
```
The application will refuse to start in production if `SECRET_KEY` or `ALLOWED_HOSTS` is missing. Do not use the example key above; replace it with a securely generated value.

### Deploying on PythonAnywhere
1. In the PythonAnywhere **Web** tab, use a Python 3.11 virtualenv and configure its WSGI file to load this project's `main.wsgi` module (`DJANGO_SETTINGS_MODULE` should be `main.settings`).
2. In a Bash console, activate that virtualenv, go to the directory containing `manage.py`, and run:
   ```bash
   python -m pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```
3. In the Web tab's **Static files** section, map `/static/` to the project's `staticfiles` directory (the same directory as `manage.py`).
4. Configure the web app environment with `DEBUG=False`, a newly generated private `SECRET_KEY`, and `ALLOWED_HOSTS=aimansolutionslms.pythonanywhere.com`. Reload the web app after changing settings or deploying code.
5. Confirm the site loads over HTTPS. Production settings redirect HTTP to HTTPS and mark session/CSRF cookies secure. Keep HSTS disabled until HTTPS has been confirmed reliably.

---

## 💾 Database Setup & Demo Data

### 1. Run Migrations
Apply existing migrations across all modular apps (`accounts`, `courses`, `students`, `teachers`):
```bash
python manage.py migrate
```

### 2. Seed Demo Data
Populate the database with initial course data using the custom management command:
```bash
python manage.py seed_demo_data
```

### 3. Create Superuser (Admin)
To access Django Admin and the main dashboard:
```bash
python manage.py createsuperuser
```

---

## 🖥️ Running the Local Server

Start the local Django development server:
```bash
python manage.py runserver
```

Open your browser and navigate to:
*   **Home / Landing Page:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
*   **Admin Portal:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 📁 Project Architecture

```text
area311/
│
├── accounts/            # User authentication, roles, landing, & messaging
├── main/                # Django project configuration (settings, urls, wsgi, asgi)
├── courses/             # Course management, study resources, live classes, seed commands
│   └── management/
│       └── commands/    # Custom commands (e.g., seed_demo_data.py)
├── students/            # Student portal, enrollment view, & dashboard
├── teachers/            # Teacher dashboard & classroom management
├── .env                 # Local environment variables (do not commit)
├── .gitignore           # Ignored files list for Git tracking
├── db.sqlite3           # Local SQLite database
└── manage.py            # Django management entry point
```

---

## 🧪 Running Tests

To execute test suites across all modular apps:
```bash
python manage.py test accounts courses students teachers
```

---

## 📄 License
This project is proprietary and developed for educational purposes.