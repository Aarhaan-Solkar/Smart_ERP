import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

# --- App Initialization ---
app = Flask(__name__)
app.secret_key = 'erp_system_secret_2026'

# --- Google Sheets Configuration ---
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    # Ensure this name matches your Google Sheet title exactly
    return client.open("Student_Database").sheet1

# --- Staff Credentials ---
STAFF_USERS = {
    "admin@erp.com": {"password": "admin123", "role": "admin"},
    "faculty@erp.com": {"password": "faculty456", "role": "faculty"}
}

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form.get('id_or_email')
        password = request.form.get('password')

        # 1. Check Staff
        if user_input in STAFF_USERS and STAFF_USERS[user_input]['password'] == password:
            session['user'] = user_input
            session['role'] = STAFF_USERS[user_input]['role']
            return redirect(url_for(f"{session['role']}_dashboard"))

        # 2. Check Student (Google Sheets)
        try:
            sheet = get_sheet()
            # Find Roll No in Column A
            cell = sheet.find(str(user_input))
            if cell:
                row_data = sheet.row_values(cell.row)
                # Password is in Column D (Index 3)
                if len(row_data) >= 4 and str(row_data[3]) == str(password):
                    session['user'] = user_input
                    session['role'] = 'student'
                    return redirect(url_for('student_dashboard'))
        except Exception as e:
            print(f"Login Error: {e}")

        flash('Invalid Credentials. Please try again.', 'danger')
            
    return render_template('login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
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

@app.route('/faculty/dashboard')
def faculty_dashboard():
    if session.get('role') != 'faculty':
        return redirect(url_for('login'))
    
    try:
        sheet = get_sheet()
        all_students = sheet.get_all_records()

        # --- Quick Stats ---
        total_students = len(all_students)
        gpas = [float(s['Current GPA']) for s in all_students]
        avg_gpa = round(sum(gpas)/total_students, 2)
        avg_att = round(sum(float(s['Attendance Average']) for s in all_students)/total_students, 1)
        kt_students_count = len([s for s in all_students if int(s['Number of KT']) > 0])

        # --- Students Requiring Attention (Logic: Attendance < 75% OR GPA < 5 OR KT > 0) ---
        attention_list = [s for s in all_students if float(s['Attendance Average']) < 75 or float(s['Current GPA']) < 5 or int(s['Number of KT']) > 0]

        # --- Chart Data ---
        subjects = ['BC', 'BDA', 'NLP', 'ML', 'MIS']
        sub_avgs = [round(sum(float(s[sub]) for s in all_students)/total_students, 2) for sub in subjects]

        return render_template('faculty_dashboard.html', 
                               students=all_students[:15], # Showing 15 for Faculty
                               attention_students=attention_list[:5], # Top 5 at-risk
                               total=total_students,
                               avg_gpa=avg_gpa,
                               avg_att=avg_att,
                               kt_count=kt_students_count,
                               sub_labels=subjects,
                               sub_data=sub_avgs)
    except Exception as e:
        return f"Faculty Portal Error: {e}"

@app.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    
    try:
        sheet = get_sheet()
        roll_no = session.get('user')
        # Find student row
        cell = sheet.find(str(roll_no))
        student_data = sheet.row_values(cell.row)
        
        # Mapping based on your Google Sheet structure
        # Column A=Roll(0), B=Name(1), C=Email(2), D=Pass(3), E=Att(4), F=BC(5), G=BDA(6), H=NLP(7), I=ML(8), J=MIS(9), K=GPA(10), L=KT(11)
        student = {
            "name": student_data[1],
            "roll": student_data[0],
            "attendance": float(student_data[4]),
            "gpa": float(student_data[10]),
            "total_kt": int(student_data[11]),
            "marks": {
                "BC": int(student_data[5]),
                "BDA": int(student_data[6]),
                "NLP": int(student_data[7]),
                "ML": int(student_data[8]),
                "MIS": int(student_data[9])
            }
        }

        # Calculate Academic Status
        if student['gpa'] >= 8 and student['attendance'] >= 80:
            status = "Excellent"
        elif student['gpa'] >= 5 and student['attendance'] >= 75:
            status = "Good"
        else:
            status = "At Risk"

        # Identify Internal KTs (Marks < 7)
        internal_kts = {sub: mark for sub, mark in student['marks'].items() if mark < 7}

        return render_template('student_dashboard.html', 
                               s=student, 
                               status=status, 
                               internal_kts=internal_kts)
    except Exception as e:
        return f"Student Portal Error: {e}"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)