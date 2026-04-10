import json
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.anket import Anket, AnketSoru, AnketCevap
from datetime import date

bp = Blueprint('katilim', __name__)


@bp.route('/')
@login_required
def aktif_anketler():
    """Kullanicinin doldurabilecegi aktif anketleri listele."""
    bugun = date.today()
    rol = current_user.rol

    query = Anket.query.filter(
        Anket.aktif == True,
        Anket.baslangic_tarihi <= bugun,
        Anket.bitis_tarihi >= bugun,
    )

    # Hedef kitleye gore filtrele
    query = query.filter(
        db.or_(
            Anket.hedef_kitle == 'tumu',
            Anket.hedef_kitle == rol,
        )
    )

    anketler = query.order_by(Anket.created_at.desc()).all()

    # Kullanicinin daha once cevapladigi anketleri isaretle
    cevaplanan_ids = set()
    for anket in anketler:
        if anket.kullanici_cevapladi_mi(current_user.id):
            cevaplanan_ids.add(anket.id)

    return render_template('anket/aktif_anketler.html',
                           anketler=anketler,
                           cevaplanan_ids=cevaplanan_ids)


@bp.route('/<int:anket_id>/doldur', methods=['GET', 'POST'])
@login_required
def doldur(anket_id):
    """Anket doldurma sayfasi."""
    anket = Anket.query.get_or_404(anket_id)
    bugun = date.today()

    # Anket aktif mi kontrol et
    if not anket.aktif or bugun < anket.baslangic_tarihi or bugun > anket.bitis_tarihi:
        flash('Bu anket su anda aktif degil.', 'warning')
        return redirect(url_for('anket.katilim.aktif_anketler'))

    # Hedef kitle kontrolu
    if anket.hedef_kitle != 'tumu' and anket.hedef_kitle != current_user.rol:
        flash('Bu ankete katilma yetkiniz bulunmuyor.', 'danger')
        return redirect(url_for('anket.katilim.aktif_anketler'))

    # Daha once cevaplanmis mi
    if anket.kullanici_cevapladi_mi(current_user.id):
        flash('Bu anketi daha once doldurmusunuz.', 'info')
        return redirect(url_for('anket.katilim.aktif_anketler'))

    sorular = anket.sorular.order_by(AnketSoru.sira).all()

    if not sorular:
        flash('Bu ankette henuz soru bulunmuyor.', 'warning')
        return redirect(url_for('anket.katilim.aktif_anketler'))

    if request.method == 'POST':
        hatalar = []

        for soru in sorular:
            cevap_degeri = request.form.get(f'soru_{soru.id}', '').strip()

            if soru.zorunlu and not cevap_degeri:
                hatalar.append(f'Soru {soru.sira}: Bu soru zorunludur.')
                continue

            if cevap_degeri:
                cevap = AnketCevap(
                    anket_id=anket.id,
                    soru_id=soru.id,
                    kullanici_id=None if anket.anonim else current_user.id,
                    cevap=cevap_degeri,
                )
                db.session.add(cevap)

        if hatalar:
            db.session.rollback()
            for hata in hatalar:
                flash(hata, 'danger')
            return render_template('anket/anket_doldur.html',
                                   anket=anket, sorular=sorular)

        # Anonim olmasa bile katilimciyi takip etmek icin bir isaretci kayit
        if anket.anonim:
            # Anonim ankette kullanici_id'yi sadece takip icin
            # ayri bir kayitta tutalim (cevaplarda tutmuyoruz)
            isaretci = AnketCevap(
                anket_id=anket.id,
                soru_id=sorular[0].id,
                kullanici_id=current_user.id,
                cevap='__katilim_isaretci__',
            )
            db.session.add(isaretci)

        db.session.commit()
        flash('Anket cevaplarniz basariyla kaydedildi. Katiliminiz icin tesekkurler!', 'success')
        return redirect(url_for('anket.katilim.aktif_anketler'))

    return render_template('anket/anket_doldur.html',
                           anket=anket, sorular=sorular)
