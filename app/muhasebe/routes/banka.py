from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.muhasebe import BankaHesabi, BankaHareketi
from app.muhasebe.forms import BankaHesapForm, TransferForm
from app.muhasebe.utils import banka_hareketi_olustur

bp = Blueprint('banka', __name__)


@bp.route('/')
@login_required
def liste():
    hesaplar = BankaHesabi.query.filter_by(aktif=True).all()
    toplam_bakiye = sum(float(h.bakiye) for h in hesaplar)
    return render_template('muhasebe/banka/liste.html',
                           hesaplar=hesaplar, toplam_bakiye=toplam_bakiye)


@bp.route('/ekle', methods=['GET', 'POST'])
@login_required
def ekle():
    form = BankaHesapForm()
    if form.validate_on_submit():
        hesap = BankaHesabi(
            banka_adi=form.banka_adi.data,
            hesap_adi=form.hesap_adi.data,
            iban=form.iban.data,
            hesap_no=form.hesap_no.data,
            bakiye=form.bakiye.data or 0
        )
        db.session.add(hesap)
        db.session.commit()
        flash('Banka hesabı başarıyla eklendi.', 'success')
        return redirect(url_for('muhasebe.banka.liste'))

    return render_template('muhasebe/banka/hesap_form.html',
                           form=form, baslik='Yeni Banka Hesabı')


@bp.route('/<int:hesap_id>')
@login_required
def detay(hesap_id):
    hesap = BankaHesabi.query.get_or_404(hesap_id)
    page = request.args.get('page', 1, type=int)

    hareketler = BankaHareketi.query.filter_by(
        banka_hesap_id=hesap_id
    ).order_by(BankaHareketi.tarih.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('muhasebe/banka/detay.html',
                           hesap=hesap, hareketler=hareketler)


@bp.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    form = TransferForm()

    hesaplar = BankaHesabi.query.filter_by(aktif=True).all()
    hesap_choices = [(h.id, f'{h.banka_adi} - {h.hesap_adi} ({"{:,.2f}".format(h.bakiye)} ₺)') for h in hesaplar]
    form.kaynak_hesap_id.choices = hesap_choices
    form.hedef_hesap_id.choices = hesap_choices

    if form.validate_on_submit():
        if form.kaynak_hesap_id.data == form.hedef_hesap_id.data:
            flash('Kaynak ve hedef hesap aynı olamaz.', 'danger')
            return render_template('muhasebe/banka/transfer.html', form=form)

        kaynak = BankaHesabi.query.get(form.kaynak_hesap_id.data)
        tutar = Decimal(str(form.tutar.data))

        if tutar > Decimal(str(kaynak.bakiye)):
            flash('Kaynak hesapta yeterli bakiye yok.', 'danger')
            return render_template('muhasebe/banka/transfer.html', form=form)

        # Kaynaktan çıkış
        banka_hareketi_olustur(
            form.kaynak_hesap_id.data, 'cikis', form.tutar.data,
            aciklama=f'Transfer: {form.aciklama.data or "Hesaplar arası transfer"}',
            karsi_hesap_id=form.hedef_hesap_id.data
        )

        # Hedefe giriş
        banka_hareketi_olustur(
            form.hedef_hesap_id.data, 'giris', form.tutar.data,
            aciklama=f'Transfer: {form.aciklama.data or "Hesaplar arası transfer"}',
            karsi_hesap_id=form.kaynak_hesap_id.data
        )

        db.session.commit()
        flash(f'{"{:,.2f}".format(form.tutar.data)} ₺ başarıyla transfer edildi.', 'success')
        return redirect(url_for('muhasebe.banka.liste'))

    return render_template('muhasebe/banka/transfer.html', form=form)
