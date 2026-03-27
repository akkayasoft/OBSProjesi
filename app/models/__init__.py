from app.models.user import User  # noqa: F401
from app.models.muhasebe import (  # noqa: F401
    GelirGiderKategorisi, GelirGiderKaydi,
    Ogrenci, OdemePlani, Taksit, Odeme,
    Personel, PersonelOdemeKaydi,
    BankaHesabi, BankaHareketi
)
from app.models.kayit import (  # noqa: F401
    Sinif, Sube, KayitDonemi,
    OgrenciKayit, VeliBilgisi, OgrenciBelge
)
from app.models.devamsizlik import (  # noqa: F401
    Devamsizlik
)
from app.models.personel import (  # noqa: F401
    PersonelIzin
)
