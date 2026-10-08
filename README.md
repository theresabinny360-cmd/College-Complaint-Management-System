# Vimal Jyothi Engineering College (VJEC)
## College Complaint Management System

A centralized, responsive, role-based grievance redressal and campus support web platform engineered for **Vimal Jyothi Engineering College (VJEC), Chemperi, Kannur**. 

Developed using **Python Flask**, **Flask-SQLAlchemy**, **SQLite**, **Jinja2**, and **Vanilla JavaScript / CSS3**.

---

## 🏛️ Project Overview

The **VJEC College Complaint Management System** streamlines institutional issue reporting, departmental routing, real-time tracking, counselling coordination, anti-ragging oversight, visitor inquiries, and administrative analytics.

### Key Institutional Disciplines (10 Departments):
1. **ECE** – Electronics and Communication Engineering
2. **CSE** – Computer Science and Engineering
3. **CSD** – Computer Science and Design
4. **CSBS** – Computer Science and Business Systems
5. **CE** – Civil Engineering
6. **ME** – Mechanical Engineering
7. **EEE** – Electrical and Electronics Engineering
8. **AEI** – Applied Electronics and Instrumentation
9. **ADS** – Artificial Intelligence and Data Science
10. **CSCY** – Computer Science and Cyber Security

---

## 🌟 Core System Features

1. **Designation Selection First Interface**:
   - Clean, professional entry screen presenting 4 large designation cards:
     - **Student Portal**
     - **Faculty Portal**
     - **Counsellor Portal**
     - **Administrator Control Panel**
   - Role verification prevents unauthorized cross-role logins.

2. **Role-Based Access Control (RBAC) & Strict Privacy**:
   - **Student**: Strict confidentiality. A student can **only view their own grievances**. Other students' complaints return `403 Forbidden` at backend database query level.
   - **Faculty**: Access complaints routed specifically to their department or assigned to their account.
   - **Counsellor**: Manage student counselling bookings, appointments, and referred welfare grievances.
   - **Administrator**: Full system visibility, routing override, status/priority modification, user management, and audit logs.

3. **Anonymous / Confidential Grievances**:
   - Students can check **"Submit Anonymously"**. Handling faculty and officers see *"Anonymous Student"* while the system maintains internal secure record-keeping.

4. **Complaint Lifecycle Tracking & Stepper**:
   - Real-time 8-stage progress tracker:
     `Submitted` &rarr; `Under Review` &rarr; `Assigned` &rarr; `In Progress` &rarr; `Action Taken` &rarr; `Awaiting Feedback` &rarr; `Resolved` &rarr; `Closed`
   - Complete audit trail showing timestamps, acting officials, and remarks.

5. **Live Updates & Conversation Channel**:
   - Threaded discussion stream for each grievance between students and authorized handling faculty/administrators with optional attachments.

6. **Student Counselling Cell**:
   - One-on-one confidential consultation booking module with preferred dates, time slots, and confidential notes. Counsellors can confirm, reschedule, or complete sessions.

7. **Anti-Ragging Incident Reporting**:
   - Strictly restricted confidential reporting module with emergency alerts directly routed to the Anti-Ragging Committee and Flying Squad.

8. **Student Feedback & Star Ratings**:
   - Upon grievance resolution, students provide 1–5 star ratings, satisfaction levels, and written remarks.

9. **Interactive Campus Navigation**:
   - Visual block navigator covering St. Thomas Main Block, Academic Block B (ECE/AEI), Block C (CSD/CSBS), Mechanical Complex, Civil Complex, EEE Complex, Central Library, Hostels, and Cafeteria.

10. **Visitor Support Desk**:
    - Publicly accessible intake form for parents, guests, and recruiters to submit queries, managed through the Administrator dashboard.

11. **Institutional Analytics & Charts**:
    - Real-time interactive charts (Department Distribution, Status Breakdown, Category Distribution) using Chart.js.

---

## 🔑 Demo Login Credentials

The application is pre-seeded with all required test accounts:

| Designation | Name | Login ID | Password | Department / Role Notes |
|:---|:---|:---|:---|:---|
| **Student 1** | Theresa Binny | `VML23EC040` | `theresa@123` | ECE &bull; 4th Year |
| **Student 2** | Aneeta Ullas | `VML23EC008` | `Aneeta@123` | ECE &bull; 4th Year |
| **Faculty 1** | Ms. Arya Thalakkat | `VML23FT001` | `Arya@123` | ECE Department Faculty |
| **Faculty 2** | Ms. Aishwarya | `VML23FT002` | `Aishwarya@123` | ECE Department Faculty |
| **Counsellor** | Dr. Mathew Joseph | `VML23CN001` | `Mathew@123` | Student Counselling Cell |
| **Administrator** | Administrator | `ADM2604` | `Admin@123` | Master System Authority |

> **Note**: A quick 1-click credential filler is provided on the login page for effortless test evaluation!

---

## 🛠️ Technology Stack

- **Backend**: Python 3, Flask 3.1, Jinja2 Templates
- **ORM & Database**: Flask-SQLAlchemy 3.1, SQLite 3
- **Security**: Werkzeug password hashing (`pbkdf2:sha256`), secure session management, RBAC decorators
- **Frontend**: Responsive HTML5, CSS3 Custom Properties (VJEC Navy `#002b49` & Gold `#f59e0b` palette), Vanilla JavaScript
- **Icons & Charts**: FontAwesome 6, Chart.js

---

## 📁 Project Structure

```text
vjec_complaint_system/
├── app.py                     # Main application factory, routes, and authentication decorators
├── config.py                  # Database URI, upload folder, and security settings
├── models.py                  # SQLAlchemy models (User, Complaint, Appointment, Feedback, etc.)
├── seed.py                    # Seeder script preloading departments, demo accounts, sample data
├── test_app.py                # Automated integration & unit test suite
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
│
├── instance/
│   └── vjec_complaints.db     # SQLite development database
│
├── uploads/                   # Secured file upload storage
│
├── static/
│   ├── css/
│   │   └── style.css          # Institutional stylesheet with responsive layouts
│   ├── js/
│   │   └── main.js            # Password toggles, notifications, ratings, navigation
│   └── images/
│       └── vjec_logo.svg      # Official VJEC vector emblem
│
└── templates/
    ├── base.html              # Institutional layout with role-based navigation sidebar
    ├── index.html             # First interface: 4-designation selection cards
    ├── login.html             # Authentication form with show/hide password toggle
    ├── register.html          # Account registration form (VML validation)
    ├── visitor_support.html   # Public visitor inquiry desk
    ├── student/
    │   ├── dashboard.html     # Student metrics, privacy banner, recent grievances
    │   ├── register_complaint.html # Filing form with anonymous toggle & file upload
    │   ├── my_complaints.html # Student's private grievances list with filters
    │   ├── complaint_detail.html # 8-stage stepper, chat stream, audit history
    │   ├── track_complaint.html # Real-time ID tracker
    │   ├── counselling.html   # Counselling booking and appointments
    │   ├── anti_ragging.html  # Confidential incident report form
    │   ├── feedback.html      # 5-star resolution rating widget
    │   ├── campus_navigation.html # Interactive campus landmark directory
    │   ├── notifications.html # Alerts list
    │   └── profile.html       # Profile details
    ├── faculty/
    │   ├── dashboard.html     # Department queue metrics
    │   ├── assigned_complaints.html # Queue with priority/status filters
    │   ├── complaint_detail.html # Status updater, action logs, resolution entry
    │   ├── feedback.html      # Student feedback on department resolutions
    │   ├── notifications.html # Department alerts
    │   └── profile.html       # Faculty profile
    ├── counsellor/
    │   ├── dashboard.html     # Session metrics
    │   ├── appointments.html  # Confirm, reschedule, and complete appointments
    │   ├── complaints.html    # Referred grievances
    │   ├── complaint_detail.html # Counsellor notes and student guidance
    │   ├── notifications.html # Alerts
    │   └── profile.html       # Counsellor profile
    ├── admin/
    │   ├── dashboard.html     # KPI metrics & Chart.js visualizations
    │   ├── users.html         # User CRUD & status management
    │   ├── user_form.html     # Add/edit accounts
    │   ├── departments.html   # 10 branches oversight & HOD details
    │   ├── department_edit.html # Modify department information
    │   ├── complaints.html    # Master queue with comprehensive filters
    │   ├── complaint_detail.html # Administrative override & reassignment
    │   ├── anti_ragging.html  # Confidential disciplinary investigation portal
    │   ├── counselling.html   # All counselling appointments
    │   ├── feedback.html      # Institutional feedback analytics
    │   ├── visitor_support.html # Visitor requests & response handling
    │   ├── system_activity.html # Comprehensive audit trail
    │   ├── reports.html       # Printable annual summary report
    │   ├── settings.html      # System parameters & helpline numbers
    │   └── notifications.html # Broadcast notification dispatch
    └── errors/
        ├── 403.html           # Access Forbidden error page
        ├── 404.html           # Page Not Found error page
        └── 500.html           # Internal Server Error page
```

---

## 🚀 Installation & Running the Application

### 1. Prerequisites
Ensure **Python 3.10+** is installed on your computer.

### 2. Navigate to Project Directory
```powershell
cd C:\Users\annab\.gemini\antigravity\scratch\vjec_complaint_system
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Seed Database with Official VJEC Demo Data
```powershell
python seed.py
```

### 5. Run the Automated Test Suite (Optional)
Verify all 8 test suites pass:
```powershell
python test_app.py
```

### 6. Start the Flask Server
```powershell
python app.py
```

### 7. Access the Application
Open your web browser and visit:
```text
http://127.0.0.1:5000
```

---

## 🔒 Security & Privacy Implementation Highlights

1. **Backend Database Verification**:
   - Unauthorized access to complaints (e.g., student A trying to query `/student/complaints/<id>` belonging to student B) aborts with HTTP `403 Forbidden` at the database query level.
2. **Password Hashing**:
   - Passwords are encrypted using Werkzeug's `generate_password_hash` (`pbkdf2:sha256`) and never stored or returned in plaintext.
3. **Session Authentication**:
   - Flask sessions track user identity; logout clears sessions and flushes state.
4. **Login ID Validation**:
   - Validates that student and faculty registration IDs strictly begin with `VML`.
   - Prevents self-registration of arbitrary administrator accounts.
5. **Secure Uploads**:
   - Strict file extension validation (`png`, `jpg`, `pdf`, `doc`, `docx`, `txt`) and randomized filename hashing to prevent path traversal.

---

## 🎓 Project Demonstration Guide

1. **Homepage**: Observe the **Designation Selection First Interface** with 4 institutional roles.
2. **Student Flow**:
   - Sign in as **Theresa Binny** (`VML23EC040` / `theresa@123`).
   - Notice her 4 complaints (including `CMP-2026-101`).
   - Register a new complaint with the **Submit Anonymously** checkbox checked.
   - Post an update in the live discussion box.
   - Book a session in the **Counselling** module.
   - Test privacy: try typing the URL for Aneeta's complaint (`/student/complaints/CMP-2026-201`) to witness the custom **403 Forbidden Access Denied** page.
3. **Faculty Flow**:
   - Sign in as **Ms. Arya Thalakkat** (`VML23FT001` / `Arya@123`).
   - Notice she manages ECE complaints. Open `CMP-2026-101`, post a reply, update status to `Action Taken`, and view timeline.
4. **Counsellor Flow**:
   - Sign in as **Dr. Mathew Joseph** (`VML23CN001` / `Mathew@123`).
   - Confirm or reschedule the student appointment request.
5. **Administrator Flow**:
   - Sign in as **Administrator** (`ADM2604` / `Admin@123`).
   - View dynamic Chart.js dashboards, all 10 departments, user management table, anti-ragging portal, visitor desk, audit log, and printable annual report.
