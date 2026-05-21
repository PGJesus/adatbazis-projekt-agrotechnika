from __future__ import annotations

from sqlalchemy import cast, or_, select, String
from sqlalchemy.orm import Session, selectinload

from adatbazis.modellek import Gazdalkodo, Ket, Tablak, Teljesitesek, Vallalasok

_KERESES_LIMIT = 30


def keres(munkamenet: Session, reszlet: str) -> list[Gazdalkodo]:
    """Prefix-egyezés névben és támogatási azonosítóban; autocomplete-hez."""
    reszlet = reszlet.strip()
    if not reszlet:
        return []
    minta = f'{reszlet}%'
    return list(
        munkamenet.execute(
            select(Gazdalkodo)
            .where(
                or_(
                    Gazdalkodo.nev.ilike(minta),
                    cast(Gazdalkodo.tamogatasi_azonosito, String).like(minta),
                )
            )
            .order_by(Gazdalkodo.nev)
            .limit(_KERESES_LIMIT)
        ).scalars()
    )


def osszes(munkamenet: Session) -> list[Gazdalkodo]:
    """Az összes gazdálkodó, KETeikkel együtt betöltve (dashboard-listához)."""
    return list(
        munkamenet.execute(
            select(Gazdalkodo)
            .options(selectinload(Gazdalkodo.ketek))
            .order_by(Gazdalkodo.nev)
        ).scalars()
    )


def egy(munkamenet: Session, gid: int) -> Gazdalkodo | None:
    """Egy gazdálkodó teljes részletei: KETs → táblák → teljesítések,
    vállalások → teljesítések — mind előre betöltve, N+1 lekérdezés nélkül."""
    return munkamenet.execute(
        select(Gazdalkodo)
        .options(
            selectinload(Gazdalkodo.ketek)
            .selectinload(Ket.tablak)
            .selectinload(Tablak.teljesitesek),
            selectinload(Gazdalkodo.vallalasok)
            .selectinload(Vallalasok.teljesitesek),
        )
        .where(Gazdalkodo.gid == gid)
    ).scalar_one_or_none()
