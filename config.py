import os
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

password = urllib.parse.quote_plus("student")  # Ensure proper encoding
db_url = f"postgresql://postgres:{password}@127.0.0.1:5432/smart_parking_db"


class Config:
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")

print("Database URL:", Config.SQLALCHEMY_DATABASE_URI)
