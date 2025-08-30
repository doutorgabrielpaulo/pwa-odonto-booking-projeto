from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from datetime import timedelta # Importar timedelta para calcular o tempo de expiração


# --- Loader e Tabelas de Associação ---
room_equipment_association = db.Table('room_equipment',
    db.Column('room_id', db.Integer, db.ForeignKey('room.id')),
    db.Column('equipment_id', db.Integer, db.ForeignKey('equipment.id'))
)

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
    uf_cro = db.Column(db.String(2), nullable=False)
    whatsapp = db.Column(db.String(20), unique=True, nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    genero = db.Column(db.String(50))
    score = db.Column(db.Integer, default=0, nullable=False)
    is_vip = db.Column(db.Boolean, default=False)
    is_chato = db.Column(db.Boolean, default=False)
    fobs_balance = db.Column(db.Float, default=0.0)
    contract_accepted_version = db.Column(db.Integer, default=0)
    veiculo_modelo = db.Column(db.String(100))
    veiculo_placa = db.Column(db.String(10))
    ip_address = db.Column(db.String(45))
    selfie_filename = db.Column(db.String(255))
    document_filename = db.Column(db.String(255))
    signature_filename = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    reservations = db.relationship('Reservation', back_populates='user', lazy='dynamic')
    equipment_reservations = db.relationship('EquipmentReservation', backref='user', lazy='dynamic')
    parking_reservations = db.relationship('ParkingReservation', backref='user', lazy='dynamic')
    temp_locks = db.relationship('TempLock', backref='user', lazy='dynamic') # Adicionar relacionamento com TempLock
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    price_2h30 = db.Column(db.Float, nullable=False, default=90.0)
    price_1h15 = db.Column(db.Float, nullable=False, default=55.0)
    is_active = db.Column(db.Boolean, default=True)
    admin_notice = db.Column(db.Text)
    equipments = db.relationship('Equipment', secondary=room_equipment_association, backref='rooms')
    reservations = db.relationship('Reservation', back_populates='room', lazy='dynamic')
    temp_locks = db.relationship('TempLock', backref='room', lazy='dynamic') # Adicionar relacionamento com TempLock
    
class UserTutorialPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    tutorial_type = db.Column(db.String(50), nullable=False) # Ex: 'autoclave', 'plastificadora'
    dont_remind = db.Column(db.Boolean, default=True)

    # Adicione uma restrição de unicidade para evitar duplicatas
    __table_args__ = (db.UniqueConstraint('user_id', 'room_id', 'tutorial_type', name='_user_tutorial_uc'),)
    
class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reservation_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    total_price = db.Column(db.Float)
    is_paid = db.Column(db.Boolean, default=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user = db.relationship('User', back_populates='reservations')
    room = db.relationship('Room', back_populates='reservations')

class RentableEquipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    daily_price = db.Column(db.Float, nullable=False)
    units_available = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    reservations = db.relationship('EquipmentReservation', backref='equipment', lazy='dynamic')

class EquipmentReservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reservation_date = db.Column(db.Date, nullable=False, index=True)
    is_paid = db.Column(db.Boolean, default=False)
    price = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('rentable_equipment.id'), nullable=False)

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

class Tutorial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    video_url = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True)
    value = db.Column(db.Text)

class ApiLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    event_type = db.Column(db.String(100), index=True)
    status = db.Column(db.String(50), index=True)
    details = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    ip_address = db.Column(db.String(45))

# --- NOVO MODELO (código 2) ---
class TempLock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
