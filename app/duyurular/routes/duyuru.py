from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.duyurular import Duyuru, DuyuruOkunma
from app.duyurular.forms import DuyuruForm
from datetime import datetime

bp = Blueprint('duyuru', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def liste():
    kategori = request.args.get('kategori', '')
    arama = request.args.get('arama', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Duyuru.query.filter_by(aktif=True)

    if kategori:
        query = query.filter(Duyuru.kategori == kategori)
    if arama:
        query = query.filter(
            db.or_(
                Duyuru.baslik.ilike(f'%{arama}%'),
                Duyuru.icerik.ilike(f'%{arama}%')
            )
        )

    duyurular = query.order_by(
        Duyuru.sabitlenmis.desc(),
        Duyuru.yayinlanma_tarihi.desc()
    ).paginate(page=page, per_page=20)

    return render_template('duyurular/duyuru_listesi.html',
                           duyurular=duyurular,
                           kategori=kategori,
                           arama=arama)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def yeni():
    form = DuyuruForm()

    if form.validate_on_submit():
        duyuru = Duyuru(
            baslik=form.baslik.data,
            icerik=form.icerik.data,
            kategori=form.kategori.data,
            oncelik=form.oncelik.data,
            hedef_kitle=form.hedef_kitle.data,
            bitis_tarihi=form.bitis_tarihi.data,
            sabitlenmis=form.sabitlenmis.data,
            yayinlayan_id=current_user.id,
            yayinlanma_tarihi=datetime.utcnow(),
        )
        db.session.add(duyuru)
        db.session.commit()

        # Web Push gonderimi — hedef kitleye gore
        try:
            from app.models.user import User
            from app.utils.push import push_gonder_kullanicilar

            rol_map = {
                'ogretmenler': ['ogretmen'],
                'ogrenciler': ['ogrenci'],
                'veliler': ['veli'],
                'personel': ['personel', 'muhasebeci', 'ogretmen'],
                'tumu': ['ogretmen', 'ogrenci', 'veli', 'personel',
                         'muhasebeci', 'admin'],
            }
            roller = rol_map.get(duyuru.hedef_kitle, ['ogrenci', 'veli'])
            kullanici_ids = [
                u.id for u in User.query.filter(
                    User.rol.in_(roller), User.aktif.is_(True)
                ).all()
            ]
            onek = '📌 ' if duyuru.oncelik == 'acil' else ''
            push_gonder_kullanicilar(
                kullanici_ids,
                title=f'{onek}{duyuru.baslik}',
                body=(duyuru.icerik or '')[:140],
                url=f'/duyurular/duyuru/{duyuru.id}',
                tag=f'duyuru-{duyuru.id}',
            )
        except Exception as e:  # noqa: BLE001
            current_app.logger.warning('Duyuru push hatasi: %s', e)

        flash('Duyuru başarıyla oluşturuldu.', 'success')
        return redirect(url_for('duyurular.duyuru.liste'))

    return render_template('duyurular/duyuru_form.html',
                           form=form, baslik='Yeni Duyuru')


@bp.route('/<int:duyuru_id>')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def detay(duyuru_id):
    duyuru = Duyuru.query.get_or_404(duyuru_id)

    # Okunma sayısını artır ve okunma kaydı oluştur
    okunma = DuyuruOkunma.query.filter_by(
        duyuru_id=duyuru.id,
        kullanici_id=current_user.id
    ).first()

    if not okunma:
        okunma = DuyuruOkunma(
            duyuru_id=duyuru.id,
            kullanici_id=current_user.id,
        )
        db.session.add(okunma)
        duyuru.okunma_sayisi = (duyuru.okunma_sayisi or 0) + 1
        db.session.commit()

    return render_template('duyurular/duyuru_detay.html', duyuru=duyuru)


@bp.route('/<int:duyuru_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def duzenle(duyuru_id):
    duyuru = Duyuru.query.get_or_404(duyuru_id)
    form = DuyuruForm(obj=duyuru)

    if form.validate_on_submit():
        duyuru.baslik = form.baslik.data
        duyuru.icerik = form.icerik.data
        duyuru.kategori = form.kategori.data
        duyuru.oncelik = form.oncelik.data
        duyuru.hedef_kitle = form.hedef_kitle.data
        duyuru.bitis_tarihi = form.bitis_tarihi.data
        duyuru.sabitlenmis = form.sabitlenmis.data

        db.session.commit()
        flash('Duyuru başarıyla güncellendi.', 'success')
        return redirect(url_for('duyurular.duyuru.detay', duyuru_id=duyuru.id))

    return render_template('duyurular/duyuru_form.html',
                           form=form, baslik='Duyuru Düzenle')


@bp.route('/<int:duyuru_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def sil(duyuru_id):
    duyuru = Duyuru.query.get_or_404(duyuru_id)
    baslik = duyuru.baslik
    db.session.delete(duyuru)
    db.session.commit()
    flash(f'"{baslik}" duyurusu silindi.', 'success')
    return redirect(url_for('duyurular.duyuru.liste'))


@bp.route('/<int:duyuru_id>/sabitle', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def sabitle(duyuru_id):
    duyuru = Duyuru.query.get_or_404(duyuru_id)
    duyuru.sabitlenmis = not duyuru.sabitlenmis
    db.session.commit()
    durum = 'sabitlendi' if duyuru.sabitlenmis else 'sabitlemesi kaldırıldı'
    flash(f'Duyuru {durum}.', 'success')
    return redirect(url_for('duyurular.duyuru.liste'))
