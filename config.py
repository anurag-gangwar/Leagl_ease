import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or os.urandom(24).hex()
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(os.path.dirname(__file__), "instance", "legal_ease.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    REPORTS_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'reports')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SARVAM_MODEL = os.getenv('SARVAM_MODEL', 'sarvam-105b')
    SARVAM_REASONING_EFFORT = os.getenv('SARVAM_REASONING_EFFORT', 'high').strip().lower()
    if SARVAM_REASONING_EFFORT not in {'low', 'medium', 'high'}:
        SARVAM_REASONING_EFFORT = 'high'


    # Supported Languages
    LANGUAGES = {
        'hindi':    {'name': 'Hindi',   'code': 'hi', 'flag': '🇮🇳'},
        'tamil':    {'name': 'Tamil',   'code': 'ta', 'flag': '🇮🇳'},
        'telugu':   {'name': 'Telugu',  'code': 'te', 'flag': '🇮🇳'},
        'marathi':  {'name': 'Marathi', 'code': 'mr', 'flag': '🇮🇳'},
        'bengali':  {'name': 'Bengali', 'code': 'bn', 'flag': '🇮🇳'},
        'kannada':  {'name': 'Kannada', 'code': 'kn', 'flag': '🇮🇳'},
        'gujarati': {'name': 'Gujarati','code': 'gu', 'flag': '🇮🇳'},
    }

    CONTRACT_TYPES = [
        'Rental Agreement',
        'Vendor Contract',
        'Service Agreement',
        'Employment Bond',
        'Non-Disclosure Agreement',
        'Partnership Agreement',
        'Loan Agreement',
        'General Contract',
    ]

    SARVAM_LANGUAGE_CODES = {
        'hindi':    'hi-IN',
        'tamil':    'ta-IN',
        'telugu':   'te-IN',
        'marathi':  'mr-IN',
        'bengali':  'bn-IN',
        'kannada':  'kn-IN',
        'gujarati': 'gu-IN',
        }

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
