"""Master DB: tenant (dershane/okul) listesi.

Her kurum icin bir satir:
- slug: subdomain (dershanex -> dershanex.obs.akkayasoft.com)
- db_name: kurumun kendi Postgres veritabani adi
- durum: aktif / askida / silindi
- abonelik_bitis: null ise limitsiz

Master DB tenant app'teki db'den tamamen ayridir (ayri engine, ayri metadata).
Kurumsal veriler kurumun kendi DB'sinde; burasi sadece "hangi kurum hangi DB'de"
defteri.
"""
from datetime import datetime
from sqlalchemy import (Column, Integer, String, DateTime, Date, Text, Boolean,
                        Index)
from sqlalchemy.orm import declarative_base


MasterBase = declarative_base()


class Tenant(MasterBase):
    __tablename__ = 'tenants'

    id = Column(Integer, primary_key=True)
    slug = Column(String(64), nullable=False, unique=True, index=True)
    ad = Column(String(200), nullable=False)

    # Kurumun kendi Postgres DB adi (ornek: obs_dershanex).
    # URL sema'si config'teki template'den turetilir.
    db_name = Column(String(120), nullable=False, unique=True)

    durum = Column(String(20), nullable=False, default='aktif', index=True)
    # aktif / askida / silindi

    abonelik_bitis = Column(Date, nullable=True)
    iletisim_email = Column(String(200), nullable=True)
    iletisim_telefon = Column(String(40), nullable=True)
    notlar = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_tenants_durum_slug', 'durum', 'slug'),
    )

    @property
    def aktif_mi(self) -> bool:
        if self.durum != 'aktif':
            return False
        if self.abonelik_bitis is None:
            return True
        from datetime import date
        return date.today() <= self.abonelik_bitis

    def __repr__(self) -> str:
        return f'<Tenant slug={self.slug!r} db={self.db_name!r} durum={self.durum!r}>'
