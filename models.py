from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    login_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # STUDENT, FACULTY, COUNSELLOR, ADMINISTRATOR
    department = db.Column(db.String(20), nullable=True)  # ECE, CSE, etc.
    year_semester = db.Column(db.String(50), nullable=True)  # '4th Year', '3rd Year / S5', etc.
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default='ACTIVE')  # ACTIVE, INACTIVE
    profile_image = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    complaints = db.relationship('Complaint', backref='student', lazy='dynamic',
                                 foreign_keys='Complaint.student_id')
    assigned_complaints = db.relationship('Complaint', backref='assigned_to', lazy='dynamic',
                                          foreign_keys='Complaint.assigned_to_id')
    student_appointments = db.relationship('CounsellingAppointment', backref='student', lazy='dynamic',
                                           foreign_keys='CounsellingAppointment.student_id')
    counsellor_appointments = db.relationship('CounsellingAppointment', backref='counsellor', lazy='dynamic',
                                              foreign_keys='CounsellingAppointment.counsellor_id')
    notifications = db.relationship('Notification', backref='recipient', lazy='dynamic',
                                    foreign_keys='Notification.user_id',
                                    order_by='Notification.created_at.desc()')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'ADMINISTRATOR'

    def is_faculty(self):
        return self.role == 'FACULTY'

    def is_student(self):
        return self.role == 'STUDENT'

    def is_counsellor(self):
        return self.role == 'COUNSELLOR'

    def __repr__(self):
        return f'<User {self.login_id} - {self.name} ({self.role})>'


class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    hod_name = db.Column(db.String(100), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    location = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Department {self.code}: {self.name}>'


class Complaint(db.Model):
    __tablename__ = 'complaints'

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_code = db.Column(db.String(10), nullable=False)  # ECE, CSE, etc.
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    category = db.Column(db.String(50), nullable=False)  # Academic, Infrastructure, Hostel, Transportation, Campus Services, Faculty/Teaching, Examination, Library, Laboratory, IT/Internet, Anti-Ragging, Other
    priority = db.Column(db.String(20), default='Medium')  # Low, Medium, High, Critical
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    is_anonymous = db.Column(db.Boolean, default=False)
    
    # Status: Submitted, Under Review, Assigned, In Progress, Action Taken, Awaiting Student Feedback, Resolved, Closed
    status = db.Column(db.String(30), default='Submitted', nullable=False)
    attachment_filename = db.Column(db.String(255), nullable=True)
    resolution_details = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    history = db.relationship('ComplaintHistory', backref='complaint', lazy='dynamic',
                              cascade='all, delete-orphan',
                              order_by='ComplaintHistory.created_at.desc()')
    messages = db.relationship('ComplaintMessage', backref='complaint', lazy='dynamic',
                               cascade='all, delete-orphan',
                               order_by='ComplaintMessage.created_at.asc()')
    feedback = db.relationship('Feedback', backref='complaint', uselist=False,
                               cascade='all, delete-orphan')

    @property
    def display_author(self):
        """Show anonymous student if anonymous, unless for internal admin use"""
        if self.is_anonymous:
            return "Anonymous Student"
        return self.student.name if self.student else "Unknown"

    @property
    def status_step(self):
        """Returns integer 1 to 7 for visual timeline stepper"""
        steps = {
            'Submitted': 1,
            'Under Review': 2,
            'Assigned': 3,
            'In Progress': 4,
            'Action Taken': 5,
            'Awaiting Student Feedback': 6,
            'Resolved': 7,
            'Closed': 8
        }
        return steps.get(self.status, 1)

    def __repr__(self):
        return f'<Complaint {self.complaint_id} - {self.subject} ({self.status})>'


class ComplaintHistory(db.Model):
    __tablename__ = 'complaint_history'

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    action_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action_by_name = db.Column(db.String(100), nullable=False)
    action_by_role = db.Column(db.String(30), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    previous_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=True)
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ComplaintHistory {self.complaint_id}: {self.action}>'


class ComplaintMessage(db.Model):
    __tablename__ = 'complaint_messages'

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_name = db.Column(db.String(100), nullable=False)
    sender_role = db.Column(db.String(30), nullable=False)
    is_anonymous_sender = db.Column(db.Boolean, default=False)
    message = db.Column(db.Text, nullable=False)
    attachment_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id])

    @property
    def display_sender(self):
        if self.is_anonymous_sender:
            return "Anonymous Student"
        return self.sender_name

    def __repr__(self):
        return f'<ComplaintMessage {self.id} on {self.complaint_id} by {self.sender_name}>'


class CounsellingAppointment(db.Model):
    __tablename__ = 'counselling_appointments'

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    counsellor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    preferred_date = db.Column(db.String(30), nullable=False)
    preferred_time = db.Column(db.String(30), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    confidential_note = db.Column(db.Text, nullable=True)
    # Requested, Confirmed, Rescheduled, Completed, Cancelled
    status = db.Column(db.String(30), default='Requested', nullable=False)
    confirmed_date = db.Column(db.String(30), nullable=True)
    confirmed_time = db.Column(db.String(30), nullable=True)
    venue = db.Column(db.String(150), default='Student Counselling Cell, Main Block Room 204')
    counsellor_notes = db.Column(db.Text, nullable=True)
    student_feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<CounsellingAppointment {self.appointment_id} ({self.status})>'


class AntiRaggingComplaint(db.Model):
    __tablename__ = 'anti_ragging_complaints'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    complainant_name = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(100), nullable=True)
    incident_category = db.Column(db.String(100), nullable=False)  # Verbal, Physical, Hostelite Harassment, Social, Other
    description = db.Column(db.Text, nullable=False)
    incident_date = db.Column(db.String(30), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    is_emergency = db.Column(db.Boolean, default=False)
    attachment_filename = db.Column(db.String(255), nullable=True)
    # Submitted, Under Investigation, Action Taken, Closed
    status = db.Column(db.String(30), default='Submitted', nullable=False)
    investigation_notes = db.Column(db.Text, nullable=True)
    action_taken = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('User', foreign_keys=[student_id])

    @property
    def display_name(self):
        if self.is_anonymous:
            return "Confidential / Anonymous"
        return self.complainant_name

    def __repr__(self):
        return f'<AntiRaggingComplaint {self.report_id}>'


class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False, unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5
    resolution_satisfaction = db.Column(db.String(30), nullable=False)  # Highly Satisfied, Satisfied, Neutral, Dissatisfied
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('User', foreign_keys=[student_id])

    def __repr__(self):
        return f'<Feedback for Complaint #{self.complaint_id}: {self.rating} stars>'


class VisitorRequest(db.Model):
    __tablename__ = 'visitor_requests'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    visitor_name = db.Column(db.String(100), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)
    contact_email = db.Column(db.String(120), nullable=True)
    purpose = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    query_text = db.Column(db.Text, nullable=False)
    visit_date = db.Column(db.String(30), nullable=True)
    status = db.Column(db.String(30), default='Pending')  # Pending, Responded, Resolved, Closed
    admin_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<VisitorRequest {self.request_id} from {self.visitor_name}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(30), default='complaint')  # complaint, counselling, system, feedback
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_name = db.Column(db.String(100), nullable=True)
    user_role = db.Column(db.String(30), nullable=True)
    action = db.Column(db.String(150), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user_name}>'


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<SystemSetting {self.key}={self.value}>'
