import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    STEAM_API_KEY = os.getenv("STEAM_API_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///steam_value_lookup.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False