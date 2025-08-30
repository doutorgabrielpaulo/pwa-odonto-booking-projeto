import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Define o caminho base do projeto
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Classe de configuração base."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'voce-precisa-mudar-isso'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- NOVAS CONFIGURAÇÕES DE E-MAIL ---
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
