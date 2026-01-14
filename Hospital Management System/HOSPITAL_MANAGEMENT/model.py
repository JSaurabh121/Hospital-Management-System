# model.py
from extensions import db
from datetime import datetime

# ========== USER ==========
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)   # 'admin', 'doctor', 'patient'
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)

    # For doctors: link to Doctor profile
    doctor_profile = db.relationship("Doctor", back_populates="user", uselist=False)

    # Appointments where this user is doctor
    doctor_appointments = db.relationship(
        "Appointment",
        foreign_keys="Appointment.doctor_id",
        back_populates="doctor_user"
    )

    # Appointments where this user is patient
    patient_appointments = db.relationship(
        "Appointment",
        foreign_keys="Appointment.patient_id",
        back_populates="patient_user"
    )


# ========== DEPARTMENT ==========
class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    Department_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Doctors that belong to this department
    doctors = db.relationship("Doctor", back_populates="department")


# ========== DOCTOR PROFILE ==========
class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)

    qualification = db.Column(db.String(200))
    experience = db.Column(db.Integer)  # years

    user = db.relationship("User", back_populates="doctor_profile")
    department = db.relationship("Department", back_populates="doctors")


# ========== APPOINTMENT (ADVANCED) ==========
class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    date = db.Column(db.String(20))      # e.g. "24/09/2025"
    time = db.Column(db.String(20))      # e.g. "08 am - 12 pm"
    type = db.Column(db.String(50))      # "In-person", "Online", etc.
    status = db.Column(db.String(20), default='booked')  # booked/completed/cancelled

    # Relationships to doctor and patient
    doctor_user = db.relationship(
        "User",
        foreign_keys=[doctor_id],
        back_populates="doctor_appointments"
    )
    patient_user = db.relationship(
        "User",
        foreign_keys=[patient_id],
        back_populates="patient_appointments"
    )

    # Visit history entries
    treatments = db.relationship(
        "Treatment",
        back_populates="appointment",
        cascade="all, delete-orphan"
    )


# ========== TREATMENT / PATIENT HISTORY ==========
class Treatment(db.Model):
    __tablename__ = 'treatments'

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)

    visit_type = db.Column(db.String(50))   # In-person, Online, etc.
    test_done = db.Column(db.String(100))   # ECG, MRI, etc.
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    medicines = db.Column(db.Text)          # "Med1 1-0-1, Med2 0-1-0"
    date_prescribed = db.Column(db.DateTime, default=datetime.utcnow)

    appointment = db.relationship("Appointment", back_populates="treatments")
