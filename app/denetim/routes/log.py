from flask import Blueprint, render_template, request
from flask_login import login_required
from app.utils import role_required
from app.models.denetim import DenetimLog
from app.models.user import User

bp = Blueprint('log', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    islem = request.args.get('islem', '')
    modul = request.args.get('modul', '')
    kullanici_id = request.args.get('kullanici_id', 0, type=int)

    query = DenetimLog.query
    if islem:
        query = query.filter(DenetimLog.islem == islem)
    if modul:
        query = query.filter(DenetimLog.modul.ilike(f'%{modul}%'))
    if kullanici_id:
        query = query.filter(DenetimLog.kullanici_id == kullanici_id)

    loglar = query.order_by(DenetimLog.tarih.desc()).paginate(page=page, per_page=30)
    kullanicilar = User.query.order_by(User.ad).all()

    return render_template('denetim/log_listesi.html',
                           loglar=loglar, islem=islem, modul=modul,
                           kullanici_id=kullanici_id, kullanicilar=kullanicilar)
