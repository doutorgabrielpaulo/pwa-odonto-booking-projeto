from app import db

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

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
