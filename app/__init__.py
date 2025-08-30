from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail # <-- 1. Importe o Mail

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
migrate = Migrate()
mail = Mail() # <-- 2. Crie a instância do Mail

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app) # <-- 3. Inicialize o Mail com o app
    
    from app.routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from app.routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from app.routes.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    return app
