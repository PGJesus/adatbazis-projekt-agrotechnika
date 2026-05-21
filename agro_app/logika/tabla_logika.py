from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from adatbazis.modellek import Tablak, Teljesitesek, Vallalasok


class GazdalkodoElteres(Exception):
    """A vállalás és a tábla nem ugyanahhoz a gazdálkodóhoz tartozik."""


class TeljesitesMarLetezik(Exception):
    """A (vállalás, tábla) pár már teljesítettként van jelölve."""


class TeljesitesNemTalalhato(Exception):
    """Nincs teljesítés a megadott (vállalás, tábla) párhoz."""


def teljesit(
    munkamenet: Session,
    vid: int,
    tid: int,
    datum: date | None = None,
) -> Teljesitesek:
    """Teljesítettnek jelöl egy (vállalás, tábla) párt a megadott dátummal.

    Kivételek:
        GazdalkodoElteres        – ha a tábla nem a vállalás gazdájáé
        TeljesitesMarLetezik     – ha már van bejegyezve teljesítés
    """
    vallalasok = munkamenet.get(Vallalasok, vid)
    if vallalasok is None:
        raise ValueError(f'Ismeretlen vállalás: vid={vid}')

    tabla = munkamenet.get(Tablak, tid)
    if tabla is None:
        raise ValueError(f'Ismeretlen tábla: tid={tid}')

    # A tábla → KET → gazdálkodó láncán ellenőrizzük a tulajdont.
    if tabla.ket.gazdalkodo_gid != vallalasok.gazdalkodo_gid:
        raise GazdalkodoElteres(
            f'A {tid} tábla gazdálkodója (gid={tabla.ket.gazdalkodo_gid}) '
            f'nem egyezik a {vid} vállalás gazdálkodójával '
            f'(gid={vallalasok.gazdalkodo_gid}).'
        )

    meglevo = munkamenet.execute(
        select(Teljesitesek).where(
            Teljesitesek.vallalasok_vid == vid,
            Teljesitesek.tablak_tid    == tid,
        )
    ).scalar_one_or_none()
    if meglevo is not None:
        raise TeljesitesMarLetezik(
            f'A vid={vid}, tid={tid} pár már teljesítettként szerepel '
            f'({meglevo.teljesules_datuma}).'
        )

    telj = Teljesitesek(
        vallalasok_vid=vid,
        tablak_tid=tid,
        teljesules_datuma=datum or date.today(),
    )
    munkamenet.add(telj)
    munkamenet.commit()
    return telj


def visszavon(munkamenet: Session, vid: int, tid: int) -> None:
    """Visszavonja egy (vállalás, tábla) pár teljesítettségét.

    Kivétel:
        TeljesitesNemTalalhato – ha nincs ilyen bejegyzés
    """
    telj = munkamenet.execute(
        select(Teljesitesek).where(
            Teljesitesek.vallalasok_vid == vid,
            Teljesitesek.tablak_tid    == tid,
        )
    ).scalar_one_or_none()
    if telj is None:
        raise TeljesitesNemTalalhato(
            f'Nincs teljesítés a vid={vid}, tid={tid} párhoz.'
        )
    munkamenet.delete(telj)
    munkamenet.commit()
