from app import create_app
from models import User

app = create_app()
app.config['TESTING'] = True
client = app.test_client()

routes_to_test = [
    ('/', 200, None),
    ('/login', 200, None),
    ('/register', 200, None),
    ('/visitor-support', 200, None),
    ('/student/dashboard', 200, ('VML23EC040', 'theresa@123', 'STUDENT')),
    ('/student/complaints/new', 200, ('VML23EC040', 'theresa@123', 'STUDENT')),
    ('/student/my-complaints', 200, ('VML23EC040', 'theresa@123', 'STUDENT')),
    ('/student/track', 200, ('VML23EC040', 'theresa@123', 'STUDENT')),
    ('/student/counselling', 200, ('VML23EC040', 'theresa@123', 'STUDENT')),
    ('/student/anti-ragging', 200, ('VML23EC040', 'theresa@123', 'STUDENT')),
    ('/student/campus-navigation', 200, ('VML23EC040', 'theresa@123', 'STUDENT')),
    ('/student/notifications', 200, ('VML23EC040', 'theresa@123', 'STUDENT')),
    ('/student/profile', 200, ('VML23EC040', 'theresa@123', 'STUDENT')),
    ('/faculty/dashboard', 200, ('VML23FT001', 'Arya@123', 'FACULTY')),
    ('/faculty/complaints', 200, ('VML23FT001', 'Arya@123', 'FACULTY')),
    ('/faculty/feedback', 200, ('VML23FT001', 'Arya@123', 'FACULTY')),
    ('/faculty/notifications', 200, ('VML23FT001', 'Arya@123', 'FACULTY')),
    ('/faculty/profile', 200, ('VML23FT001', 'Arya@123', 'FACULTY')),
    ('/counsellor/dashboard', 200, ('VML23CN001', 'Mathew@123', 'COUNSELLOR')),
    ('/counsellor/appointments', 200, ('VML23CN001', 'Mathew@123', 'COUNSELLOR')),
    ('/counsellor/complaints', 200, ('VML23CN001', 'Mathew@123', 'COUNSELLOR')),
    ('/counsellor/notifications', 200, ('VML23CN001', 'Mathew@123', 'COUNSELLOR')),
    ('/counsellor/profile', 200, ('VML23CN001', 'Mathew@123', 'COUNSELLOR')),
    ('/admin/dashboard', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/users', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/users/new', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/departments', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/complaints', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/anti-ragging', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/counselling', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/feedback', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/visitor-support', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/system_activity', 404, None), # testing 404
    ('/admin/system-activity', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/reports', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/settings', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
    ('/admin/notifications', 200, ('ADM2604', 'Admin@123', 'ADMINISTRATOR')),
]

print("Starting Full Route Audit...")
all_passed = True
for path, expected_status, auth in routes_to_test:
    client.get('/logout')
    if auth:
        login_id, password, desig = auth
        client.post('/login', data={'login_id': login_id, 'password': password, 'designation': desig})
    resp = client.get(path)
    if resp.status_code == expected_status:
        print(f"[PASS] {path} -> {resp.status_code}")
    else:
        print(f"[FAIL] {path} -> Got {resp.status_code}, expected {expected_status}")
        all_passed = False

if all_passed:
    print("\nALL 36 CRITICAL ROUTES PASSED WITH 100% SUCCESS!")
else:
    print("\nSome routes failed.")
