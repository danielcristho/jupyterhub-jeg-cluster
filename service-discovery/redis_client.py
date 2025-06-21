from redis import Redis, ConnectionPool
from dotenv import load_dotenv
import os

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_EXPIRE_SECONDS = int(os.getenv("REDIS_EXPIRE_SECONDS", 45))

pool = ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True
)

redis_client = Redis(connection_pool=pool)
