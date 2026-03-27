"""
PythonAnywhere WSGI Configuration
Bu dosya PythonAnywhere'de WSGI config dosyasına referans olarak kullanılır.
"""
import sys
import os

# Proje dizinini Python path'e ekle
project_home = '/home/KULLANICI_ADINIZ/OBSProjesi'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Ortam değişkenlerini ayarla
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'buraya-guclu-bir-anahtar-yazin'

from app import create_app

application = create_app()
