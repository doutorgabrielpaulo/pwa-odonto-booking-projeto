# app/__init__.py
from app.models.user import User, Room, Reservation, SiteSettings, RentableEquipment, EquipmentReservation, Tutorial, ApiLog, UserTutorialPreference, TempLock, ParkingSpot, ParkingReservation, RoomEquipment
from flask import Flask
from config import Config
from app.extensions import db, bcrypt, login_manager, migrate, mail
 # Importe os modelos APÓS a inicialização do 'db'
    
    
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    # Inicialize as extensões
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
  
    # Registre os blueprints
    from app.routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from app.routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from app.routes.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    
    return app
