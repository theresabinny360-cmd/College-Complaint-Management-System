import os
from datetime import datetime, timedelta
from app import create_app
from models import (
    db, User, Department, Complaint, ComplaintHistory, ComplaintMessage,
    CounsellingAppointment, AntiRaggingComplaint, Feedback, VisitorRequest,
    Notification, AuditLog, SystemSetting
)

app = create_app()

def seed_database():
    with app.app_context():
        # Ensure instance directory and upload directory exist
        instance_dir = os.path.join(app.root_path, 'instance')
        upload_dir = os.path.join(app.root_path, 'uploads')
        os.makedirs(instance_dir, exist_ok=True)
        os.makedirs(upload_dir, exist_ok=True)

        print("[SEED] Dropping and creating database tables...")
        db.drop_all()
        db.create_all()

        print("[SEED] Adding 10 Official VJEC Departments...")
        departments = [
            Department(
                code='ECE',
                name='Electronics and Communication Engineering',
                hod_name='Dr. Anto Sahayaraj',
                contact_email='hodece@vjec.ac.in',
                location='Academic Block B, 2nd Floor',
                phone='+91 4982 221351'
            ),
            Department(
                code='CSE',
                name='Computer Science and Engineering',
                hod_name='Dr. Jeethu V. Devasia',
                contact_email='hodcse@vjec.ac.in',
                location='Main Academic Block, 3rd Floor',
                phone='+91 4982 221352'
            ),
            Department(
                code='CSD',
                name='Computer Science and Design',
                hod_name='Dr. Manoj V. Thomas',
                contact_email='hodcsd@vjec.ac.in',
                location='Academic Block C, 1st Floor',
                phone='+91 4982 221353'
            ),
            Department(
                code='CSBS',
                name='Computer Science and Business Systems',
                hod_name='Dr. Jomy Jose',
                contact_email='hodcsbs@vjec.ac.in',
                location='Academic Block C, 2nd Floor',
                phone='+91 4982 221354'
            ),
            Department(
                code='CE',
                name='Civil Engineering',
                hod_name='Dr. Biju Mathew',
                contact_email='hodce@vjec.ac.in',
                location='Civil Engineering Block, Ground Floor',
                phone='+91 4982 221355'
            ),
            Department(
                code='ME',
                name='Mechanical Engineering',
                hod_name='Dr. S. Christopher Ezhil Singh',
                contact_email='hodme@vjec.ac.in',
                location='Mechanical Engineering Block',
                phone='+91 4982 221356'
            ),
            Department(
                code='EEE',
                name='Electrical and Electronics Engineering',
                hod_name='Dr. Justin P. Jose',
                contact_email='hodeee@vjec.ac.in',
                location='Electrical Engineering Block',
                phone='+91 4982 221357'
            ),
            Department(
                code='AEI',
                name='Applied Electronics and Instrumentation',
                hod_name='Dr. V. Sampath Kumar',
                contact_email='hodaei@vjec.ac.in',
                location='Academic Block B, 1st Floor',
                phone='+91 4982 221358'
            ),
            Department(
                code='ADS',
                name='Artificial Intelligence and Data Science',
                hod_name='Dr. S. K. Nandha Kumar',
                contact_email='hodads@vjec.ac.in',
                location='Main Academic Block, 2nd Floor',
                phone='+91 4982 221359'
            ),
            Department(
                code='CSCY',
                name='Computer Science and Cyber Security',
                hod_name='Dr. Reena Sharma',
                contact_email='hodcscy@vjec.ac.in',
                location='Main Academic Block, 4th Floor',
                phone='+91 4982 221360'
            )
        ]
        db.session.add_all(departments)
        db.session.flush()

        print("[SEED] Creating Demo Accounts...")
        # 1. Administrator: ADM2604 / Admin@123
        admin = User(
            login_id='ADM2604',
            name='Administrator',
            role='ADMINISTRATOR',
            department='General Administration',
            email='admin.complaints@vjec.ac.in',
            phone='+91 94951 00000',
            status='ACTIVE'
        )
        admin.set_password('Admin@123')

        # 2. Student 1: Theresa Binny / VML23EC040 / theresa@123
        student1 = User(
            login_id='VML23EC040',
            name='Theresa Binny',
            role='STUDENT',
            department='ECE',
            year_semester='4th Year',
            email='theresa.ec040@vjec.ac.in',
            phone='+91 98471 23456',
            status='ACTIVE'
        )
        student1.set_password('theresa@123')

        # 3. Student 2: Aneeta Ullas / VML23EC008 / Aneeta@123
        student2 = User(
            login_id='VML23EC008',
            name='Aneeta Ullas',
            role='STUDENT',
            department='ECE',
            year_semester='4th Year',
            email='aneeta.ec008@vjec.ac.in',
            phone='+91 98471 65432',
            status='ACTIVE'
        )
        student2.set_password('Aneeta@123')

        # 4. Faculty 1: Ms. Arya Thalakkat / VML23FT001 / Arya@123
        faculty1 = User(
            login_id='VML23FT001',
            name='Ms. Arya Thalakkat',
            role='FACULTY',
            department='ECE',
            year_semester=None,
            email='arya.thalakkat@vjec.ac.in',
            phone='+91 94471 11223',
            status='ACTIVE'
        )
        faculty1.set_password('Arya@123')

        # 5. Faculty 2: Ms. Aishwarya / VML23FT002 / Aishwarya@123
        faculty2 = User(
            login_id='VML23FT002',
            name='Ms. Aishwarya',
            role='FACULTY',
            department='ECE',
            year_semester=None,
            email='aishwarya.faculty@vjec.ac.in',
            phone='+91 94471 33445',
            status='ACTIVE'
        )
        faculty2.set_password('Aishwarya@123')

        # 6. Counsellor: Dr. Mathew Joseph / VML23CN001 / Mathew@123
        counsellor = User(
            login_id='VML23CN001',
            name='Dr. Mathew Joseph',
            role='COUNSELLOR',
            department='Student Counselling Cell',
            year_semester=None,
            email='counsellor@vjec.ac.in',
            phone='+91 94472 88990',
            status='ACTIVE'
        )
        counsellor.set_password('Mathew@123')

        db.session.add_all([admin, student1, student2, faculty1, faculty2, counsellor])
        db.session.flush()

        print("[SEED] Creating Realistic Demo Complaints for Theresa Binny and Aneeta Ullas...")
        now = datetime.utcnow()

        # Theresa's Complaints:
        # CMP 1: Theresa Binny - Microprocessor Lab Kit Malfunction (In Progress, ECE)
        c1 = Complaint(
            complaint_id='CMP-2026-101',
            student_id=student1.id,
            department_code='ECE',
            assigned_to_id=faculty1.id,
            category='Laboratory',
            priority='High',
            subject='Microprocessor Lab Kit Malfunction in Room 204',
            description='In the 8086 microprocessor laboratory bench 4, the dual power supply unit trips intermittently and the keyboard interface does not register inputs properly during lab hours.',
            is_anonymous=False,
            status='In Progress',
            created_at=now - timedelta(days=3, hours=4),
            updated_at=now - timedelta(hours=2)
        )
        db.session.add(c1)
        db.session.flush()

        # History for C1
        h1_1 = ComplaintHistory(
            complaint_id=c1.id,
            action_by_id=student1.id,
            action_by_name=student1.name,
            action_by_role='STUDENT',
            action='Complaint registered in portal',
            previous_status=None,
            new_status='Submitted',
            comments='Registered through Student Portal',
            created_at=now - timedelta(days=3, hours=4)
        )
        h1_2 = ComplaintHistory(
            complaint_id=c1.id,
            action_by_id=admin.id,
            action_by_name=admin.name,
            action_by_role='ADMINISTRATOR',
            action='Automated Routing & Faculty Assignment',
            previous_status='Submitted',
            new_status='Assigned',
            comments='Routed to ECE Department Faculty Ms. Arya Thalakkat',
            created_at=now - timedelta(days=2, hours=10)
        )
        h1_3 = ComplaintHistory(
            complaint_id=c1.id,
            action_by_id=faculty1.id,
            action_by_name=faculty1.name,
            action_by_role='FACULTY',
            action='Investigation Initiated',
            previous_status='Assigned',
            new_status='In Progress',
            comments='Lab technical staff assigned to inspect bench 4 power regulator and cable pins.',
            created_at=now - timedelta(days=1, hours=5)
        )
        db.session.add_all([h1_1, h1_2, h1_3])

        # Messages for C1
        m1_1 = ComplaintMessage(
            complaint_id=c1.id,
            sender_id=student1.id,
            sender_name=student1.name,
            sender_role='STUDENT',
            message='Respected Madam, bench 4 keypad failed again during the Thursday afternoon session. Please check if replacement trainer board is available.',
            created_at=now - timedelta(days=2, hours=8)
        )
        m1_2 = ComplaintMessage(
            complaint_id=c1.id,
            sender_id=faculty1.id,
            sender_name=faculty1.name,
            sender_role='FACULTY',
            message='Hello Theresa, the lab instructor Mr. Babu has taken the unit for capacitor checking. In the meantime, you may use bench 9.',
            created_at=now - timedelta(days=1, hours=4)
        )
        db.session.add_all([m1_1, m1_2])

        # CMP 2: Theresa Binny - Wi-Fi Signal in ECE Seminar Hall (Action Taken)
        c2 = Complaint(
            complaint_id='CMP-2026-102',
            student_id=student1.id,
            department_code='ECE',
            assigned_to_id=faculty1.id,
            category='IT/Internet',
            priority='Medium',
            subject='Campus Wi-Fi Signal Weakness near ECE Seminar Hall',
            description='Students attending technical symposium preparations cannot access the college intranet or research papers due to dead zones in the seminar hall rear rows.',
            is_anonymous=False,
            status='Action Taken',
            created_at=now - timedelta(days=5, hours=2),
            updated_at=now - timedelta(hours=6)
        )
        db.session.add(c2)
        db.session.flush()

        h2_1 = ComplaintHistory(
            complaint_id=c2.id,
            action_by_id=student1.id,
            action_by_name=student1.name,
            action_by_role='STUDENT',
            action='Complaint registered',
            previous_status=None,
            new_status='Submitted',
            comments='Filed by Theresa Binny',
            created_at=now - timedelta(days=5, hours=2)
        )
        h2_2 = ComplaintHistory(
            complaint_id=c2.id,
            action_by_id=faculty1.id,
            action_by_name=faculty1.name,
            action_by_role='FACULTY',
            action='Campus IT Team Notified',
            previous_status='Assigned',
            new_status='Action Taken',
            comments='Requested IT Cell to add an additional Aruba access point in Seminar Hall.',
            created_at=now - timedelta(hours=6)
        )
        db.session.add_all([h2_1, h2_2])

        # CMP 3: Theresa Binny - Projector not working (Resolved + Feedback)
        c3 = Complaint(
            complaint_id='CMP-2026-103',
            student_id=student1.id,
            department_code='ECE',
            assigned_to_id=faculty1.id,
            category='Infrastructure',
            priority='Critical',
            subject='Projector not working in S7 ECE Classroom B201',
            description='The ceiling mounted HDMI projector in classroom B201 is displaying color distortion and turns off automatically after 5 minutes.',
            is_anonymous=False,
            status='Resolved',
            resolution_details='Maintenance team replaced the faulty cooling fan and HDMI cable adapter. Verified working with full HD resolution.',
            created_at=now - timedelta(days=8),
            updated_at=now - timedelta(days=6),
            resolved_at=now - timedelta(days=6)
        )
        db.session.add(c3)
        db.session.flush()

        h3_1 = ComplaintHistory(
            complaint_id=c3.id,
            action_by_id=faculty1.id,
            action_by_name=faculty1.name,
            action_by_role='FACULTY',
            action='Resolution Completed',
            previous_status='In Progress',
            new_status='Resolved',
            comments='Maintenance completed successfully by hardware maintenance team.',
            created_at=now - timedelta(days=6)
        )
        db.session.add(h3_1)

        # Feedback for C3
        fb3 = Feedback(
            complaint_id=c3.id,
            student_id=student1.id,
            rating=5,
            resolution_satisfaction='Highly Satisfied',
            comments='Prompt resolution within 24 hours. The classroom projector is functioning smoothly now. Thank you Ms. Arya!',
            created_at=now - timedelta(days=5)
        )
        db.session.add(fb3)

        # CMP 4: Theresa Binny - Library Digital Access (Submitted / Under Review)
        c4 = Complaint(
            complaint_id='CMP-2026-104',
            student_id=student1.id,
            department_code='ECE',
            assigned_to_id=None,
            category='Library',
            priority='Low',
            subject='IEEE Xplore Remote Access Credentials Expired',
            description='Remote institutional access login for final year IEEE digital library papers shows subscription expired error.',
            is_anonymous=False,
            status='Under Review',
            created_at=now - timedelta(hours=14),
            updated_at=now - timedelta(hours=14)
        )
        db.session.add(c4)

        # Aneeta Ullas Complaints (MUST NOT BE VISIBLE TO THERESA!):
        # CMP 5: Aneeta Ullas - College Bus Route 14 Delay
        c5 = Complaint(
            complaint_id='CMP-2026-201',
            student_id=student2.id,
            department_code='ECE',
            assigned_to_id=faculty2.id,
            category='Transportation',
            priority='Medium',
            subject='College Bus Route 14 Frequent Delay at Taliparamba Stop',
            description='Bus Route 14 arrives 15-20 minutes late repeatedly due to route modification, causing students to miss the morning 8:45 AM attendance bell.',
            is_anonymous=False,
            status='Under Review',
            created_at=now - timedelta(days=2, hours=3),
            updated_at=now - timedelta(days=1)
        )
        db.session.add(c5)

        # CMP 6: Aneeta Ullas - Anonymous Hostel Complaint
        c6 = Complaint(
            complaint_id='CMP-2026-202',
            student_id=student2.id,
            department_code='ECE',
            assigned_to_id=faculty2.id,
            category='Hostel',
            priority='High',
            subject='Sanitary Water Quality and Geyser Heating in Ladies Hostel 2nd Floor',
            description='Water pressure in the 2nd floor east wing bathrooms is very low and solar geyser is not functioning in the mornings.',
            is_anonymous=True,  # ANONYMOUS OPTION!
            status='In Progress',
            created_at=now - timedelta(days=4),
            updated_at=now - timedelta(days=1)
        )
        db.session.add(c6)
        db.session.flush()

        h6_1 = ComplaintHistory(
            complaint_id=c6.id,
            action_by_id=student2.id,
            action_by_name='Anonymous Student',
            action_by_role='STUDENT',
            action='Anonymous Complaint submitted',
            previous_status=None,
            new_status='Submitted',
            comments='Submitted anonymously with high priority',
            created_at=now - timedelta(days=4)
        )
        h6_2 = ComplaintHistory(
            complaint_id=c6.id,
            action_by_id=faculty2.id,
            action_by_name=faculty2.name,
            action_by_role='FACULTY',
            action='Hostel Warden Contacted',
            previous_status='Assigned',
            new_status='In Progress',
            comments='Forwarded plumber inspection request to Ladies Hostel resident warden.',
            created_at=now - timedelta(days=2)
        )
        db.session.add_all([h6_1, h6_2])

        print("[SEED] Creating Counselling Appointments...")
        # Appointment 1 for Theresa (Confirmed)
        apt1 = CounsellingAppointment(
            appointment_id='APT-2026-001',
            student_id=student1.id,
            counsellor_id=counsellor.id,
            preferred_date=(datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
            preferred_time='03:30 PM',
            reason='Academic workload balance and campus placement interview stress',
            confidential_note='Requesting one-on-one session to structure preparation time for upcoming technical assessments.',
            status='Confirmed',
            confirmed_date=(datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
            confirmed_time='03:30 PM',
            venue='Student Counselling Cell, Main Block Room 204',
            counsellor_notes='Appointment confirmed. Student advised to bring academic timetable.'
        )

        # Appointment 2 for Aneeta (Requested)
        apt2 = CounsellingAppointment(
            appointment_id='APT-2026-002',
            student_id=student2.id,
            counsellor_id=counsellor.id,
            preferred_date=(datetime.now() + timedelta(days=4)).strftime('%Y-%m-%d'),
            preferred_time='11:00 AM',
            reason='Career guidance regarding higher studies vs campus placement opportunities',
            confidential_note='Need advice on GATE exam preparation timeline.',
            status='Requested'
        )
        db.session.add_all([apt1, apt2])

        print("[SEED] Creating Anti-Ragging Demo Record...")
        arg1 = AntiRaggingComplaint(
            report_id='ARG-2026-001',
            student_id=student1.id,
            is_anonymous=True,
            complainant_name='Confidential Student',
            contact_info='Confidential (Protected in System)',
            incident_category='Hostelite Harassment / Intimidation',
            description='Senior students gathered near the open sports stadium pavilion at 8:30 PM demanding junior students perform unauthorized roll calls.',
            incident_date=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            location='Campus Sports Complex / Stadium Pathway',
            is_emergency=False,
            status='Action Taken',
            investigation_notes='Anti-ragging flying squad dispatched at 9:00 PM. Increased night security patrol stationed at stadium corridor.',
            action_taken='Disciplinary committee summoned students involved, formal warnings issued, and night wardens instructed to lock ground gate after 7:30 PM.'
        )
        db.session.add(arg1)

        print("[SEED] Creating Visitor Support Demo Record...")
        vis1 = VisitorRequest(
            request_id='VIS-2026-001',
            visitor_name='Mr. Rajesh Nair',
            contact_phone='+91 94470 55432',
            contact_email='rajesh.nair.kannur@gmail.com',
            purpose='Parent Admission Inquiry',
            department='ADS',
            query_text='Seeking curriculum information and lab infrastructure visit for BTech Artificial Intelligence and Data Science admission.',
            visit_date=(datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
            status='Responded',
            admin_response='Admission office will arrange department tour and meet HOD on arrival at Main Block Admin Office.'
        )
        vis2 = VisitorRequest(
            request_id='VIS-2026-002',
            visitor_name='Dr. K. S. Radhakrishnan',
            contact_phone='+91 98460 12399',
            contact_email='radhakrishnan.guest@ieee.org',
            purpose='Guest Lecture / Industry Expert',
            department='ECE',
            query_text='Verification of guest house booking and audio-visual equipment setup in ECE Conference Hall.',
            visit_date=(datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            status='Pending'
        )
        db.session.add_all([vis1, vis2])

        print("[SEED] Adding Demo Notifications...")
        n1 = Notification(
            user_id=student1.id,
            title='Complaint Status Updated: CMP-2026-101',
            message='Your complaint regarding Microprocessor Lab Kit is now "In Progress". Ms. Arya Thalakkat has updated the action log.',
            link='/student/complaints/CMP-2026-101',
            category='complaint',
            is_read=False
        )
        n2 = Notification(
            user_id=student1.id,
            title='Counselling Appointment Confirmed',
            message='Dr. Mathew Joseph has confirmed your session on ' + apt1.confirmed_date + ' at ' + apt1.confirmed_time + '.',
            link='/student/counselling',
            category='counselling',
            is_read=False
        )
        n3 = Notification(
            user_id=student1.id,
            title='Complaint Resolved: CMP-2026-103',
            message='Classroom Projector complaint has been resolved. Please provide your valuable feedback.',
            link='/student/feedback/' + c3.complaint_id,
            category='feedback',
            is_read=True
        )
        n4 = Notification(
            user_id=faculty1.id,
            title='New Complaint Assigned: CMP-2026-101',
            message='A High-priority laboratory complaint from ECE department has been routed to you.',
            link='/faculty/complaints/CMP-2026-101',
            category='complaint',
            is_read=False
        )
        n5 = Notification(
            user_id=counsellor.id,
            title='New Counselling Request: APT-2026-002',
            message='Student Aneeta Ullas has requested a counselling appointment for career guidance.',
            link='/counsellor/appointments',
            category='counselling',
            is_read=False
        )
        n6 = Notification(
            user_id=admin.id,
            title='Anti-Ragging Incident Resolved',
            message='Action taken for incident report ARG-2026-001 by Anti-Ragging Cell.',
            link='/admin/anti-ragging',
            category='system',
            is_read=False
        )
        db.session.add_all([n1, n2, n3, n4, n5, n6])

        print("[SEED] Adding Audit Logs...")
        logs = [
            AuditLog(
                user_id=admin.id,
                user_name='Administrator',
                user_role='ADMINISTRATOR',
                action='System Initialization',
                details='Database seeded with VJEC departments, demo credentials, and active workflow models.'
            ),
            AuditLog(
                user_id=student1.id,
                user_name='Theresa Binny',
                user_role='STUDENT',
                action='Complaint Submission',
                details='Submitted complaint CMP-2026-101 (Microprocessor Lab Kit Malfunction)'
            ),
            AuditLog(
                user_id=faculty1.id,
                user_name='Ms. Arya Thalakkat',
                user_role='FACULTY',
                action='Status Change',
                details='Changed status of CMP-2026-101 from Assigned to In Progress'
            )
        ]
        db.session.add_all(logs)

        # System Settings
        settings = [
            SystemSetting(key='college_name', value='Vimal Jyothi Engineering College', description='Official institution name'),
            SystemSetting(key='portal_version', value='2.4.0 (2026 BTech Final Year Edition)', description='Portal build version'),
            SystemSetting(key='anti_ragging_helpline', value='1800-180-5522 / +91 94471 22334', description='Toll-free anti-ragging contact'),
            SystemSetting(key='counselling_cell_contact', value='counsellor@vjec.ac.in | Room 204 Main Block', description='Campus counselling centre location'),
            SystemSetting(key='anonymous_complaints_allowed', value='true', description='Allow students to file anonymous complaints')
        ]
        db.session.add_all(settings)

        db.session.commit()
        print("[SEED] Successfully seeded database with all official VJEC demo accounts and data!")

if __name__ == '__main__':
    seed_database()
