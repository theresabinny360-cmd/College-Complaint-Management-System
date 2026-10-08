import unittest
from app import create_app
from models import db, User, Complaint, CounsellingAppointment, AntiRaggingComplaint, VisitorRequest, Feedback

class VJECComplaintSystemTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_homepage_designation_selection(self):
        """Test homepage loads first interface with 4 designations"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Vimal Jyothi Engineering College', response.data)
        self.assertIn(b'College Complaint Management System', response.data)
        self.assertIn(b'STUDENT', response.data)
        self.assertIn(b'FACULTY', response.data)
        self.assertIn(b'COUNSELLOR', response.data)
        self.assertIn(b'ADMINISTRATOR', response.data)
        print("[PASS] Test 1: Homepage designation selection screen verified")

    def test_02_all_role_logins(self):
        """Test authentication for all demo accounts"""
        # Student 1: Theresa Binny
        resp = self.client.post('/login', data={
            'login_id': 'VML23EC040',
            'password': 'theresa@123',
            'designation': 'STUDENT'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Theresa Binny', resp.data)

        # Logout
        self.client.get('/logout')

        # Faculty 1: Ms. Arya Thalakkat
        resp = self.client.post('/login', data={
            'login_id': 'VML23FT001',
            'password': 'Arya@123',
            'designation': 'FACULTY'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Arya Thalakkat', resp.data)

        self.client.get('/logout')

        # Counsellor: Dr. Mathew Joseph
        resp = self.client.post('/login', data={
            'login_id': 'VML23CN001',
            'password': 'Mathew@123',
            'designation': 'COUNSELLOR'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Mathew Joseph', resp.data)

        self.client.get('/logout')

        # Administrator: ADM2604
        resp = self.client.post('/login', data={
            'login_id': 'ADM2604',
            'password': 'Admin@123',
            'designation': 'ADMINISTRATOR'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Institutional System Control', resp.data)

        self.client.get('/logout')
        print("[PASS] Test 2: All 4 role logins successfully verified")

    def test_03_role_mismatch_and_invalid_login(self):
        """Test that role mismatch and wrong password are rejected"""
        # Student trying to login as FACULTY
        resp = self.client.post('/login', data={
            'login_id': 'VML23EC040',
            'password': 'theresa@123',
            'designation': 'FACULTY'
        }, follow_redirects=True)
        self.assertIn(b'Designation mismatch', resp.data)

        # Wrong password
        resp = self.client.post('/login', data={
            'login_id': 'VML23EC040',
            'password': 'wrongpassword',
            'designation': 'STUDENT'
        }, follow_redirects=True)
        self.assertIn(b'Invalid Login ID or Password', resp.data)
        print("[PASS] Test 3: Role mismatch and invalid password rejection verified")

    def test_04_strict_privacy_rule(self):
        """Crucial Requirement 33: Theresa CANNOT access Aneeta's complaints"""
        with self.app.app_context():
            theresa = User.query.filter_by(login_id='VML23EC040').first()
            aneeta = User.query.filter_by(login_id='VML23EC008').first()
            aneeta_complaint = Complaint.query.filter_by(student_id=aneeta.id).first()

        # Login as Theresa
        self.client.post('/login', data={
            'login_id': 'VML23EC040',
            'password': 'theresa@123',
            'designation': 'STUDENT'
        }, follow_redirects=True)

        # Theresa tries to access Aneeta's complaint directly by URL
        resp = self.client.get(f'/student/complaints/{aneeta_complaint.complaint_id}')
        # Must return 403 Forbidden!
        self.assertEqual(resp.status_code, 403)
        self.assertIn(b'403', resp.data)
        self.assertIn(b'Access Denied', resp.data)

        # Theresa's "My Complaints" list does NOT contain Aneeta's complaint
        resp = self.client.get('/student/my-complaints')
        self.assertNotIn(aneeta_complaint.subject.encode(), resp.data)

        self.client.get('/logout')
        print("[PASS] Test 4: Strict complaint privacy verified (403 on unauthorized access)")

    def test_05_complaint_registration_and_conversation(self):
        """Test student submitting a complaint and adding to conversation"""
        # Login as Theresa
        self.client.post('/login', data={
            'login_id': 'VML23EC040',
            'password': 'theresa@123',
            'designation': 'STUDENT'
        }, follow_redirects=True)

        # Submit new complaint
        resp = self.client.post('/student/complaints/new', data={
            'category': 'Academic',
            'department_code': 'ECE',
            'priority': 'Medium',
            'subject': 'Digital Signal Processing Reference Books in Library',
            'description': 'The recommended textbook Oppenheim Discrete-Time Signal Processing has only 2 copies available for 60 students in S7 ECE.',
            'is_anonymous': 'on'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Complaint registered successfully', resp.data)

        with self.app.app_context():
            new_c = Complaint.query.filter_by(subject='Digital Signal Processing Reference Books in Library').first()
            self.assertIsNotNone(new_c)
            self.assertTrue(new_c.is_anonymous)
            complaint_id = new_c.complaint_id

        # Post update in conversation
        resp = self.client.post(f'/student/complaints/{complaint_id}', data={
            'message': 'Subject teacher Prof. Ramesh also recommended having additional e-copies.'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Your update has been added', resp.data)

        self.client.get('/logout')
        print("[PASS] Test 5: Complaint registration and conversation message verified")

    def test_06_counselling_booking_and_confirmation(self):
        """Test student booking counselling and counsellor confirming"""
        # 1. Student books appointment
        self.client.post('/login', data={
            'login_id': 'VML23EC008',
            'password': 'Aneeta@123',
            'designation': 'STUDENT'
        }, follow_redirects=True)

        with self.app.app_context():
            counsellor = User.query.filter_by(role='COUNSELLOR').first()

        resp = self.client.post('/student/counselling', data={
            'counsellor_id': counsellor.id,
            'preferred_date': '2026-10-15',
            'preferred_time': '02:00 PM',
            'reason': 'Stress management before semester laboratory exam',
            'confidential_note': 'Would like tips on balancing project submissions'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Counselling appointment requested successfully', resp.data)

        with self.app.app_context():
            apt = CounsellingAppointment.query.filter_by(reason='Stress management before semester laboratory exam').first()
            self.assertIsNotNone(apt)
            apt_id = apt.appointment_id

        self.client.get('/logout')

        # 2. Counsellor confirms appointment
        self.client.post('/login', data={
            'login_id': 'VML23CN001',
            'password': 'Mathew@123',
            'designation': 'COUNSELLOR'
        }, follow_redirects=True)

        resp = self.client.post('/counsellor/appointments', data={
            'action': 'confirm',
            'appointment_id': apt_id,
            'confirmed_date': '2026-10-15',
            'confirmed_time': '02:00 PM',
            'venue': 'Student Counselling Cell Room 204',
            'notes': 'Confirmed. Please feel free to bring any questions.'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'confirmed', resp.data)

        self.client.get('/logout')
        print("[PASS] Test 6: Counselling booking and counsellor confirmation verified")

    def test_07_visitor_support_and_anti_ragging(self):
        """Test public visitor support submission and anti-ragging reporting"""
        # Visitor support (public)
        resp = self.client.post('/visitor-support', data={
            'visitor_name': 'Prof. Dr. V. Narayanan',
            'contact_phone': '+91 94470 99887',
            'contact_email': 'narayanan.guest@gmail.com',
            'purpose': 'Technical Symposium / Conference',
            'department': 'ECE',
            'query': 'Keynote speaker for IEEE International Conference arriving Friday morning.',
            'visit_date': '2026-10-20'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Your visitor request has been logged', resp.data)

        # Anti-ragging by student
        self.client.post('/login', data={
            'login_id': 'VML23EC040',
            'password': 'theresa@123',
            'designation': 'STUDENT'
        }, follow_redirects=True)

        resp = self.client.post('/student/anti-ragging', data={
            'incident_category': 'Verbal Harassment / Humiliation',
            'description': 'Loud chanting and unapproved group assembly near canteen porch at 7:00 PM.',
            'incident_date': '2026-10-05',
            'location': 'Canteen Porch',
            'is_anonymous': 'on'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Anti-Ragging complaint submitted confidentially', resp.data)

        self.client.get('/logout')
        print("[PASS] Test 7: Visitor support and anti-ragging submission verified")

    def test_08_administrator_management_and_override(self):
        """Test admin dashboard, overriding status, and department control"""
        self.client.post('/login', data={
            'login_id': 'ADM2604',
            'password': 'Admin@123',
            'designation': 'ADMINISTRATOR'
        }, follow_redirects=True)

        resp = self.client.get('/admin/dashboard')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Institutional System Control', resp.data)

        # Admin view all users
        resp = self.client.get('/admin/users')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Theresa Binny', resp.data)
        self.assertIn(b'ADM2604', resp.data)

        # Admin view 10 departments
        resp = self.client.get('/admin/departments')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'ECE', resp.data)
        self.assertIn(b'CSE', resp.data)
        self.assertIn(b'CSCY', resp.data)

        # Admin override complaint status
        resp = self.client.post('/admin/complaints/CMP-2026-101', data={
            'action_type': 'admin_update',
            'status': 'Action Taken',
            'priority': 'Critical',
            'category': 'Laboratory',
            'remarks': 'Principal inspected ECE lab; component ordered via urgent procurement.'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'updated successfully', resp.data)

        self.client.get('/logout')
        print("[PASS] Test 8: Administrator management and supervisory override verified")

if __name__ == '__main__':
    unittest.main()
