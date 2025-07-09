import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'secret-service-1111')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

    # Database
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.environ.get('POSTGRES_DB', 'discovery')
    POSTGRES_USER = os.environ.get('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'postgres')

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
        f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'false').lower() == 'true'

    # Redis
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', 'redis@pass')
    REDIS_EXPIRE_SECONDS = int(os.environ.get('REDIS_EXPIRE_SECONDS', 30))

    # Load Balancer Settings
    DEFAULT_MAX_CPU_USAGE = 80.0
    DEFAULT_MAX_MEMORY_USAGE = 85.0
    STRICT_MAX_CPU_USAGE = 60.0
    STRICT_MAX_MEMORY_USAGE = 60.0
    STRICT_MAX_CONTAINERS = 5

    # Scoring weights
    CPU_WEIGHT = 0.8
    MEMORY_WEIGHT = 0.8
    HEAVY_PENALTY = 80
    MEDIUM_PENALTY = 20