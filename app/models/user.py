from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from datetime import timedelta
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Modelos ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    cro = db.Column(db.String(20), unique=True, nullable=False)
    whatsapp = db.Column(db.String(20), unique=True, nullable=False)
    cpf = db.Column(db.String(20), unique=True, nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)
    genero = db.Column(db.String(10), nullable=False)
    uf_cro = db.Column(db.String(2), nullable=False)
    num_cro = db.Column(db.String(10), nullable=False)
    profile_image = db.Column(db.String(20), nullable=False, default="default.jpg")
    score = db.Column(db.Integer, default=0)
    is_admin = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    fobs_balance = db.Column(db.Float, default=0.0)
    contract_accepted_version = db.Column(db.Integer, default=0)
    veiculo_modelo = db.Column(db.String(100))
    veiculo_placa = db.Column(db.String(10))
    is_vip = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(45))
    selfie_filename = db.Column(db.String(255))
    document_filename = db.Column(db.String(255))
    signature_filename = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    reservations = db.relationship("Reservation", backref="booker", lazy=True)
    temp_locks = db.relationship('TempLock', backref='user', lazy='dynamic')
    parking_reservations = db.relationship('ParkingReservation', backref='user', lazy='dynamic')

    def __repr__(self):
        return f"User('{self.nome_completo}' , '{self.email}')"
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config["SECRET_KEY"])
        return s.dumps({"user_id": self.id}).decode("utf-8")
    
    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            user_id = s.loads(token, max_age=1800)["user_id"]
        except:
            return None
        return User.query.get(user_id)
        
class BlockedTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room = db.relationship('Room', backref=db.backref('blocked_times', lazy=True))
    
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    price_2h30 = db.Column(db.Float, nullable=False)
    price_1h15 = db.Column(db.Float, nullable=False)
    video_url = db.Column(db.String(200), nullable=True)
    video_tutorial_url = db.Column(db.String(200), nullable=True)
    video_tutorial_autoclave_url = db.Column(db.String(200), nullable=True)
    video_tutorial_raiox_url = db.Column(db.String(200), nullable=True)
    video_tutorial_plastificadora_url = db.Column(db.String(200), nullable=True)
    image_file = db.Column(db.String(20), nullable=False, default="default_room.jpg")
    is_active = db.Column(db.Boolean, default=True)
    admin_notice = db.Column(db.Text)
    allow_1h15_rental = db.Column(db.Boolean, default=True)
    is_visible = db.Column(db.Boolean, default=True)
    
    reservations = db.relationship("Reservation", backref="room", lazy=True)
    temp_locks = db.relationship('TempLock', backref='room', lazy='dynamic')
    equipments = db.relationship('Equipment', secondary='room_equipment', backref=db.backref('rooms', lazy='dynamic'))
    
    def __repr__(self):
        return f"Room('{self.name}' , '{self.price_2h30}')"
# Tabela de associação para muitos-para-muitos entre Room e Equipment
room_equipment = db.Table('room_equipment',
    db.Column('room_id', db.Integer, db.ForeignKey('room.id'), primary_key=True),
    db.Column('equipment_id', db.Integer, db.ForeignKey('equipment.id'), primary_key=True)
)
class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    reservation_date = db.Column(db.Date, nullable=False, index=True)  # NOVA LINHA ADICIONADA
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_paid = db.Column(db.Boolean, default=False, index=True)
    total_price = db.Column(db.Float)
    
    def __repr__(self):
        return f"Reservation(User: {self.user_id}, Room: {self.room_id}, Start: {self.start_time}, End: {self.end_time})"
class Tutorial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    video_url = db.Column(db.String(200), nullable=True)
    image_file = db.Column(db.String(20), nullable=False, default="default_tutorial.jpg")
    
    def __repr__(self):
        return f"Tutorial('{self.title}')"
class SiteSettings(db.Model):
    __tablename__ = 'site_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f"SiteSettings('{self.key}', '{self.value}')"
class ApiLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    event_type = db.Column(db.String(100), index=True)
    status = db.Column(db.String(50), index=True)
    details = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    ip_address = db.Column(db.String(45))
class UserTutorialPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    tutorial_type = db.Column(db.String(50), nullable=False)
    dont_remind = db.Column(db.Boolean, default=True)
    __table_args__ = (db.UniqueConstraint('user_id', 'room_id', 'tutorial_type', name='_user_tutorial_uc'),)
class TempLock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    reservations = db.relationship('ParkingReservation', backref='spot', lazy='dynamic')
class ParkingReservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reservation_date = db.Column(db.Date, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
