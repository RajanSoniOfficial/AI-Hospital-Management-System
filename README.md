# AI Hospital Management System

A BCA-ready Hospital Management System starter with:
- Admin login
- Dashboard analytics cards
- Patient registration
- Doctor directory
- Appointment management
- Billing
- AI Center with safe patient-record summarization
- SQLite database for easy local setup

## Demo login
Email: admin@hospital.local
Password: admin123

## Run on Windows

1. Install Python 3.11+.
2. Open this folder in VS Code.
3. Open Terminal.
4. Create a virtual environment:
   python -m venv venv
5. Activate:
   venv\Scripts\activate
6. Install:
   pip install -r requirements.txt
7. Run:
   python app.py
8. Open:
   http://127.0.0.1:5000

The database file `hospital.db` is created automatically.

## Production
Before public deployment:
- change `app.secret_key`
- use PostgreSQL
- store secrets in environment variables
- add proper password/user management
- add CSRF protection
- enable HTTPS
- never use real patient medical data for a college demo
