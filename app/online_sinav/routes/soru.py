from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.online_sinav import OnlineSinav, SinavSoru, SoruSecenegi
from app.online_sinav.forms import SoruForm

bp = Blueprint('soru', __name__)


@bp.route('/sinav/<int:sinav_id>/sorular')
@login_required
@role_required('admin', 'ogretmen')
def liste(sinav_id):
    sinav = OnlineSinav.query.get_or_404(sinav_id)
    sorular = sinav.sorular.order_by(SinavSoru.sira).all()
    return render_template('online_sinav/soru_listesi.html', sinav=sinav, sorular=sorular)


@bp.route('/sinav/<int:sinav_id>/soru/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni(sinav_id):
    sinav = OnlineSinav.query.get_or_404(sinav_id)
    form = SoruForm()

    if form.validate_on_submit():
        # Sonraki sira numarasi
        son_sira = db.session.query(db.func.max(SinavSoru.sira)).filter_by(sinav_id=sinav.id).scalar() or 0

        soru = SinavSoru(
            sinav_id=sinav.id,
            soru_metni=form.soru_metni.data,
            soru_turu=form.soru_turu.data,
            puan=form.puan.data,
            sira=son_sira + 1,
            zorluk=form.zorluk.data,
            aciklama=form.aciklama.data,
        )
        db.session.add(soru)
        db.session.flush()

        # Secenekleri ekle (coktan secmeli icin)
        if form.soru_turu.data == 'coktan_secmeli':
            secenekler = request.form.getlist('secenek_metni[]')
            dogru_index = request.form.get('dogru_secenek', '0')
            for i, metin in enumerate(secenekler):
                if metin.strip():
                    db.session.add(SoruSecenegi(
                        soru_id=soru.id,
                        secenek_metni=metin.strip(),
                        sira=i + 1,
                        dogru_mu=(str(i) == dogru_index),
                    ))

        # Dogru/yanlis icin otomatik secenekler
        if form.soru_turu.data == 'dogru_yanlis':
            dogru_cevap = request.form.get('dogru_yanlis_cevap', 'true')
            db.session.add(SoruSecenegi(
                soru_id=soru.id, secenek_metni='Doğru', sira=1,
                dogru_mu=(dogru_cevap == 'true')
            ))
            db.session.add(SoruSecenegi(
                soru_id=soru.id, secenek_metni='Yanlış', sira=2,
                dogru_mu=(dogru_cevap == 'false')
            ))

        # Bosluk doldurma icin dogru cevabi secenek olarak sakla
        if form.soru_turu.data == 'bosluk_doldurma':
            dogru_cevap = request.form.get('bosluk_cevap', '')
            if dogru_cevap.strip():
                db.session.add(SoruSecenegi(
                    soru_id=soru.id, secenek_metni=dogru_cevap.strip(),
                    sira=1, dogru_mu=True
                ))

        db.session.commit()
        flash('Soru başarıyla eklendi.', 'success')
        return redirect(url_for('online_sinav.soru.liste', sinav_id=sinav.id))

    return render_template('online_sinav/soru_form.html', form=form, sinav=sinav, baslik='Yeni Soru Ekle')


@bp.route('/soru/<int:soru_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(soru_id):
    soru = SinavSoru.query.get_or_404(soru_id)
    sinav = soru.sinav
    form = SoruForm(obj=soru)

    if form.validate_on_submit():
        soru.soru_metni = form.soru_metni.data
        soru.soru_turu = form.soru_turu.data
        soru.puan = form.puan.data
        soru.zorluk = form.zorluk.data
        soru.aciklama = form.aciklama.data

        # Mevcut secenekleri sil ve yeniden olustur
        SoruSecenegi.query.filter_by(soru_id=soru.id).delete()

        if form.soru_turu.data == 'coktan_secmeli':
            secenekler = request.form.getlist('secenek_metni[]')
            dogru_index = request.form.get('dogru_secenek', '0')
            for i, metin in enumerate(secenekler):
                if metin.strip():
                    db.session.add(SoruSecenegi(
                        soru_id=soru.id,
                        secenek_metni=metin.strip(),
                        sira=i + 1,
                        dogru_mu=(str(i) == dogru_index),
                    ))

        if form.soru_turu.data == 'dogru_yanlis':
            dogru_cevap = request.form.get('dogru_yanlis_cevap', 'true')
            db.session.add(SoruSecenegi(
                soru_id=soru.id, secenek_metni='Doğru', sira=1,
                dogru_mu=(dogru_cevap == 'true')
            ))
            db.session.add(SoruSecenegi(
                soru_id=soru.id, secenek_metni='Yanlış', sira=2,
                dogru_mu=(dogru_cevap == 'false')
            ))

        if form.soru_turu.data == 'bosluk_doldurma':
            dogru_cevap = request.form.get('bosluk_cevap', '')
            if dogru_cevap.strip():
                db.session.add(SoruSecenegi(
                    soru_id=soru.id, secenek_metni=dogru_cevap.strip(),
                    sira=1, dogru_mu=True
                ))

        db.session.commit()
        flash('Soru başarıyla güncellendi.', 'success')
        return redirect(url_for('online_sinav.soru.liste', sinav_id=sinav.id))

    return render_template('online_sinav/soru_form.html', form=form, sinav=sinav, soru=soru, baslik='Soruyu Düzenle')


@bp.route('/soru/<int:soru_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(soru_id):
    soru = SinavSoru.query.get_or_404(soru_id)
    sinav_id = soru.sinav_id
    db.session.delete(soru)
    db.session.commit()
    flash('Soru başarıyla silindi.', 'success')
    return redirect(url_for('online_sinav.soru.liste', sinav_id=sinav_id))
