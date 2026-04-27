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

    # Abonelik plani: basic / standart / premium / unlimited
    # Limitleri belirler — plan presetlerinden okunur (PLAN_LIMITLERI).
    plan = Column(String(20), nullable=False, default='standart', index=True)

    # Plan preset'inin limitini override eder (null ise plan default'u kullanilir).
    # Ozel anlasmali musterilere dershane bazinda ozel limit verilebilsin diye.
    ogrenci_limiti = Column(Integer, nullable=True)
    kullanici_limiti = Column(Integer, nullable=True)
    ogretmen_limiti = Column(Integer, nullable=True)

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


class PlatformAdmin(MasterBase):
    """Tum tenant'lari yoneten platform admini (Akkayasoft maintainer'i).

    Bu hesap hicbir tenant'in User'i degildir; sadece master DB'de yasar.
    /sistem/ url prefix'inden giris yapip tum dershaneleri yonetir.
    """
    __tablename__ = 'platform_admin'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    ad = Column(String(100), nullable=False)
    soyad = Column(String(100), nullable=False)
    email = Column(String(200), nullable=True)
    aktif = Column(Boolean, default=True, nullable=False)

    son_giris = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def tam_ad(self) -> str:
        return f"{self.ad} {self.soyad}".strip()

    def set_password(self, sifre: str) -> None:
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(sifre)

    def check_password(self, sifre: str) -> bool:
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, sifre)

    def __repr__(self) -> str:
        return f'<PlatformAdmin {self.username!r}>'


class PlatformAuditLog(MasterBase):
    """Platform admin'lerin yaptigi degisiklikleri kayit altina al.

    Kim ne zaman hangi tenant'a ne yapti, ileri donuk denetim icin.
    """
    __tablename__ = 'platform_audit_log'
    __table_args__ = (
        Index('ix_audit_admin_tarih', 'admin_id', 'created_at'),
        Index('ix_audit_tenant', 'tenant_id'),
    )

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, nullable=True)  # FK ekleyebiliriz; simdilik gevsek
    admin_username = Column(String(80), nullable=True)  # admin silindiyse de gozuksun
    tenant_id = Column(Integer, nullable=True)
    tenant_slug = Column(String(64), nullable=True)
    aksiyon = Column(String(50), nullable=False)
    # tenant_create / tenant_update / tenant_suspend / tenant_activate / tenant_delete
    # plan_change / limit_change / login / logout
    detay = Column(Text, nullable=True)
    ip = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f'<PlatformAuditLog {self.aksiyon} by={self.admin_username} tenant={self.tenant_slug}>'
