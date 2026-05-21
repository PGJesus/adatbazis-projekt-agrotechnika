from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from adatbazis.modellek import Ket, Tablak, Teljesitesek, Vallalasok


class Allapot(enum.Enum):
    ZOLD     = 'zold'
    SARGA    = 'sarga'
    PIROS    = 'piros'
    SZANKCIO = 'szankcio'
    KESZ     = 'kesz'


# ─── Ablak-számítás ───────────────────────────────────────────────────────────

def aktualis_ablak_vege(ma: date | None = None) -> date:
    """Az aktuális 5-éves ablak utolsó napja (pl. 2029-12-31)."""
    ma = ma or date.today()
    # Ablakok: 2025–2029, 2030–2034, … (az első ablak kezdete: 2025)
    ablak_sorszam = (ma.year - 2025) // 5
    ablak_vege_ev = 2025 + ablak_sorszam * 5 + 4
    return date(ablak_vege_ev, 12, 31)


def _honap_marad(ma: date, cel: date) -> int:
    """Egész hónapok száma ma és cel között (negatív, ha cel a múltban van)."""
    return (cel.year - ma.year) * 12 + (cel.month - ma.month)


# ─── KET-szintű logika ────────────────────────────────────────────────────────

def haladas(munkamenet: Session, kid: int) -> tuple[int, int]:
    """(kész, összes) teljesítési pár a megadott KEThez.

    összes = len(farmer vallalasok) × len(KET táblák)
    kész   = DB-ből megszámolt, ténylegesen teljesített párok
    """
    ket = munkamenet.get(Ket, kid)
    if ket is None:
        raise ValueError(f'Ismeretlen KET: kid={kid}')

    vallalasok_szam = (
        munkamenet.execute(
            select(func.count())
            .select_from(Vallalasok)
            .where(Vallalasok.gazdalkodo_gid == ket.gazdalkodo_gid)
        ).scalar_one()
    )
    tabla_szam = (
        munkamenet.execute(
            select(func.count())
            .select_from(Tablak)
            .where(Tablak.ket_kid == kid)
        ).scalar_one()
    )
    osszesen = vallalasok_szam * tabla_szam

    keszult = munkamenet.execute(
        select(func.count())
        .select_from(Teljesitesek)
        .join(Vallalasok, Teljesitesek.vallalasok_vid == Vallalasok.vid)
        .join(Tablak,     Teljesitesek.tablak_tid     == Tablak.tid)
        .where(
            Tablak.ket_kid           == kid,
            Vallalasok.gazdalkodo_gid == ket.gazdalkodo_gid,
        )
    ).scalar_one()

    return (int(keszult), int(osszesen))


def allapot(munkamenet: Session, kid: int, ma: date | None = None) -> Allapot:
    """Határidő-állapot a megadott KET-hez.

    A `ma` paraméter tesztelhetőséghez; éles futásban None (= date.today()).
    """
    keszult, osszesen = haladas(munkamenet, kid)
    if osszesen > 0 and keszult >= osszesen:
        return Allapot.KESZ

    ma = ma or date.today()
    ablak_vege = aktualis_ablak_vege(ma)

    if ma > ablak_vege:
        return Allapot.SZANKCIO

    honapok = _honap_marad(ma, ablak_vege)

    if honapok <= 12:
        return Allapot.PIROS
    if honapok <= 18:
        return Allapot.SARGA
    return Allapot.ZOLD
