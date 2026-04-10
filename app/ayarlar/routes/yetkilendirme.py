from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.ayarlar import RolModulIzin

bp = Blueprint('yetkilendirme', __name__, url_prefix='/yetkilendirme')


@bp.route('/')
@login_required
@role_required('admin')
def index():
    """Rol-modül yetkilendirme matrisi"""
    roller = RolModulIzin.ROLLER
    moduller = RolModulIzin.MODULLER

    # Mevcut izinleri çek
    izinler = {}
    for rol in roller:
        izinler[rol] = {}
        for modul_key in moduller:
            izin = RolModulIzin.query.filter_by(rol=rol, modul_key=modul_key).first()
            izinler[rol][modul_key] = izin.aktif if izin else (rol == 'admin')

    return render_template('ayarlar/yetkilendirme.html',
                           roller=roller,
                           moduller=moduller,
                           izinler=izinler)


@bp.route('/kaydet', methods=['POST'])
@login_required
@role_required('admin')
def kaydet():
    """Yetkilendirme değişikliklerini kaydet"""
    roller = RolModulIzin.ROLLER
    moduller = RolModulIzin.MODULLER

    for rol in roller:
        for modul_key in moduller:
            checkbox_name = f'izin_{rol}_{modul_key}'
            aktif = checkbox_name in request.form

            izin = RolModulIzin.query.filter_by(rol=rol, modul_key=modul_key).first()
            if izin:
                izin.aktif = aktif
            else:
                db.session.add(RolModulIzin(rol=rol, modul_key=modul_key, aktif=aktif))

    db.session.commit()
    flash('Yetkilendirme ayarları başarıyla kaydedildi.', 'success')
    return redirect(url_for('ayarlar.yetkilendirme.index'))


@bp.route('/sifirla', methods=['POST'])
@login_required
@role_required('admin')
def sifirla():
    """Varsayılan izinlere sıfırla"""
    RolModulIzin.query.delete()
    db.session.commit()
    RolModulIzin.varsayilan_izinleri_olustur()
    flash('Yetkilendirme ayarları varsayılana sıfırlandı.', 'info')
    return redirect(url_for('ayarlar.yetkilendirme.index'))
