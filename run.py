from dotenv import load_dotenv
load_dotenv()  # .env varsa ortam degiskenlerini yukle (lokal gelistirme icin)

from app import create_app

app = create_app()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, port=port)
