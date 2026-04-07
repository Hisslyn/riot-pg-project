import os
from dotenv import load_dotenv

load_dotenv(override=True)

RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL is not set. Check your .env file.")
if not RIOT_API_KEY:
    raise EnvironmentError("RIOT_API_KEY is not set. Check your .env file.")

# Regional routing values (for account/match APIs)
REGIONAL_ROUTES = {
    "na1":  "americas",
    "la1":  "americas",
    "la2":  "americas",
    "br1":  "americas",
    "euw1": "europe",
    "eun1": "europe",
    "tr1":  "europe",
    "ru":   "europe",
    "kr":   "asia",
    "jp1":  "asia",
    # Valorant region codes
    "na":   "americas",
    "eu":   "europe",
    "ap":   "asia",
    "oc1":  "sea",
    "ph2":  "sea",
    "sg2":  "sea",
    "th2":  "sea",
    "tw2":  "sea",
    "vn2":  "sea",
}
