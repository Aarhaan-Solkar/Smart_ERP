from flask import Flask, render_template, request, redirect, url_for, flash, session
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
from email.mime.text import MIMEText
from flask import jsonify
import traceback

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
    
    try:
        sheet = get_sheet()
        all_students = sheet.get_all_records()
        display_students = all_students[:52]

        # --- Calculate Quick Stats ---
        total_count = len(all_students)
        
        # 1. Average GPA
        gpas = [float(s['Current GPA']) for s in all_students if str(s['Current GPA']).replace('.','',1).isdigit()]
        avg_gpa = round(sum(gpas)/len(gpas), 2) if gpas else 0
        
        # 2. Class Attendance Average
        atts = [float(s['Attendance Average']) for s in all_students if str(s['Attendance Average']).replace('.','',1).isdigit()]
        avg_att = round(sum(atts)/len(atts), 1) if atts else 0
        
        # 3. Defaulter Count (Attendance < 75%)
        defaulters = len([s for s in all_students if float(s['Attendance Average']) < 75])

        # --- Analytics Charts (Same as before) ---
        subjects = ['BC', 'BDA', 'NLP', 'ML', 'MIS']
        sub_avgs = [round(sum(float(s[sub]) for s in all_students if str(s[sub]).isdigit())/total_count, 2) for sub in subjects]

        ranges = {"<60%": 0, "60-75%": 0, "75-90%": 0, "90%+": 0}
        for s in all_students:
            val = float(s['Attendance Average'])
            if val < 60: ranges["<60%"] += 1
            elif val < 75: ranges["60-75%"] += 1
            elif val < 90: ranges["75-90%"] += 1
            else: ranges["90%+"] += 1

        return render_template('admin_dashboard.html', 
                               students=display_students,
                               total_students=total_count,
                               avg_gpa=avg_gpa,
                               avg_att=avg_att,
                               defaulters=defaulters,
                               att_labels=list(ranges.keys()),
                               att_values=list(ranges.values()),
                               sub_labels=subjects,
                               sub_data=sub_avgs)
    except Exception as e:
        print("FULL ERROR:", traceback.format_exc())  # shows in terminal
        return f"<pre>{traceback.format_exc()}</pre>"

@app.route('/send-defaulter-email', methods=['POST'])
def send_defaulter_email():
    if session.get('role') != 'admin':
        return jsonify({"message": "Unauthorized"}), 403

    data = request.get_json()
    student_email = data.get('email')
    parent_email = data.get('parent_email')
    name = data.get('name')

    sender_email = "solkaraarhaan@gmail.com"
    sender_password = "bkph wqdy mdzi rsfp"

    subject = "⚠️ Defaulter Notice - Attendance Shortage"
    body = f"""
    Dear {name} and Parent,

    This is to inform you that {name} has been marked as a DEFAULTER due to attendance below 75%.

    📌 Immediate action is required:
    Please contact the Class Coordinator and complete the necessary formalities.

    This may affect academic eligibility if ignored.

    Regards,  
    Prof. Sayali Karmode  
    """

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = f"{student_email}, {parent_email}"

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return jsonify({"message": f"Email sent to {name}"})

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"})

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