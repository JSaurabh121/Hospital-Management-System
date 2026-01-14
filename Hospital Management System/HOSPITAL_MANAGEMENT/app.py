# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from extensions import db
from model import User, Department, Doctor, Appointment, Treatment
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "secret_key"

db.init_app(app)


# ------------------------------------------------
# BASIC PAGES
# ------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')


# ------------------------------------------------
# REGISTRATION / LOGIN
# ------------------------------------------------
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if password != confirm:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('registration'))

        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "warning")
            return redirect(url_for('registration'))

        new_user = User(
            username=username,
            email=email,
            password=password,
            role="patient",
            registration_date=datetime.now()
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful!", "success")
        return redirect(url_for('login'))

    return render_template('registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            session['id'] = user.id
            session['role'] = user.role

            if user.role == "admin":
                return redirect(url_for('admin_dashboard'))
            elif user.role == "doctor":
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))

        flash("Invalid login", "danger")
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for('login'))


# ------------------------------------------------
# PATIENT DASHBOARD
# ------------------------------------------------
@app.route('/patient_dashboard')
def patient_dashboard():
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    patient = User.query.get_or_404(session['id'])
    departments = Department.query.all()

    upcoming = Appointment.query.filter_by(
        patient_id=patient.id, status="booked"
    ).all()

    cancelled = Appointment.query.filter_by(
        patient_id=patient.id, status="cancelled"
    ).all()

    return render_template(
        "patient_dashboard.html",
        patient=patient,
        departments=departments,
        upcoming_appointments=upcoming,
        cancelled_appointments=cancelled
    )


# CANCEL APPOINTMENT – FIXED (GET allowed)
@app.route('/cancel_appointment/<int:appt_id>')
def cancel_appointment(appt_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != session['id']:
        flash("Not allowed!", "danger")
        return redirect(url_for('patient_dashboard'))

    appt.status = "cancelled"
    db.session.commit()
    flash("Appointment cancelled!", "info")
    return redirect(url_for('patient_dashboard'))

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'id' not in session:
        return redirect(url_for('login'))

    user = User.query.get_or_404(session['id'])

    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')

        new_pass = request.form.get('password')
        if new_pass:
            user.password = new_pass

        db.session.commit()
        flash("Profile updated successfully!", "success")

        # redirect based on role
        if user.role == 'patient':
            return redirect(url_for('patient_dashboard'))
        elif user.role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        else:
            return redirect(url_for('admin_dashboard'))

    return render_template('edit_profile.html', user=user)

@app.route('/my_history')
def my_history():
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    # redirect to full history page
    return redirect(url_for('view_patient_history', patient_id=session['id']))



# ------------------------------------------------
# DEPARTMENTS
# ------------------------------------------------
@app.route('/department/<int:dept_id>')
def department_details(dept_id):
    if 'role' not in session:
        return redirect(url_for('login'))

    dept = Department.query.get_or_404(dept_id)
    doctors = Doctor.query.filter_by(department_id=dept_id).all()

    return render_template(
        "department_details.html",
        department=dept,
        doctors=doctors
    )


# ------------------------------------------------
# DOCTOR AVAILABILITY + BOOKING
# ------------------------------------------------
@app.route('/doctor/<int:doc_id>/availability')
def doctor_availability(doc_id):
    doctor = Doctor.query.get_or_404(doc_id)

    # static sample slots
    sample_slots = {
        "05/12/2025": ["08:00 - 12:00 am", "04:00 - 09:00 pm"],
        "06/12/2025": ["08:00 - 12:00 am", "04:00 - 09:00 pm"],
        "07/12/2025": ["08:00 - 12:00 am", "04:00 - 09:00 pm"],
        "08/12/2025": ["08:00 - 12:00 am", "04:00 - 09:00 pm"],
        "09/12/2025": ["08:00 - 12:00 am", "04:00 - 09:00 pm"],
        "10/12/2025": ["08:00 - 12:00 am", "04:00 - 09:00 pm"],
        "11/12/2025": ["08:00 - 12:00 am", "04:00 - 09:00 pm"],
        "12/12/2025": ["08:00 - 12:00 am", "04:00 - 09:00 pm"],
    }

    # Fetch booked slots from DB
    booked = Appointment.query.filter_by(
        doctor_id=doctor.user_id,
        status='booked'
    ).all()

    booked_slots = {(a.date, a.time) for a in booked}

    return render_template(
        "doctor_availability.html",
        doctor=doctor,
        slots=sample_slots,
        booked_slots=booked_slots
    )

# ------------------------------------------------
# DOCTOR: UPDATE PATIENT HISTORY FOR AN APPOINTMENT
# ------------------------------------------------
@app.route('/doctor/appointment/<int:appt_id>/update', methods=['GET', 'POST'])
def update_patient_history(appt_id):
    # Only doctors allowed
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    # Get appointment
    appt = Appointment.query.get_or_404(appt_id)

    # Make sure this appointment belongs to the logged-in doctor
    if appt.doctor_id != session['id']:
        flash("You can only update your own appointments.", "danger")
        return redirect(url_for('doctor_dashboard'))

    if request.method == 'POST':
        # Read form fields
        visit_type   = request.form.get('visit_type')
        test_done    = request.form.get('test_done')
        diagnosis    = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        medicines    = request.form.get('medicines')

        # Create a Treatment row
        treatment = Treatment(
            appointment_id=appt.id,
            visit_type=visit_type,
            test_done=test_done,
            diagnosis=diagnosis,
            prescription=prescription,
            medicines=medicines
        )
        db.session.add(treatment)

        # (optional) mark appointment as completed
        appt.status = "completed"

        db.session.commit()
        flash("Patient history updated successfully.", "success")
        return redirect(url_for('doctor_dashboard'))

    # GET => show the form
    return render_template('update_history.html', appointment=appt)



@app.route('/doctor/<int:doc_id>/book', methods=['POST'])
def book_appointment(doc_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    doctor = Doctor.query.get_or_404(doc_id)
    date = request.form.get('date')
    time = request.form.get('time')

    appt = Appointment(
        doctor_id=doctor.user_id,   # FIXED
        patient_id=session['id'],
        date=date,
        time=time,
        type="In-person",
        status="booked"
    )
    db.session.add(appt)
    db.session.commit()

    flash("Appointment booked!", "success")
    return redirect(url_for('patient_dashboard'))

@app.route('/doctor/complete/<int:appt_id>', methods=['POST', 'GET'])
def doctor_complete_appointment(appt_id):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    appt = Appointment.query.get_or_404(appt_id)
    appt.status = "completed"
    db.session.commit()

    flash("Appointment marked as completed!", "success")
    return redirect(url_for('doctor_dashboard'))

@app.route('/doctor/cancel/<int:appt_id>')
def doctor_cancel_appointment(appt_id):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    appt = Appointment.query.get_or_404(appt_id)
    appt.status = "cancelled"
    db.session.commit()

    flash("Appointment cancelled successfully!", "info")
    return redirect(url_for('doctor_dashboard'))


# ------------------------------------------------
# ADMIN DASHBOARD + DOCTOR CRUD
# ------------------------------------------------
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    doctors = User.query.filter_by(role='doctor').all()
    patients = User.query.filter_by(role='patient').all()
    appointments = Appointment.query.all()

    return render_template(
        "admin_dashboard.html",
        doctors=doctors,
        patients=patients,
        appointments=appointments
    )


@app.route('/admin_dashboard/create_doctor', methods=['GET', 'POST'])
def create_doctor():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        dept = request.form.get("department_id")
        qualification = request.form.get("qualification")
        experience = request.form.get("experience")

        new_user = User(
            username=name,
            email=email,
            password=password,
            role='doctor'
        )
        db.session.add(new_user)
        db.session.commit()

        new_doctor = Doctor(
            user_id=new_user.id,
            department_id=dept,
            qualification=qualification,
            experience=experience
        )
        db.session.add(new_doctor)
        db.session.commit()

        flash("Doctor added!", "success")
        return redirect(url_for('admin_dashboard'))

    departments = Department.query.all()
    return render_template('create_doctor.html', departments=departments)


@app.route('/admin_dashboard/edit_doctor/<int:doc_id>', methods=["GET", "POST"])
def edit_doctor(doc_id):
    doctor = Doctor.query.get_or_404(doc_id)
    departments = Department.query.all()

    if request.method == "POST":
        doctor.user.username = request.form.get("name")
        doctor.user.email = request.form.get("email")

        new_pass = request.form.get("password")
        if new_pass:
            doctor.user.password = new_pass

        doctor.department_id = request.form.get("department_id")
        doctor.qualification = request.form.get("qualification")
        doctor.experience = request.form.get("experience")

        db.session.commit()
        flash("Doctor updated!", "success")

        return redirect(url_for('admin_dashboard'))

    return render_template("edit_doctor.html", doctor=doctor, departments=departments)


# ------------------------------------------------
# DOCTOR DASHBOARD
# ------------------------------------------------
@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    doc_user = User.query.get_or_404(session['id'])
    profile = doc_user.doctor_profile

    upcoming = Appointment.query.filter_by(
        doctor_id=doc_user.id, status='booked'
    ).all()

    return render_template(
        'doctor_dashboard.html',
        doctor=doc_user,
        doc_profile=profile,
        upcoming_appointments=upcoming
    )


# ------------------------------------------------
# DB INIT
# ------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if Department.query.count() == 0:
            db.session.add_all([
                Department(Department_name="Cardiology", description="Heart care"),
                Department(Department_name="Oncology", description="Cancer care"),
                Department(Department_name="General Medicine", description="General checkups"),
            ])
            db.session.commit()

        if not User.query.filter_by(username="admin").first():
            admin = User(
                username="admin",
                email="admin@gmail.com",
                password="admin",
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True, use_reloader=True)
