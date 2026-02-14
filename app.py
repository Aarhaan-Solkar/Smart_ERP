import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

# --- App Initialization ---
app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Data Loading ---
# --- Data Loading ---
def load_data():
    """Loads user, student, and faculty data."""
    try:
        with open('students.json', 'r') as f:
            students_data = json.load(f)
    except FileNotFoundError:
        students_data = []

    # Admin User
    users_data = {
        "admin": {"password": generate_password_hash("adminpassword"), "role": "admin"}
    }

    # Faculty Users (NEW)
    faculty_users = {
        "faculty_cs": {"password": generate_password_hash("cs_pass"), "role": "faculty", "department": "Computer Science"},
        "faculty_mech": {"password": generate_password_hash("mech_pass"), "role": "faculty", "department": "Mechanical"},
        "faculty_extc": {"password": generate_password_hash("extc_pass"), "role": "faculty", "department": "EXTC"},
        "faculty_it": {"password": generate_password_hash("it_pass"), "role": "faculty", "department": "IT"},
        "faculty_civil": {"password": generate_password_hash("civil_pass"), "role": "faculty", "department": "Civil"},
    }
    users_data.update(faculty_users) # Add faculty users to the main users dictionary

    # Student Users
    for student in students_data:
        users_data[student['username']] = { "password": generate_password_hash("password"), "role": "student" }
    
    return users_data, students_data

users, students = load_data()
print(f"Loaded {len(students)} student records from students.json.")

# --- Eligibility Logic ---
def check_eligibility(student):
    year_str = student.get('year', '').lower()
    y1_ext, y1_int = student.get('kts_y1_ext', 0), student.get('kts_y1_int', 0)
    y2_ext, y2_int = student.get('kts_y2_ext', 0), student.get('kts_y2_int', 0)
    y3_ext, y3_int = student.get('kts_y3_ext', 0), student.get('kts_y3_int', 0)

    if 'first' in year_str:
        if y1_ext > 5 or y1_int > 3 or (y1_ext + y1_int) > 8: return "Not Eligible"
        return "Eligible"
    elif 'second' in year_str:
        if y1_ext > 0 or y1_int > 0: return "Not Eligible"
        if y2_ext > 5 or y2_int > 3 or (y2_ext + y2_int) > 8: return "Not Eligible"
        return "Eligible"
    elif 'third' in year_str:
        if y1_ext > 0 or y1_int > 0 or y2_ext > 0 or y2_int > 0: return "Not Eligible"
        if y3_ext > 5 or y3_int > 3 or (y3_ext + y3_int) > 8: return "Not Eligible"
        return "Eligible"
    elif 'final' in year_str or 'fourth' in year_str:
         if y1_ext > 0 or y1_int > 0 or y2_ext > 0 or y2_int > 0 or y3_ext > 0 or y3_int > 0: return "Not Eligible"
         return "Eligible"
    return "Status Unknown"

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        # MODIFIED: Redirect based on role already in session
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session.get('role') == 'faculty':
            return redirect(url_for('faculty_dashboard'))
        else: # Student
            return redirect(url_for('student_dashboard'))
            
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['role'] = user['role']
            
            # --- NEW LOGIC FOR FACULTY ---
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'faculty':
                session['department'] = user['department'] # Store department in session
                return redirect(url_for('faculty_dashboard'))
            else: # Student
                return redirect(url_for('student_dashboard'))
            # --- END OF NEW LOGIC ---

        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' not in session or session.get('role') != 'admin': return redirect(url_for('login'))
    
    overall_eligibility = {'Eligible': 0, 'Not Eligible': 0}
    department_distribution = {}
    department_eligibility = {}

    for student in students:
        status = check_eligibility(student)
        is_eligible = 'Not Eligible' not in status
        overall_eligibility['Eligible' if is_eligible else 'Not Eligible'] += 1
        dept = student.get('department', 'Unknown')
        department_distribution[dept] = department_distribution.get(dept, 0) + 1
        if dept not in department_eligibility:
            department_eligibility[dept] = {'Eligible': 0, 'Not Eligible': 0}
        department_eligibility[dept]['Eligible' if is_eligible else 'Not Eligible'] += 1

    search_query = request.args.get('search', '').lower()
    search_results = []
    if search_query:
        filtered_students = [s for s in students if search_query in s['full_name'].lower()]
        search_results = [{'student': s, 'status': check_eligibility(s)} for s in filtered_students]

    return render_template(
        'admin_dashboard.html', search_query=search_query, search_results=search_results,
        overall_eligibility_labels=list(overall_eligibility.keys()), overall_eligibility_data=list(overall_eligibility.values()),
        department_dist_labels=list(department_distribution.keys()), department_dist_data=list(department_distribution.values()),
        department_eligibility_data=department_eligibility
    )

@app.route('/faculty_dashboard')
def faculty_dashboard():
    # Security check: Ensure user is a logged-in faculty member
    if 'username' not in session or session.get('role') != 'faculty':
        return redirect(url_for('login'))
    
    # Get the faculty's department from the session
    faculty_department = session.get('department', 'Unknown')
    
    # Filter students to only include those from the faculty's department
    department_students = [s for s in students if s.get('department') == faculty_department]

    # --- Calculate statistics ONLY for the filtered students ---
    eligibility_counts = {'Eligible': 0, 'Not Eligible': 0}
    year_distribution = {}

    for student in department_students:
        status = check_eligibility(student)
        is_eligible = 'Not Eligible' not in status
        
        eligibility_counts['Eligible' if is_eligible else 'Not Eligible'] += 1
        
        year = student.get('year', 'Unknown')
        year_distribution[year] = year_distribution.get(year, 0) + 1

    # --- Handle server-side search (as a fallback) ---
    search_query = request.args.get('search', '').lower()
    search_results = []
    if search_query:
        # This part will now primarily be for non-JS users or direct links
        filtered_students_for_search = [s for s in department_students if search_query in s['full_name'].lower()]
        search_results = [{'student': s, 'status': check_eligibility(s)} for s in filtered_students_for_search]

    return render_template(
        'faculty_dashboard.html',
        department=faculty_department,
        # MODIFIED: Pass the full list of students to the template
        all_department_students=[{'student': s, 'status': check_eligibility(s)} for s in department_students],
        search_query=search_query,
        search_results=search_results, # We can keep this for fallback
        eligibility_labels=list(eligibility_counts.keys()),
        eligibility_data=list(eligibility_counts.values()),
        year_dist_labels=list(year_distribution.keys()),
        year_dist_data=list(year_distribution.values()),
        total_students=len(department_students),
        eligible_count=eligibility_counts.get('Eligible', 0),
        not_eligible_count=eligibility_counts.get('Not Eligible', 0)
    )

@app.route('/student_dashboard')
def student_dashboard():
    if 'username' not in session or session.get('role') != 'student': return redirect(url_for('login'))
    
    student_data = next((s for s in students if s['username'] == session['username']), None)
    
    if student_data:
        eligibility_status = check_eligibility(student_data)
        total_kts = student_data.get('kts_y1_ext', 0) + student_data.get('kts_y1_int', 0) + \
                    student_data.get('kts_y2_ext', 0) + student_data.get('kts_y2_int', 0) + \
                    student_data.get('kts_y3_ext', 0) + student_data.get('kts_y3_int', 0)
    else:
        eligibility_status = "N/A"
        total_kts = "N/A"

    # Dummy data for charts
    attendance_data = {'labels': ["Jan", "Feb", "Mar", "Apr", "May", "Jun"], 'data': [92, 88, 95, 85, 91, 89]}
    gpa_data = {'labels': ["Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6"], 'data': [7.8, 8.2, 8.0, 8.5, 8.3, 8.8]}

    return render_template(
        'student_dashboard.html', 
        student_data=student_data,
        eligibility_status=eligibility_status,
        total_kts=total_kts,
        attendance_data=json.dumps(attendance_data),
        gpa_data=json.dumps(gpa_data)
    )

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)