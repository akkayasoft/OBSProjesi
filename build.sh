#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# instance klasörünü oluştur (SQLite fallback için)
mkdir -p instance

# 1) Mevcut Alembic migration'larını uygula (eski moduller)
flask db upgrade

# 2) Migration'a girmemiş yeni modellerin tablolarını oluştur (idempotent — varsa dokunmaz)
python -c "from app import create_app; from app.extensions import db; app=create_app(); ctx=app.app_context(); ctx.push(); db.create_all(); print('create_all tamamlandi')"

# 3) Seed verisi (admin kullanıcı, sistem ayarları vs.)
flask seed
