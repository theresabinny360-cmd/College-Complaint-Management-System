import os
import uuid
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort, send_from_directory
)
from werkzeug.utils import secure_filename
from config import Config
from models import (
    db, User, Department, Complaint, ComplaintHistory, ComplaintMessage,
    CounsellingAppointment, AntiRaggingComplaint, Feedback, VisitorRequest,
    Notification, AuditLog, SystemSetting
)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

    db.init_app(app)

    # -------------------------------------------------------------
    # Helper Decorators & Functions
    # -------------------------------------------------------------
    def get_current_user():
        if 'user_id' in session:
            return User.query.get(session['user_id'])
        return None

    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            user = get_current_user()
            if not user or user.status != 'ACTIVE':
                session.clear()
                flash('Your account is inactive or not found. Please contact administration.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    def role_required(allowed_roles):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'user_id' not in session:
                    flash('Please log in to access this page.', 'warning')
                    return redirect(url_for('login'))
                user = get_current_user()
                if not user or user.status != 'ACTIVE':
                    session.clear()
                    flash('Your account is inactive or not found.', 'danger')
                    return redirect(url_for('login'))
                if user.role not in allowed_roles:
                    # Strict role authorization - unauthorized access
                    abort(403)
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    def save_upload_file(file):
        if file and file.filename and allowed_file(file.filename):
            orig_filename = secure_filename(file.filename)
            unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}_{orig_filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
            return unique_name
        return None

    def log_audit(action, details=None, user=None):
        try:
            u = user or get_current_user()
            log = AuditLog(
                user_id=u.id if u else None,
                user_name=u.name if u else 'System/Guest',
                user_role=u.role if u else 'ANONYMOUS',
                action=action,
                details=details,
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()
        except Exception:
            db.session.rollback()

    def create_notification(user_id, title, message, link=None, category='complaint'):
        try:
            notif = Notification(
                user_id=user_id,
                title=title,
                message=message,
                link=link,
                category=category
            )
            db.session.add(notif)
            db.session.commit()
        except Exception:
            db.session.rollback()

    # -------------------------------------------------------------
    # Context Processors & Filters
    # -------------------------------------------------------------
    @app.context_processor
    def inject_global_data():
        current_user = get_current_user()
        unread_notifications_count = 0
        recent_notifications = []
        if current_user:
            unread_notifications_count = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()
            recent_notifications = Notification.query.filter_by(
                user_id=current_user.id
            ).order_by(Notification.created_at.desc()).limit(5).all()

        all_depts = Department.query.order_by(Department.code.asc()).all()
        return dict(
            current_user=current_user,
            unread_notifications_count=unread_notifications_count,
            recent_notifications=recent_notifications,
            all_departments=all_depts,
            now=datetime.utcnow(),
            college_name="Vimal Jyothi Engineering College",
            college_short="VJEC"
        )

    @app.template_filter('status_badge')
    def status_badge_filter(status):
        badges = {
            'Submitted': 'badge-secondary',
            'Under Review': 'badge-info',
            'Assigned': 'badge-primary',
            'In Progress': 'badge-warning',
            'Action Taken': 'badge-teal',
            'Awaiting Student Feedback': 'badge-purple',
            'Resolved': 'badge-success',
            'Closed': 'badge-dark',
            'Requested': 'badge-info',
            'Confirmed': 'badge-success',
            'Rescheduled': 'badge-warning',
            'Completed': 'badge-teal',
            'Cancelled': 'badge-danger',
            'Pending': 'badge-warning',
            'Responded': 'badge-success'
        }
        return badges.get(status, 'badge-secondary')

    @app.template_filter('priority_badge')
    def priority_badge_filter(priority):
        badges = {
            'Low': 'badge-priority-low',
            'Medium': 'badge-priority-medium',
            'High': 'badge-priority-high',
            'Critical': 'badge-priority-critical'
        }
        return badges.get(priority, 'badge-priority-medium')

    @app.template_filter('format_datetime')
    def format_datetime_filter(dt):
        if not dt:
            return '—'
        return dt.strftime('%d %b %Y, %I:%M %p')

    @app.template_filter('format_date')
    def format_date_filter(dt):
        if not dt:
            return '—'
        if isinstance(dt, str):
            return dt
        return dt.strftime('%d %b %Y')

    # -------------------------------------------------------------
    # Error Handlers
    # -------------------------------------------------------------
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # -------------------------------------------------------------
    # Upload File Serving
    # -------------------------------------------------------------
    @app.route('/uploads/<filename>')
    @login_required
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # =============================================================
    # 1. DESIGNATION SELECTION & AUTHENTICATION
    # =============================================================
    @app.route('/')
    def index():
        # First interface: Professional designation-selection screen
        # If user is already logged in, redirect to their role dashboard
        if 'user_id' in session and 'role' in session:
            role = session['role']
            if role == 'STUDENT':
                return redirect(url_for('student_dashboard'))
            elif role == 'FACULTY':
                return redirect(url_for('faculty_dashboard'))
            elif role == 'COUNSELLOR':
                return redirect(url_for('counsellor_dashboard'))
            elif role == 'ADMINISTRATOR':
                return redirect(url_for('admin_dashboard'))
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    @app.route('/login/<role_param>', methods=['GET', 'POST'])
    def login(role_param=None):
        if 'user_id' in session:
            role = session.get('role')
            if role == 'STUDENT':
                return redirect(url_for('student_dashboard'))
            elif role == 'FACULTY':
                return redirect(url_for('faculty_dashboard'))
            elif role == 'COUNSELLOR':
                return redirect(url_for('counsellor_dashboard'))
            elif role == 'ADMINISTRATOR':
                return redirect(url_for('admin_dashboard'))

        # Map role parameter
        valid_roles = {
            'student': 'STUDENT',
            'faculty': 'FACULTY',
            'counsellor': 'COUNSELLOR',
            'admin': 'ADMINISTRATOR',
            'administrator': 'ADMINISTRATOR'
        }
        selected_role = valid_roles.get(role_param.lower()) if role_param else None

        if request.method == 'POST':
            login_id = request.form.get('login_id', '').strip()
            password = request.form.get('password', '').strip()
            chosen_role = request.form.get('designation', '').strip()

            if not login_id or not password:
                flash('Please enter both Login ID and Password.', 'danger')
                return render_template('login.html', selected_role=selected_role)

            user = User.query.filter_by(login_id=login_id).first()

            if not user or not user.check_password(password):
                flash('Invalid Login ID or Password. Please try again.', 'danger')
                log_audit('Failed Login Attempt', f'Login ID: {login_id}')
                return render_template('login.html', selected_role=selected_role)

            if user.status != 'ACTIVE':
                flash('Your account has been deactivated. Please contact the administrator.', 'warning')
                return render_template('login.html', selected_role=selected_role)

            # Role verification: Do NOT allow a student to log in through faculty/admin account type
            if chosen_role and user.role != chosen_role:
                flash(f'Designation mismatch: Account {login_id} is registered as {user.role}, not {chosen_role}. Please select the correct designation.', 'danger')
                return render_template('login.html', selected_role=selected_role)

            # Successful login
            session.clear()
            session['user_id'] = user.id
            session['login_id'] = user.login_id
            session['name'] = user.name
            session['role'] = user.role
            session['department'] = user.department

            log_audit('User Login', f'User {user.name} ({user.login_id}) logged in as {user.role}', user)
            flash(f'Welcome back, {user.name}!', 'success')

            if user.role == 'STUDENT':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'FACULTY':
                return redirect(url_for('faculty_dashboard'))
            elif user.role == 'COUNSELLOR':
                return redirect(url_for('counsellor_dashboard'))
            elif user.role == 'ADMINISTRATOR':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))

        return render_template('login.html', selected_role=selected_role)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        preselected_role = request.args.get('role', 'student').lower()
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            login_id = request.form.get('login_id', '').strip().upper()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            designation = request.form.get('designation', '').strip().upper()
            department = request.form.get('department', '').strip()
            year_semester = request.form.get('year_semester', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()

            # Validation
            if not name or not login_id or not password or not designation:
                flash('Please fill in all required fields.', 'danger')
                return render_template('register.html', preselected_role=preselected_role)

            if password != confirm_password:
                flash('Passwords do not match. Please verify your password.', 'danger')
                return render_template('register.html', preselected_role=preselected_role)

            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'danger')
                return render_template('register.html', preselected_role=preselected_role)

            # Security: Normal users cannot register an Administrator account directly
            if designation == 'ADMINISTRATOR':
                flash('Administrator accounts cannot be self-registered. Please contact system admin.', 'danger')
                return render_template('register.html', preselected_role=preselected_role)

            # Login ID validation: must begin with VML
            if not login_id.startswith('VML'):
                flash('Invalid Login ID format! College Login ID must begin with "VML" (e.g. VML23EC040, VML23FT001).', 'danger')
                return render_template('register.html', preselected_role=preselected_role)

            # Check duplicate login_id
            existing = User.query.filter_by(login_id=login_id).first()
            if existing:
                flash(f'An account with Login ID {login_id} already exists. Please login or use your own ID.', 'danger')
                return render_template('register.html', preselected_role=preselected_role)

            # Check duplicate email if provided
            if email:
                existing_email = User.query.filter_by(email=email).first()
                if existing_email:
                    flash(f'Email address {email} is already associated with another account.', 'danger')
                    return render_template('register.html', preselected_role=preselected_role)

            # Status: Student accounts are active immediately; Faculty/Counsellor are Active
            new_user = User(
                name=name,
                login_id=login_id,
                role=designation,
                department=department if department else None,
                year_semester=year_semester if designation == 'STUDENT' else None,
                email=email if email else None,
                phone=phone if phone else None,
                status='ACTIVE'
            )
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()

            # Welcome notification
            create_notification(
                new_user.id,
                'Welcome to VJEC Complaint Portal',
                f'Welcome {new_user.name}! Your {new_user.role.capitalize()} account has been successfully created.',
                link=None,
                category='system'
            )

            log_audit('Account Created', f'New {designation} user {name} ({login_id}) registered', new_user)
            flash(f'Account created successfully for {login_id}! Please login with your credentials.', 'success')
            return redirect(url_for('login', role_param=designation.lower()))

        return render_template('register.html', preselected_role=preselected_role)

    @app.route('/logout')
    def logout():
        user = get_current_user()
        if user:
            log_audit('User Logout', f'User {user.name} logged out', user)
        session.clear()
        flash('You have been logged out successfully.', 'info')
        return redirect(url_for('index'))

    # =============================================================
    # 2. VISITOR SUPPORT (PUBLIC / ANYONE)
    # =============================================================
    @app.route('/visitor-support', methods=['GET', 'POST'])
    def visitor_support():
        if request.method == 'POST':
            name = request.form.get('visitor_name', '').strip()
            phone = request.form.get('contact_phone', '').strip()
            email = request.form.get('contact_email', '').strip()
            purpose = request.form.get('purpose', '').strip()
            department = request.form.get('department', '').strip()
            query = request.form.get('query', '').strip()
            visit_date = request.form.get('visit_date', '').strip()

            if not name or not phone or not query or not department:
                flash('Please complete all required fields.', 'danger')
                return render_template('visitor_support.html')

            # Generate Visitor Request ID
            req_count = VisitorRequest.query.count() + 1
            request_id = f"VIS-2026-{req_count:03d}"

            req_obj = VisitorRequest(
                request_id=request_id,
                visitor_name=name,
                contact_phone=phone,
                contact_email=email,
                purpose=purpose,
                department=department,
                query_text=query,
                visit_date=visit_date,
                status='Pending'
            )
            db.session.add(req_obj)
            db.session.commit()

            # Notify Admin
            admin_users = User.query.filter_by(role='ADMINISTRATOR').all()
            for adm in admin_users:
                create_notification(
                    adm.id,
                    f'New Visitor Support Request: {request_id}',
                    f'Visitor {name} submitted an inquiry regarding {department}.',
                    link=url_for('admin_visitor_support'),
                    category='system'
                )

            log_audit('Visitor Support Submitted', f'Request {request_id} from {name}')
            flash(f'Thank you, {name}! Your visitor request has been logged under Reference ID: {request_id}. Our administrative desk will review it shortly.', 'success')
            return redirect(url_for('visitor_support'))

        return render_template('visitor_support.html')

    # =============================================================
    # 3. STUDENT PORTAL MODULES
    # =============================================================
    @app.route('/student/dashboard')
    @role_required(['STUDENT'])
    def student_dashboard():
        student = get_current_user()
        
        # Privacy: Student only queries their OWN complaints
        my_complaints = Complaint.query.filter_by(student_id=student.id).order_by(Complaint.created_at.desc()).all()
        
        total_complaints = len(my_complaints)
        pending_complaints = sum(1 for c in my_complaints if c.status in ['Submitted', 'Under Review', 'Assigned'])
        in_progress_complaints = sum(1 for c in my_complaints if c.status in ['In Progress', 'Action Taken'])
        resolved_complaints = sum(1 for c in my_complaints if c.status in ['Resolved', 'Closed'])
        
        # Appointments
        my_appointments = CounsellingAppointment.query.filter_by(student_id=student.id).order_by(CounsellingAppointment.created_at.desc()).all()
        total_appointments = len(my_appointments)

        recent_complaints = my_complaints[:5]

        return render_template(
            'student/dashboard.html',
            total_complaints=total_complaints,
            pending_complaints=pending_complaints,
            in_progress_complaints=in_progress_complaints,
            resolved_complaints=resolved_complaints,
            total_appointments=total_appointments,
            recent_complaints=recent_complaints,
            appointments=my_appointments[:3]
        )

    @app.route('/student/complaints/new', methods=['GET', 'POST'])
    @role_required(['STUDENT'])
    def student_register_complaint():
        student = get_current_user()
        if request.method == 'POST':
            category = request.form.get('category', '').strip()
            department_code = request.form.get('department_code', '').strip().upper()
            priority = request.form.get('priority', 'Medium').strip()
            subject = request.form.get('subject', '').strip()
            description = request.form.get('description', '').strip()
            is_anonymous = request.form.get('is_anonymous') == 'on'
            file = request.files.get('attachment')

            if not category or not department_code or not subject or not description:
                flash('Please fill in all mandatory fields.', 'danger')
                return render_template('student/register_complaint.html')

            # Generate unique Complaint ID
            year = datetime.utcnow().year
            complaint_count = Complaint.query.count() + 1
            complaint_id = f"CMP-{year}-{complaint_count:03d}"

            attachment_filename = save_upload_file(file)

            # Auto-assign to faculty member of that department if available
            dept_faculty = User.query.filter_by(role='FACULTY', department=department_code, status='ACTIVE').first()
            assigned_id = dept_faculty.id if dept_faculty else None
            initial_status = 'Assigned' if assigned_id else 'Submitted'

            complaint = Complaint(
                complaint_id=complaint_id,
                student_id=student.id,
                department_code=department_code,
                assigned_to_id=assigned_id,
                category=category,
                priority=priority,
                subject=subject,
                description=description,
                is_anonymous=is_anonymous,
                status=initial_status,
                attachment_filename=attachment_filename
            )
            db.session.add(complaint)
            db.session.flush()

            # Create Initial History
            action_desc = "Complaint registered anonymously" if is_anonymous else f"Complaint registered by {student.name}"
            history = ComplaintHistory(
                complaint_id=complaint.id,
                action_by_id=student.id,
                action_by_name='Anonymous Student' if is_anonymous else student.name,
                action_by_role='STUDENT',
                action='Complaint Registered',
                previous_status=None,
                new_status=initial_status,
                comments=f"Category: {category} | Priority: {priority}" + (f" | Auto-assigned to {dept_faculty.name}" if dept_faculty else "")
            )
            db.session.add(history)

            # Notifications
            create_notification(
                student.id,
                f"Complaint Registered: {complaint_id}",
                f"Your complaint '{subject}' has been submitted. Status: {initial_status}.",
                link=url_for('student_complaint_detail', complaint_id=complaint_id),
                category='complaint'
            )

            if dept_faculty:
                create_notification(
                    dept_faculty.id,
                    f"New Assigned Complaint: {complaint_id}",
                    f"A new {priority} priority complaint '{subject}' has been assigned to your department ({department_code}).",
                    link=url_for('faculty_complaint_detail', complaint_id=complaint_id),
                    category='complaint'
                )

            db.session.commit()
            log_audit('Complaint Created', f"Complaint {complaint_id} created by {student.name} (Anonymous: {is_anonymous})", student)
            flash(f"Complaint registered successfully! Your tracking ID is {complaint_id}.", "success")
            return redirect(url_for('student_my_complaints'))

        return render_template('student/register_complaint.html')

    @app.route('/student/my-complaints')
    @role_required(['STUDENT'])
    def student_my_complaints():
        student = get_current_user()
        status_filter = request.args.get('status')
        category_filter = request.args.get('category')

        # Privacy rule: ONLY query complaints where student_id == current_user.id
        query = Complaint.query.filter_by(student_id=student.id)

        if status_filter:
            query = query.filter_by(status=status_filter)
        if category_filter:
            query = query.filter_by(category=category_filter)

        complaints = query.order_by(Complaint.created_at.desc()).all()
        return render_template('student/my_complaints.html', complaints=complaints,
                               status_filter=status_filter, category_filter=category_filter)

    @app.route('/student/complaints/<complaint_id>', methods=['GET', 'POST'])
    @role_required(['STUDENT'])
    def student_complaint_detail(complaint_id):
        student = get_current_user()
        complaint = Complaint.query.filter_by(complaint_id=complaint_id).first_or_404()

        # Strict Backend Privacy check: Theresa cannot view Aneeta's complaint!
        if complaint.student_id != student.id:
            abort(403)

        if request.method == 'POST':
            # Posting update / message in conversation
            message_text = request.form.get('message', '').strip()
            file = request.files.get('attachment')

            if message_text or file:
                att_file = save_upload_file(file)
                msg = ComplaintMessage(
                    complaint_id=complaint.id,
                    sender_id=student.id,
                    sender_name='Anonymous Student' if complaint.is_anonymous else student.name,
                    sender_role='STUDENT',
                    is_anonymous_sender=complaint.is_anonymous,
                    message=message_text,
                    attachment_filename=att_file
                )
                db.session.add(msg)

                # History log
                hist = ComplaintHistory(
                    complaint_id=complaint.id,
                    action_by_id=student.id,
                    action_by_name='Anonymous Student' if complaint.is_anonymous else student.name,
                    action_by_role='STUDENT',
                    action='Student added update / message',
                    previous_status=complaint.status,
                    new_status=complaint.status,
                    comments=message_text[:100] + '...' if len(message_text) > 100 else message_text
                )
                db.session.add(hist)

                # Notify assigned faculty or admin
                if complaint.assigned_to_id:
                    create_notification(
                        complaint.assigned_to_id,
                        f"Student Update on {complaint.complaint_id}",
                        f"New update/message on '{complaint.subject}'.",
                        link=url_for('faculty_complaint_detail', complaint_id=complaint.complaint_id),
                        category='complaint'
                    )

                db.session.commit()
                flash('Your update has been added to the complaint conversation.', 'success')
                return redirect(url_for('student_complaint_detail', complaint_id=complaint_id))

        return render_template('student/complaint_detail.html', complaint=complaint)

    @app.route('/student/track', methods=['GET', 'POST'])
    @role_required(['STUDENT'])
    def student_track_complaint():
        student = get_current_user()
        searched_id = request.args.get('complaint_id', '').strip()
        complaint = None
        error_msg = None

        if searched_id:
            found = Complaint.query.filter_by(complaint_id=searched_id).first()
            if not found:
                error_msg = f"No complaint found matching ID '{searched_id}'."
            elif found.student_id != student.id:
                # Privacy rule: Cannot track another student's complaint!
                error_msg = "Access Denied: You are not authorized to view this complaint."
            else:
                complaint = found

        return render_template('student/track_complaint.html', complaint=complaint,
                               searched_id=searched_id, error_msg=error_msg)

    @app.route('/student/counselling', methods=['GET', 'POST'])
    @role_required(['STUDENT'])
    def student_counselling():
        student = get_current_user()
        counsellors = User.query.filter_by(role='COUNSELLOR', status='ACTIVE').all()

        if request.method == 'POST':
            counsellor_id = request.form.get('counsellor_id')
            pref_date = request.form.get('preferred_date', '').strip()
            pref_time = request.form.get('preferred_time', '').strip()
            reason = request.form.get('reason', '').strip()
            confidential_note = request.form.get('confidential_note', '').strip()

            if not pref_date or not pref_time or not reason:
                flash('Please complete all mandatory appointment fields.', 'danger')
                return render_template('student/counselling.html', counsellors=counsellors)

            # Appointment ID
            count = CounsellingAppointment.query.count() + 1
            apt_id = f"APT-2026-{count:03d}"

            apt = CounsellingAppointment(
                appointment_id=apt_id,
                student_id=student.id,
                counsellor_id=int(counsellor_id) if counsellor_id else (counsellors[0].id if counsellors else None),
                preferred_date=pref_date,
                preferred_time=pref_time,
                reason=reason,
                confidential_note=confidential_note,
                status='Requested'
            )
            db.session.add(apt)
            db.session.commit()

            # Notify counsellor
            target_counsellor_id = apt.counsellor_id
            if target_counsellor_id:
                create_notification(
                    target_counsellor_id,
                    f"New Counselling Booking: {apt_id}",
                    f"Student {student.name} requested an appointment on {pref_date} at {pref_time}.",
                    link=url_for('counsellor_appointments'),
                    category='counselling'
                )

            log_audit('Counselling Appointment Booked', f"Appointment {apt_id} booked by {student.name}", student)
            flash(f"Counselling appointment requested successfully (Ref: {apt_id}). The counsellor will confirm your slot.", "success")
            return redirect(url_for('student_counselling'))

        # Fetch student's appointments
        appointments = CounsellingAppointment.query.filter_by(student_id=student.id).order_by(CounsellingAppointment.created_at.desc()).all()
        return render_template('student/counselling.html', counsellors=counsellors, appointments=appointments)

    @app.route('/student/anti-ragging', methods=['GET', 'POST'])
    @role_required(['STUDENT'])
    def student_anti_ragging():
        student = get_current_user()
        if request.method == 'POST':
            is_anon = request.form.get('is_anonymous') == 'on'
            category = request.form.get('incident_category', '').strip()
            description = request.form.get('description', '').strip()
            date = request.form.get('incident_date', '').strip()
            location = request.form.get('location', '').strip()
            is_emergency = request.form.get('is_emergency') == 'on'
            file = request.files.get('attachment')

            if not category or not description or not date or not location:
                flash('Please provide all details regarding the incident.', 'danger')
                return render_template('student/anti_ragging.html')

            count = AntiRaggingComplaint.query.count() + 1
            report_id = f"ARG-2026-{count:03d}"
            att_file = save_upload_file(file)

            report = AntiRaggingComplaint(
                report_id=report_id,
                student_id=student.id,
                is_anonymous=is_anon,
                complainant_name='Confidential Student' if is_anon else student.name,
                contact_info='Confidential (Protected in System)' if is_anon else (student.phone or student.email),
                incident_category=category,
                description=description,
                incident_date=date,
                location=location,
                is_emergency=is_emergency,
                attachment_filename=att_file,
                status='Submitted'
            )
            db.session.add(report)
            db.session.commit()

            # Strictly notify Admin and Counsellor
            officials = User.query.filter(User.role.in_(['ADMINISTRATOR', 'COUNSELLOR'])).all()
            for off in officials:
                create_notification(
                    off.id,
                    f"URGENT: Anti-Ragging Report Filed ({report_id})",
                    f"New {'EMERGENCY ' if is_emergency else ''}Anti-Ragging report filed at location: {location}.",
                    link=url_for('admin_anti_ragging'),
                    category='system'
                )

            log_audit('Anti-Ragging Report Filed', f"Report {report_id} filed (Emergency: {is_emergency})", student)
            flash(f"Anti-Ragging complaint submitted confidentially under Report ID: {report_id}. The Anti-Ragging Committee has been alerted immediately.", "success")
            return redirect(url_for('student_anti_ragging'))

        # Fetch past anti-ragging reports filed by this student
        my_reports = AntiRaggingComplaint.query.filter_by(student_id=student.id).order_by(AntiRaggingComplaint.created_at.desc()).all()
        return render_template('student/anti_ragging.html', my_reports=my_reports)

    @app.route('/student/feedback/<complaint_id>', methods=['GET', 'POST'])
    @role_required(['STUDENT'])
    def student_feedback(complaint_id):
        student = get_current_user()
        complaint = Complaint.query.filter_by(complaint_id=complaint_id).first_or_404()

        # Privacy check
        if complaint.student_id != student.id:
            abort(403)

        if complaint.status not in ['Resolved', 'Closed']:
            flash('Feedback can only be submitted after a complaint has been resolved.', 'warning')
            return redirect(url_for('student_complaint_detail', complaint_id=complaint_id))

        if complaint.feedback:
            flash('You have already submitted feedback for this complaint.', 'info')
            return render_template('student/feedback.html', complaint=complaint, feedback=complaint.feedback)

        if request.method == 'POST':
            rating = int(request.form.get('rating', 5))
            satisfaction = request.form.get('satisfaction', 'Satisfied')
            comments = request.form.get('comments', '').strip()

            fb = Feedback(
                complaint_id=complaint.id,
                student_id=student.id,
                rating=rating,
                resolution_satisfaction=satisfaction,
                comments=comments
            )
            # Update complaint status to Closed if resolved
            complaint.status = 'Closed'
            db.session.add(fb)

            # History
            hist = ComplaintHistory(
                complaint_id=complaint.id,
                action_by_id=student.id,
                action_by_name=student.name,
                action_by_role='STUDENT',
                action='Student submitted feedback & closed complaint',
                previous_status='Resolved',
                new_status='Closed',
                comments=f"Rating: {rating}/5 | Satisfaction: {satisfaction}"
            )
            db.session.add(hist)

            # Notify assigned faculty
            if complaint.assigned_to_id:
                create_notification(
                    complaint.assigned_to_id,
                    f"Student Feedback Received: {complaint.complaint_id}",
                    f"Rating: {rating}/5 stars - '{comments[:80]}...'",
                    link=url_for('faculty_complaint_detail', complaint_id=complaint.complaint_id),
                    category='feedback'
                )

            db.session.commit()
            log_audit('Feedback Submitted', f"Feedback for {complaint.complaint_id} by {student.name}", student)
            flash('Thank you for your valuable feedback! The complaint has been officially closed.', 'success')
            return redirect(url_for('student_complaint_detail', complaint_id=complaint_id))

        return render_template('student/feedback.html', complaint=complaint, feedback=None)

    @app.route('/student/campus-navigation')
    @role_required(['STUDENT', 'FACULTY', 'COUNSELLOR', 'ADMINISTRATOR'])
    def campus_navigation():
        return render_template('student/campus_navigation.html')

    @app.route('/student/notifications')
    @role_required(['STUDENT'])
    def student_notifications():
        student = get_current_user()
        notifications = Notification.query.filter_by(user_id=student.id).order_by(Notification.created_at.desc()).all()
        # Mark all as read
        for n in notifications:
            n.is_read = True
        db.session.commit()
        return render_template('student/notifications.html', notifications=notifications)

    @app.route('/student/profile', methods=['GET', 'POST'])
    @role_required(['STUDENT'])
    def student_profile():
        student = get_current_user()
        if request.method == 'POST':
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip()
            student.phone = phone
            student.email = email
            db.session.commit()
            flash('Profile details updated successfully.', 'success')
            return redirect(url_for('student_profile'))
        return render_template('student/profile.html', user=student)

    # =============================================================
    # 4. FACULTY PORTAL MODULES
    # =============================================================
    @app.route('/faculty/dashboard')
    @role_required(['FACULTY'])
    def faculty_dashboard():
        faculty = get_current_user()
        dept_code = faculty.department or 'ECE'

        # Query complaints belonging to faculty's department OR assigned directly to them
        dept_complaints = Complaint.query.filter(
            (Complaint.department_code == dept_code) | (Complaint.assigned_to_id == faculty.id)
        ).order_by(Complaint.created_at.desc()).all()

        total = len(dept_complaints)
        new_count = sum(1 for c in dept_complaints if c.status == 'Submitted')
        assigned_count = sum(1 for c in dept_complaints if c.status == 'Assigned')
        in_progress_count = sum(1 for c in dept_complaints if c.status in ['In Progress', 'Action Taken'])
        resolved_count = sum(1 for c in dept_complaints if c.status in ['Resolved', 'Closed'])
        pending_count = sum(1 for c in dept_complaints if c.status not in ['Resolved', 'Closed'])

        recent = dept_complaints[:6]
        return render_template(
            'faculty/dashboard.html',
            faculty=faculty,
            dept_code=dept_code,
            total=total,
            new_count=new_count,
            assigned_count=assigned_count,
            in_progress_count=in_progress_count,
            resolved_count=resolved_count,
            pending_count=pending_count,
            recent_complaints=recent
        )

    @app.route('/faculty/complaints')
    @role_required(['FACULTY'])
    def faculty_complaints():
        faculty = get_current_user()
        dept_code = faculty.department or 'ECE'
        status_filter = request.args.get('status')
        priority_filter = request.args.get('priority')

        query = Complaint.query.filter(
            (Complaint.department_code == dept_code) | (Complaint.assigned_to_id == faculty.id)
        )
        if status_filter:
            query = query.filter(Complaint.status == status_filter)
        if priority_filter:
            query = query.filter(Complaint.priority == priority_filter)

        complaints = query.order_by(Complaint.created_at.desc()).all()
        return render_template(
            'faculty/assigned_complaints.html',
            complaints=complaints,
            status_filter=status_filter,
            priority_filter=priority_filter
        )

    @app.route('/faculty/complaints/<complaint_id>', methods=['GET', 'POST'])
    @role_required(['FACULTY'])
    def faculty_complaint_detail(complaint_id):
        faculty = get_current_user()
        complaint = Complaint.query.filter_by(complaint_id=complaint_id).first_or_404()

        # Authorization check: Can only view complaints of their department or assigned to them
        if complaint.department_code != faculty.department and complaint.assigned_to_id != faculty.id:
            abort(403)

        if request.method == 'POST':
            action_type = request.form.get('action_type')

            if action_type == 'update_status':
                new_status = request.form.get('status')
                remarks = request.form.get('remarks', '').strip()
                resolution_details = request.form.get('resolution_details', '').strip()

                if new_status and new_status != complaint.status:
                    prev_status = complaint.status
                    complaint.status = new_status
                    if new_status == 'Resolved':
                        complaint.resolved_at = datetime.utcnow()
                        complaint.resolution_details = resolution_details or remarks
                    elif resolution_details:
                        complaint.resolution_details = resolution_details

                    # History log
                    hist = ComplaintHistory(
                        complaint_id=complaint.id,
                        action_by_id=faculty.id,
                        action_by_name=faculty.name,
                        action_by_role='FACULTY',
                        action=f"Status changed to '{new_status}'",
                        previous_status=prev_status,
                        new_status=new_status,
                        comments=remarks or resolution_details
                    )
                    db.session.add(hist)

                    # Notify student
                    create_notification(
                        complaint.student_id,
                        f"Complaint Status Updated: {complaint.complaint_id}",
                        f"Your complaint '{complaint.subject}' status is now '{new_status}'. Updated by {faculty.name}.",
                        link=url_for('student_complaint_detail', complaint_id=complaint.complaint_id),
                        category='complaint'
                    )

                    db.session.commit()
                    log_audit('Status Updated by Faculty', f"Complaint {complaint.complaint_id} set to {new_status}", faculty)
                    flash(f"Complaint status updated to {new_status}.", "success")

            elif action_type == 'send_message':
                msg_text = request.form.get('message', '').strip()
                file = request.files.get('attachment')
                if msg_text or file:
                    att_file = save_upload_file(file)
                    msg = ComplaintMessage(
                        complaint_id=complaint.id,
                        sender_id=faculty.id,
                        sender_name=faculty.name,
                        sender_role='FACULTY',
                        is_anonymous_sender=False,
                        message=msg_text,
                        attachment_filename=att_file
                    )
                    db.session.add(msg)

                    hist = ComplaintHistory(
                        complaint_id=complaint.id,
                        action_by_id=faculty.id,
                        action_by_name=faculty.name,
                        action_by_role='FACULTY',
                        action='Faculty response posted',
                        previous_status=complaint.status,
                        new_status=complaint.status,
                        comments=msg_text[:100]
                    )
                    db.session.add(hist)

                    create_notification(
                        complaint.student_id,
                        f"New Message on {complaint.complaint_id}",
                        f"{faculty.name} sent a response: {msg_text[:80]}...",
                        link=url_for('student_complaint_detail', complaint_id=complaint.complaint_id),
                        category='complaint'
                    )

                    db.session.commit()
                    flash('Message sent to student successfully.', 'success')

            elif action_type == 'reassign_forward':
                target_dept = request.form.get('target_department')
                forward_notes = request.form.get('forward_notes', '').strip()
                if target_dept:
                    old_dept = complaint.department_code
                    complaint.department_code = target_dept
                    complaint.assigned_to_id = None
                    complaint.status = 'Under Review'

                    hist = ComplaintHistory(
                        complaint_id=complaint.id,
                        action_by_id=faculty.id,
                        action_by_name=faculty.name,
                        action_by_role='FACULTY',
                        action=f"Forwarded from {old_dept} to {target_dept}",
                        previous_status=complaint.status,
                        new_status='Under Review',
                        comments=forward_notes
                    )
                    db.session.add(hist)
                    db.session.commit()
                    flash(f"Complaint successfully forwarded to {target_dept} department.", 'success')
                    return redirect(url_for('faculty_complaints'))

            return redirect(url_for('faculty_complaint_detail', complaint_id=complaint_id))

        return render_template('faculty/complaint_detail.html', complaint=complaint)

    @app.route('/faculty/feedback')
    @role_required(['FACULTY'])
    def faculty_feedback():
        faculty = get_current_user()
        dept_code = faculty.department or 'ECE'
        # Query feedback on complaints for this department
        feedbacks = Feedback.query.join(Complaint).filter(Complaint.department_code == dept_code).order_by(Feedback.created_at.desc()).all()
        return render_template('faculty/feedback.html', feedbacks=feedbacks)

    @app.route('/faculty/notifications')
    @role_required(['FACULTY'])
    def faculty_notifications():
        faculty = get_current_user()
        notifs = Notification.query.filter_by(user_id=faculty.id).order_by(Notification.created_at.desc()).all()
        for n in notifs:
            n.is_read = True
        db.session.commit()
        return render_template('faculty/notifications.html', notifications=notifs)

    @app.route('/faculty/profile')
    @role_required(['FACULTY'])
    def faculty_profile():
        faculty = get_current_user()
        return render_template('faculty/profile.html', user=faculty)

    # =============================================================
    # 5. COUNSELLOR PORTAL MODULES
    # =============================================================
    @app.route('/counsellor/dashboard')
    @role_required(['COUNSELLOR'])
    def counsellor_dashboard():
        counsellor = get_current_user()
        appointments = CounsellingAppointment.query.order_by(CounsellingAppointment.created_at.desc()).all()

        total_apts = len(appointments)
        pending_requests = sum(1 for a in appointments if a.status == 'Requested')
        confirmed_apts = sum(1 for a in appointments if a.status == 'Confirmed')
        completed_apts = sum(1 for a in appointments if a.status == 'Completed')

        # Relevant complaints: complaints tagged under Counselling or Anti-Ragging
        relevant_complaints = Complaint.query.filter(
            Complaint.category.in_(['Counselling', 'Anti-Ragging', 'Campus Services'])
        ).order_by(Complaint.created_at.desc()).all()

        return render_template(
            'counsellor/dashboard.html',
            total_apts=total_apts,
            pending_requests=pending_requests,
            confirmed_apts=confirmed_apts,
            completed_apts=completed_apts,
            appointments=appointments[:5],
            complaints=relevant_complaints[:5]
        )

    @app.route('/counsellor/appointments', methods=['GET', 'POST'])
    @role_required(['COUNSELLOR'])
    def counsellor_appointments():
        counsellor = get_current_user()
        if request.method == 'POST':
            apt_id = request.form.get('appointment_id')
            action = request.form.get('action')
            apt = CounsellingAppointment.query.filter_by(appointment_id=apt_id).first_or_404()

            if action == 'confirm':
                confirmed_date = request.form.get('confirmed_date')
                confirmed_time = request.form.get('confirmed_time')
                venue = request.form.get('venue')
                notes = request.form.get('notes')

                apt.status = 'Confirmed'
                apt.confirmed_date = confirmed_date or apt.preferred_date
                apt.confirmed_time = confirmed_time or apt.preferred_time
                if venue:
                    apt.venue = venue
                if notes:
                    apt.counsellor_notes = notes
                apt.counsellor_id = counsellor.id

                create_notification(
                    apt.student_id,
                    f"Counselling Session Confirmed ({apt.appointment_id})",
                    f"Your appointment is confirmed for {apt.confirmed_date} at {apt.confirmed_time} at {apt.venue}.",
                    link=url_for('student_counselling'),
                    category='counselling'
                )
                flash(f"Appointment {apt.appointment_id} confirmed.", 'success')

            elif action == 'reschedule':
                rescheduled_date = request.form.get('rescheduled_date')
                rescheduled_time = request.form.get('rescheduled_time')
                notes = request.form.get('notes')
                apt.status = 'Rescheduled'
                apt.confirmed_date = rescheduled_date
                apt.confirmed_time = rescheduled_time
                apt.counsellor_notes = notes

                create_notification(
                    apt.student_id,
                    f"Counselling Session Rescheduled ({apt.appointment_id})",
                    f"Your appointment has been rescheduled to {rescheduled_date} at {rescheduled_time}.",
                    link=url_for('student_counselling'),
                    category='counselling'
                )
                flash(f"Appointment {apt.appointment_id} rescheduled.", 'warning')

            elif action == 'complete':
                notes = request.form.get('notes')
                apt.status = 'Completed'
                if notes:
                    apt.counsellor_notes = notes
                create_notification(
                    apt.student_id,
                    f"Counselling Session Completed",
                    f"Session {apt.appointment_id} marked as completed. Wishing you the best.",
                    link=url_for('student_counselling'),
                    category='counselling'
                )
                flash(f"Appointment marked as completed.", 'success')

            elif action == 'cancel':
                reason = request.form.get('notes', 'Cancelled by Counsellor')
                apt.status = 'Cancelled'
                apt.counsellor_notes = reason
                create_notification(
                    apt.student_id,
                    f"Counselling Session Cancelled",
                    f"Session {apt.appointment_id} was cancelled. Reason: {reason}",
                    link=url_for('student_counselling'),
                    category='counselling'
                )
                flash(f"Appointment {apt.appointment_id} cancelled.", 'info')

            db.session.commit()
            return redirect(url_for('counsellor_appointments'))

        appointments = CounsellingAppointment.query.order_by(CounsellingAppointment.created_at.desc()).all()
        return render_template('counsellor/appointments.html', appointments=appointments)

    @app.route('/counsellor/complaints')
    @role_required(['COUNSELLOR'])
    def counsellor_complaints():
        complaints = Complaint.query.filter(
            Complaint.category.in_(['Counselling', 'Anti-Ragging', 'Campus Services', 'Hostel', 'Academic'])
        ).order_by(Complaint.created_at.desc()).all()
        return render_template('counsellor/complaints.html', complaints=complaints)

    @app.route('/counsellor/complaints/<complaint_id>', methods=['GET', 'POST'])
    @role_required(['COUNSELLOR'])
    def counsellor_complaint_detail(complaint_id):
        counsellor = get_current_user()
        complaint = Complaint.query.filter_by(complaint_id=complaint_id).first_or_404()

        if request.method == 'POST':
            msg_text = request.form.get('message', '').strip()
            if msg_text:
                msg = ComplaintMessage(
                    complaint_id=complaint.id,
                    sender_id=counsellor.id,
                    sender_name=counsellor.name,
                    sender_role='COUNSELLOR',
                    is_anonymous_sender=False,
                    message=msg_text
                )
                db.session.add(msg)
                create_notification(
                    complaint.student_id,
                    f"Counsellor Response on {complaint.complaint_id}",
                    f"{counsellor.name} added advice/response.",
                    link=url_for('student_complaint_detail', complaint_id=complaint.complaint_id),
                    category='counselling'
                )
                db.session.commit()
                flash('Counselling response posted.', 'success')
                return redirect(url_for('counsellor_complaint_detail', complaint_id=complaint_id))

        return render_template('counsellor/complaint_detail.html', complaint=complaint)

    @app.route('/counsellor/notifications')
    @role_required(['COUNSELLOR'])
    def counsellor_notifications():
        counsellor = get_current_user()
        notifs = Notification.query.filter_by(user_id=counsellor.id).order_by(Notification.created_at.desc()).all()
        for n in notifs:
            n.is_read = True
        db.session.commit()
        return render_template('counsellor/notifications.html', notifications=notifs)

    @app.route('/counsellor/profile')
    @role_required(['COUNSELLOR'])
    def counsellor_profile():
        return render_template('counsellor/profile.html', user=get_current_user())

    # =============================================================
    # 6. ADMINISTRATOR PORTAL MODULES
    # =============================================================
    @app.route('/admin/dashboard')
    @role_required(['ADMINISTRATOR'])
    def admin_dashboard():
        # Comprehensive system analytics
        total_users = User.query.count()
        total_students = User.query.filter_by(role='STUDENT').count()
        total_faculty = User.query.filter_by(role='FACULTY').count()
        total_counsellors = User.query.filter_by(role='COUNSELLOR').count()

        total_complaints = Complaint.query.count()
        pending_complaints = Complaint.query.filter(Complaint.status.in_(['Submitted', 'Under Review', 'Assigned'])).count()
        in_progress_complaints = Complaint.query.filter(Complaint.status.in_(['In Progress', 'Action Taken'])).count()
        resolved_complaints = Complaint.query.filter(Complaint.status.in_(['Resolved', 'Closed'])).count()
        critical_complaints = Complaint.query.filter_by(priority='Critical').count()
        counselling_requests = CounsellingAppointment.query.count()
        anti_ragging_count = AntiRaggingComplaint.query.count()
        visitor_count = VisitorRequest.query.count()

        # Chart 1: Complaints by Department
        depts = Department.query.order_by(Department.code.asc()).all()
        dept_labels = [d.code for d in depts]
        dept_counts = [Complaint.query.filter_by(department_code=d.code).count() for d in depts]

        # Chart 2: Complaints by Category
        categories = ['Academic', 'Infrastructure', 'Hostel', 'Transportation', 'Campus Services',
                      'Faculty/Teaching', 'Examination', 'Library', 'Laboratory', 'IT/Internet', 'Anti-Ragging', 'Other']
        cat_counts = [Complaint.query.filter_by(category=c).count() for c in categories]

        # Chart 3: Status Breakdown
        statuses = ['Submitted', 'Under Review', 'Assigned', 'In Progress', 'Action Taken', 'Resolved', 'Closed']
        status_counts = [Complaint.query.filter_by(status=s).count() for s in statuses]

        recent_complaints = Complaint.query.order_by(Complaint.created_at.desc()).limit(6).all()
        recent_activities = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()

        return render_template(
            'admin/dashboard.html',
            total_users=total_users,
            total_students=total_students,
            total_faculty=total_faculty,
            total_counsellors=total_counsellors,
            total_complaints=total_complaints,
            pending_complaints=pending_complaints,
            in_progress_complaints=in_progress_complaints,
            resolved_complaints=resolved_complaints,
            critical_complaints=critical_complaints,
            counselling_requests=counselling_requests,
            anti_ragging_count=anti_ragging_count,
            visitor_count=visitor_count,
            dept_labels=dept_labels,
            dept_counts=dept_counts,
            categories=categories,
            cat_counts=cat_counts,
            statuses=statuses,
            status_counts=status_counts,
            recent_complaints=recent_complaints,
            recent_activities=recent_activities
        )

    # User Management
    @app.route('/admin/users')
    @role_required(['ADMINISTRATOR'])
    def admin_users():
        role_filter = request.args.get('role')
        dept_filter = request.args.get('department')
        search_query = request.args.get('q', '').strip()

        query = User.query
        if role_filter:
            query = query.filter_by(role=role_filter)
        if dept_filter:
            query = query.filter_by(department=dept_filter)
        if search_query:
            query = query.filter(
                (User.name.ilike(f'%{search_query}%')) |
                (User.login_id.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%'))
            )

        users = query.order_by(User.created_at.desc()).all()
        return render_template(
            'admin/users.html',
            users=users,
            role_filter=role_filter,
            dept_filter=dept_filter,
            search_query=search_query
        )

    @app.route('/admin/users/new', methods=['GET', 'POST'])
    @role_required(['ADMINISTRATOR'])
    def admin_user_create():
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            login_id = request.form.get('login_id', '').strip().upper()
            password = request.form.get('password', '').strip()
            role = request.form.get('role', '').strip().upper()
            department = request.form.get('department', '').strip()
            year_semester = request.form.get('year_semester', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()

            if not name or not login_id or not password or not role:
                flash('Please complete all required fields.', 'danger')
                return render_template('admin/user_form.html', user=None)

            if User.query.filter_by(login_id=login_id).first():
                flash(f'User with Login ID {login_id} already exists.', 'danger')
                return render_template('admin/user_form.html', user=None)

            new_user = User(
                name=name,
                login_id=login_id,
                role=role,
                department=department or None,
                year_semester=year_semester or None,
                email=email or None,
                phone=phone or None,
                status='ACTIVE'
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            log_audit('Admin Created User', f"Admin created user {name} ({login_id}) as {role}")
            flash(f"User {name} ({login_id}) created successfully.", 'success')
            return redirect(url_for('admin_users'))

        return render_template('admin/user_form.html', user=None)

    @app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
    @role_required(['ADMINISTRATOR'])
    def admin_user_edit(user_id):
        user = User.query.get_or_404(user_id)
        if request.method == 'POST':
            user.name = request.form.get('name', '').strip()
            user.department = request.form.get('department', '').strip() or None
            user.year_semester = request.form.get('year_semester', '').strip() or None
            user.email = request.form.get('email', '').strip() or None
            user.phone = request.form.get('phone', '').strip() or None
            user.status = request.form.get('status', 'ACTIVE')
            new_pass = request.form.get('password', '').strip()
            if new_pass:
                user.set_password(new_pass)

            db.session.commit()
            log_audit('Admin Edited User', f"User {user.login_id} modified by admin")
            flash(f"User {user.name} ({user.login_id}) updated successfully.", 'success')
            return redirect(url_for('admin_users'))

        return render_template('admin/user_form.html', user=user)

    @app.route('/admin/users/<int:user_id>/toggle-status')
    @role_required(['ADMINISTRATOR'])
    def admin_user_toggle_status(user_id):
        user = User.query.get_or_404(user_id)
        if user.login_id == 'ADM2604':
            flash('Cannot deactivate primary administrator account.', 'danger')
            return redirect(url_for('admin_users'))

        user.status = 'INACTIVE' if user.status == 'ACTIVE' else 'ACTIVE'
        db.session.commit()
        log_audit('Admin Toggled User Status', f"User {user.login_id} status changed to {user.status}")
        flash(f"Account for {user.name} is now {user.status}.", 'info')
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
    @role_required(['ADMINISTRATOR'])
    def admin_user_delete(user_id):
        user = User.query.get_or_404(user_id)
        if user.login_id == 'ADM2604':
            flash('Cannot delete primary administrator account.', 'danger')
            return redirect(url_for('admin_users'))

        db.session.delete(user)
        db.session.commit()
        log_audit('Admin Deleted User', f"Deleted user ID {user_id}")
        flash('User deleted successfully.', 'success')
        return redirect(url_for('admin_users'))

    # Department Management
    @app.route('/admin/departments')
    @role_required(['ADMINISTRATOR'])
    def admin_departments():
        departments = Department.query.order_by(Department.code.asc()).all()
        # Compute count of complaints and faculty per department
        dept_data = []
        for d in departments:
            complaint_count = Complaint.query.filter_by(department_code=d.code).count()
            faculty_count = User.query.filter_by(role='FACULTY', department=d.code).count()
            dept_data.append({
                'dept': d,
                'complaints': complaint_count,
                'faculty_count': faculty_count
            })
        return render_template('admin/departments.html', dept_data=dept_data)

    @app.route('/admin/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
    @role_required(['ADMINISTRATOR'])
    def admin_department_edit(dept_id):
        dept = Department.query.get_or_404(dept_id)
        if request.method == 'POST':
            dept.name = request.form.get('name', '').strip()
            dept.hod_name = request.form.get('hod_name', '').strip()
            dept.contact_email = request.form.get('contact_email', '').strip()
            dept.location = request.form.get('location', '').strip()
            dept.phone = request.form.get('phone', '').strip()
            db.session.commit()
            log_audit('Department Updated', f"Department {dept.code} updated by admin")
            flash(f"Department {dept.code} updated successfully.", 'success')
            return redirect(url_for('admin_departments'))
        return render_template('admin/department_edit.html', dept=dept)

    # All Complaints Super-View & Routing
    @app.route('/admin/complaints')
    @role_required(['ADMINISTRATOR'])
    def admin_complaints():
        dept_filter = request.args.get('department')
        status_filter = request.args.get('status')
        priority_filter = request.args.get('priority')
        category_filter = request.args.get('category')

        query = Complaint.query
        if dept_filter:
            query = query.filter_by(department_code=dept_filter)
        if status_filter:
            query = query.filter_by(status=status_filter)
        if priority_filter:
            query = query.filter_by(priority=priority_filter)
        if category_filter:
            query = query.filter_by(category=category_filter)

        complaints = query.order_by(Complaint.created_at.desc()).all()
        return render_template(
            'admin/complaints.html',
            complaints=complaints,
            dept_filter=dept_filter,
            status_filter=status_filter,
            priority_filter=priority_filter,
            category_filter=category_filter
        )

    @app.route('/admin/complaints/<complaint_id>', methods=['GET', 'POST'])
    @role_required(['ADMINISTRATOR'])
    def admin_complaint_detail(complaint_id):
        admin = get_current_user()
        complaint = Complaint.query.filter_by(complaint_id=complaint_id).first_or_404()
        faculty_list = User.query.filter_by(role='FACULTY', status='ACTIVE').all()
        counsellor_list = User.query.filter_by(role='COUNSELLOR', status='ACTIVE').all()

        if request.method == 'POST':
            action_type = request.form.get('action_type')

            if action_type == 'admin_update':
                new_status = request.form.get('status')
                new_priority = request.form.get('priority')
                new_category = request.form.get('category')
                assigned_to_id = request.form.get('assigned_to_id')
                admin_remarks = request.form.get('remarks', '').strip()
                resolution_details = request.form.get('resolution_details', '').strip()

                changes = []
                if new_status and new_status != complaint.status:
                    changes.append(f"Status: {complaint.status} -> {new_status}")
                    prev_status = complaint.status
                    complaint.status = new_status
                    if new_status == 'Resolved':
                        complaint.resolved_at = datetime.utcnow()
                else:
                    prev_status = complaint.status

                if new_priority and new_priority != complaint.priority:
                    changes.append(f"Priority: {complaint.priority} -> {new_priority}")
                    complaint.priority = new_priority

                if new_category and new_category != complaint.category:
                    changes.append(f"Category: {complaint.category} -> {new_category}")
                    complaint.category = new_category

                if assigned_to_id:
                    new_assignee_id = int(assigned_to_id)
                    if new_assignee_id != complaint.assigned_to_id:
                        assignee = User.query.get(new_assignee_id)
                        changes.append(f"Assigned to: {assignee.name}")
                        complaint.assigned_to_id = new_assignee_id
                        # Alert assignee
                        create_notification(
                            new_assignee_id,
                            f"Complaint Assigned by Admin: {complaint.complaint_id}",
                            f"Administrator assigned '{complaint.subject}' to you.",
                            link=url_for('faculty_complaint_detail', complaint_id=complaint.complaint_id),
                            category='complaint'
                        )

                if resolution_details:
                    complaint.resolution_details = resolution_details

                if changes or admin_remarks:
                    hist = ComplaintHistory(
                        complaint_id=complaint.id,
                        action_by_id=admin.id,
                        action_by_name=admin.name,
                        action_by_role='ADMINISTRATOR',
                        action=f"Admin updated: {', '.join(changes)}" if changes else "Admin remarks added",
                        previous_status=prev_status,
                        new_status=complaint.status,
                        comments=admin_remarks or resolution_details
                    )
                    db.session.add(hist)

                    # Notify student
                    create_notification(
                        complaint.student_id,
                        f"Complaint Updated by Admin ({complaint.complaint_id})",
                        f"Status: {complaint.status} | {admin_remarks[:80] if admin_remarks else 'System update'}",
                        link=url_for('student_complaint_detail', complaint_id=complaint.complaint_id),
                        category='complaint'
                    )

                db.session.commit()
                log_audit('Admin Complaint Update', f"Complaint {complaint.complaint_id} updated: {changes}")
                flash(f"Complaint {complaint.complaint_id} updated successfully.", 'success')

            elif action_type == 'admin_message':
                msg_text = request.form.get('message', '').strip()
                if msg_text:
                    msg = ComplaintMessage(
                        complaint_id=complaint.id,
                        sender_id=admin.id,
                        sender_name=admin.name,
                        sender_role='ADMINISTRATOR',
                        is_anonymous_sender=False,
                        message=msg_text
                    )
                    db.session.add(msg)
                    create_notification(
                        complaint.student_id,
                        f"Administrator Message on {complaint.complaint_id}",
                        f"Admin Office: {msg_text[:80]}...",
                        link=url_for('student_complaint_detail', complaint_id=complaint.complaint_id),
                        category='complaint'
                    )
                    db.session.commit()
                    flash('Admin message posted to conversation.', 'success')

            return redirect(url_for('admin_complaint_detail', complaint_id=complaint_id))

        return render_template(
            'admin/complaint_detail.html',
            complaint=complaint,
            faculty_list=faculty_list,
            counsellor_list=counsellor_list
        )

    # Anti-Ragging Management
    @app.route('/admin/anti-ragging', methods=['GET', 'POST'])
    @role_required(['ADMINISTRATOR'])
    def admin_anti_ragging():
        if request.method == 'POST':
            report_id = request.form.get('report_id')
            status = request.form.get('status')
            action_taken = request.form.get('action_taken', '').strip()
            notes = request.form.get('investigation_notes', '').strip()

            report = AntiRaggingComplaint.query.filter_by(report_id=report_id).first_or_404()
            report.status = status
            report.action_taken = action_taken
            report.investigation_notes = notes

            db.session.commit()
            log_audit('Anti-Ragging Updated', f"Report {report_id} status changed to {status}")
            flash(f"Anti-Ragging report {report_id} updated successfully.", 'success')
            return redirect(url_for('admin_anti_ragging'))

        reports = AntiRaggingComplaint.query.order_by(AntiRaggingComplaint.created_at.desc()).all()
        return render_template('admin/anti_ragging.html', reports=reports)

    # Counselling Management
    @app.route('/admin/counselling')
    @role_required(['ADMINISTRATOR'])
    def admin_counselling():
        appointments = CounsellingAppointment.query.order_by(CounsellingAppointment.created_at.desc()).all()
        return render_template('admin/counselling.html', appointments=appointments)

    # Feedback Management
    @app.route('/admin/feedback')
    @role_required(['ADMINISTRATOR'])
    def admin_feedback():
        feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
        avg_rating = 0
        if feedbacks:
            avg_rating = round(sum(f.rating for f in feedbacks) / len(feedbacks), 1)
        return render_template('admin/feedback.html', feedbacks=feedbacks, avg_rating=avg_rating)

    # Visitor Support Management
    @app.route('/admin/visitor-support', methods=['GET', 'POST'])
    @role_required(['ADMINISTRATOR'])
    def admin_visitor_support():
        if request.method == 'POST':
            req_id = request.form.get('request_id')
            response_text = request.form.get('admin_response', '').strip()
            new_status = request.form.get('status', 'Responded')

            vis_req = VisitorRequest.query.filter_by(request_id=req_id).first_or_404()
            vis_req.admin_response = response_text
            vis_req.status = new_status
            db.session.commit()
            log_audit('Visitor Request Handled', f"Request {req_id} updated to {new_status}")
            flash(f"Visitor request {req_id} updated.", 'success')
            return redirect(url_for('admin_visitor_support'))

        requests = VisitorRequest.query.order_by(VisitorRequest.created_at.desc()).all()
        return render_template('admin/visitor_support.html', requests=requests)

    # System Activity / Audit Logs
    @app.route('/admin/system-activity')
    @role_required(['ADMINISTRATOR'])
    def admin_system_activity():
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
        return render_template('admin/system_activity.html', logs=logs)

    # Reports
    @app.route('/admin/reports')
    @role_required(['ADMINISTRATOR'])
    def admin_reports():
        total_complaints = Complaint.query.count()
        resolved_count = Complaint.query.filter_by(status='Resolved').count()
        resolution_rate = round((resolved_count / total_complaints * 100) if total_complaints > 0 else 0, 1)

        depts = Department.query.all()
        dept_report = []
        for d in depts:
            tot = Complaint.query.filter_by(department_code=d.code).count()
            res = Complaint.query.filter_by(department_code=d.code, status='Resolved').count()
            dept_report.append({
                'code': d.code,
                'name': d.name,
                'total': tot,
                'resolved': res,
                'rate': round((res / tot * 100) if tot > 0 else 0, 1)
            })

        return render_template(
            'admin/reports.html',
            total_complaints=total_complaints,
            resolved_count=resolved_count,
            resolution_rate=resolution_rate,
            dept_report=dept_report
        )

    # Settings
    @app.route('/admin/settings', methods=['GET', 'POST'])
    @role_required(['ADMINISTRATOR'])
    def admin_settings():
        if request.method == 'POST':
            for key, val in request.form.items():
                setting = SystemSetting.query.filter_by(key=key).first()
                if setting:
                    setting.value = val
                else:
                    new_set = SystemSetting(key=key, value=val)
                    db.session.add(new_set)
            db.session.commit()
            log_audit('System Settings Updated', 'Administrator updated system settings')
            flash('System settings updated successfully.', 'success')
            return redirect(url_for('admin_settings'))

        settings = {s.key: s.value for s in SystemSetting.query.all()}
        return render_template('admin/settings.html', settings=settings)

    # Admin Notifications Module (Broadcast & User Alerts)
    @app.route('/admin/notifications', methods=['GET', 'POST'])
    @role_required(['ADMINISTRATOR'])
    def admin_notifications():
        if request.method == 'POST':
            target_role = request.form.get('target_role')
            title = request.form.get('title', '').strip()
            message = request.form.get('message', '').strip()

            if title and message:
                if target_role == 'ALL':
                    targets = User.query.filter_by(status='ACTIVE').all()
                else:
                    targets = User.query.filter_by(role=target_role, status='ACTIVE').all()

                for u in targets:
                    create_notification(u.id, title, message, link=None, category='system')

                db.session.commit()
                log_audit('Broadcast Notification Sent', f"Title: '{title}' sent to {target_role}")
                flash(f"Notification broadcast successfully sent to {len(targets)} users ({target_role}).", 'success')
                return redirect(url_for('admin_notifications'))

        all_notifs = Notification.query.order_by(Notification.created_at.desc()).limit(50).all()
        return render_template('admin/notifications.html', notifications=all_notifs)

    # AJAX endpoint to mark notification as read
    @app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
    @login_required
    def api_mark_notification_read(notif_id):
        user = get_current_user()
        notif = Notification.query.filter_by(id=notif_id, user_id=user.id).first()
        if notif:
            notif.is_read = True
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False}), 404

    @app.route('/api/notifications/read-all', methods=['POST'])
    @login_required
    def api_mark_all_read():
        user = get_current_user()
        Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
        db.session.commit()
        return jsonify({'success': True})

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=5000)
