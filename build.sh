#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# instance klasörünü oluştur (SQLite için gerekli)
mkdir -p instance

# Veritabanını hazırla
flask db upgrade
flask seed
