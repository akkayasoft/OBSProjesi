from dotenv import load_dotenv
load_dotenv()  # .env varsa ortam degiskenlerini yukle (VPS/production icin)

from app import create_app

app = create_app()
