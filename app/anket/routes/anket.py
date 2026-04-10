from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.utils import role_required
from app.extensions import db
from app.models.anket import Anket
from app.anket.forms import AnketForm
from datetime import date

bp = Blueprint('yonetim', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    hedef_kitle = request.args.get('hedef_kitle', '')
    durum = request.args.get('durum', '')
    page = request.args.get('page', 1, type=int)

    query = Anket.query

    if hedef_kitle:
        query = query.filter(Anket.hedef_kitle == hedef_kitle)

    if durum == 'aktif':
        bugun = date.today()
        query = query.filter(
            Anket.aktif == True,
            Anket.baslangic_tarihi <= bugun,
            Anket.bitis_tarihi >= bugun
        )
    elif durum == 'pasif':
        query = query.filter(Anket.aktif == False)
    elif durum == 'sona_erdi':
        bugun = date.today()
        query = query.filter(Anket.bitis_tarihi < bugun)

    anketler = query.order_by(Anket.created_at.desc()).paginate(page=page, per_page=20)

    return render_template('anket/anket_listesi.html',
                           anketler=anketler,
                           hedef_kitle=hedef_kitle,
                           durum=durum)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = AnketForm()

    if not form.baslangic_tarihi.data:
        form.baslangic_tarihi.data = date.today()

    if form.validate_on_submit():
        anket = Anket(
            baslik=form.baslik.data,
            aciklama=form.aciklama.data,
            olusturan_id=current_user.id,
            hedef_kitle=form.hedef_kitle.data,
            baslangic_tarihi=form.baslangic_tarihi.data,
            bitis_tarihi=form.bitis_tarihi.data,
            anonim=form.anonim.data,
            aktif=form.aktif.data,
        )
        db.session.add(anket)
        db.session.commit()
        flash('Anket basariyla olusturuldu. Simdi sorulari ekleyebilirsiniz.', 'success')
        return redirect(url_for('anket.yonetim.detay', anket_id=anket.id))

    return render_template('anket/anket_form.html',
                           form=form, baslik='Yeni Anket Olustur')


@bp.route('/<int:anket_id>')
@login_required
@role_required('admin', 'ogretmen')
def detay(anket_id):
    anket = Anket.query.get_or_404(anket_id)
    sorular = anket.sorular.order_by(db.text('sira')).all()
    return render_template('anket/anket_detay.html', anket=anket, sorular=sorular)


@bp.route('/<int:anket_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(anket_id):
    anket = Anket.query.get_or_404(anket_id)
    form = AnketForm(obj=anket)

    if form.validate_on_submit():
        anket.baslik = form.baslik.data
        anket.aciklama = form.aciklama.data
        anket.hedef_kitle = form.hedef_kitle.data
        anket.baslangic_tarihi = form.baslangic_tarihi.data
        anket.bitis_tarihi = form.bitis_tarihi.data
        anket.anonim = form.anonim.data
        anket.aktif = form.aktif.data

        db.session.commit()
        flash('Anket basariyla guncellendi.', 'success')
        return redirect(url_for('anket.yonetim.detay', anket_id=anket.id))

    return render_template('anket/anket_form.html',
                           form=form, baslik='Anketi Duzenle', anket=anket)


@bp.route('/<int:anket_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(anket_id):
    anket = Anket.query.get_or_404(anket_id)
    db.session.delete(anket)
    db.session.commit()
    flash('Anket basariyla silindi.', 'success')
    return redirect(url_for('anket.yonetim.liste'))
