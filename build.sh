#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

flask db upgrade
flask seed
