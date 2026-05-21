from __future__ import annotations

import dataclasses
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session

from adatbazis.modellek import Gazdalkodo, Ket, Tablak, Vallalasok, Teljesitesek


# ─── Nyilvános adattípusok ────────────────────────────────────────────────────

@dataclasses.dataclass
class Figyelmeztetés:
    fajl: str
    munkalap: str
    sor: int          # 1-alapú, egyezik az Excel sorszámával
    oszlop: str
    ertek: Any
    magyarazat: str


@dataclasses.dataclass
class ImportOsszegzo:
    gazdalkodok: int
    ketek: int
    tablak: int
    teljesitesek: int
    figyelmeztetesek: list[Figyelmeztetés]


# ─── Konstansok ───────────────────────────────────────────────────────────────

# (eloiras_azonosito, Excel oszlopnév a vállalásokban, DB leiras)
_VALLALASOK_TIPUSOK: list[tuple[int, str, str]] = [
    (1, 'istállótrágya kijuttatás 1', 'istállótrágya kijuttatás 1'),
    (2, 'istállótrágya kijuttatás 2', 'istállótrágya kijuttatás 2'),
    (3, 'melléktermék beforgatás',    'melléktermék beforgatás'),
    (4, 'középmély lazítás',          'középmély lazítás'),
]

_TABLA_EVEK = range(2025, 2030)
_TRAGYAZAS_OSZLOP    = 'istállótrágya kijuttatás dátum'
_MELLEKTERMEK_OSZLOP = 'melléktermék beforgatás dátum'
_LAZITAS_OSZLOP      = 'középmély lazítás dátum'


# ─── Fő importáló függvény ────────────────────────────────────────────────────

def importal(
    mappa: Path | str,
    munkamenet: Session,
    mod: str = 'feluliras',   # 'feluliras' | 'osszeflzes'
) -> ImportOsszegzo:
    """Importálja az összes Excel fájlt a megadott mappából az adatbázisba.

    mod='feluliras'  – az adatbázist először törli, majd újraépíti.
    mod='osszeflzes' – külső azonosítók alapján upsert, új teljesítéseket ad hozzá.
    """
    mappa = Path(mappa)
    figyelmeztetesek: list[Figyelmeztetés] = []

    # ── 1. Fájlok beolvasása ──────────────────────────────────────────────────
    gazd_munkalap, gazd_df = _excel_beolvas(mappa / 'Gazd_alapadatok.xlsx')
    vall_munkalap, vall_df = _excel_beolvas(mappa / 'Agrotechnika_vállalások.xlsx')
    ket_munkalap,  ket_df  = _excel_beolvas(mappa / 'KETEK.xlsx')

    # lista: (fájlnév, munkalapnév, DataFrame)
    tabla_adatok: list[tuple[str, str, pd.DataFrame]] = []
    for ev in _TABLA_EVEK:
        fajlnev = f'Táblák_{ev}.xlsx'
        munkalap, df = _excel_beolvas(mappa / fajlnev)
        tabla_adatok.append((fajlnev, munkalap, df))

    # ── 2. Felülírás: adatbázis ürítése ───────────────────────────────────────
    if mod == 'feluliras':
        _torol_mindent(munkamenet)

    # ── 3. Gazdálkodók ────────────────────────────────────────────────────────
    # tamogatasi_azonosito → Gazdalkodo ORM obj
    gazd_map: dict[int, Gazdalkodo] = {}

    for pandas_idx, sor in gazd_df.iterrows():
        ta = int(sor['támogatási azonosító'])

        if mod == 'osszeflzes':
            meglevo = munkamenet.query(Gazdalkodo).filter_by(
                tamogatasi_azonosito=ta
            ).one_or_none()
            if meglevo:
                meglevo.nev         = str(sor['név'])
                meglevo.cim         = str(sor['Lakcím'])
                meglevo.telefonszam = str(sor['telefonszám'])
                meglevo.email       = _szoveg_vagy_none(sor['email'])
                gazd_map[ta] = meglevo
                continue

        g = Gazdalkodo(
            nev=str(sor['név']),
            cim=str(sor['Lakcím']),
            telefonszam=str(sor['telefonszám']),
            email=_szoveg_vagy_none(sor['email']),
            tamogatasi_azonosito=ta,
        )
        munkamenet.add(g)
        gazd_map[ta] = g

    munkamenet.flush()   # gid-ek kiosztása

    # ── 4. Vállalások ─────────────────────────────────────────────────────────
    # (tamogatasi_azonosito, eloiras_azonosito) → Vallalasok ORM obj
    vallalasok_map: dict[tuple[int, int], Vallalasok] = {}

    for pandas_idx, sor in vall_df.iterrows():
        excel_sor = int(pandas_idx) + 2
        ta = int(sor['támogatási azonosító'])

        if ta not in gazd_map:
            figyelmeztetesek.append(Figyelmeztetés(
                fajl='Agrotechnika_vállalások.xlsx',
                munkalap=vall_munkalap,
                sor=excel_sor,
                oszlop='támogatási azonosító',
                ertek=ta,
                magyarazat=(
                    f'A {ta} támogatási azonosítójú gazdálkodó nem szerepel '
                    f'a Gazd_alapadatok.xlsx fájlban.'
                ),
            ))
            continue

        g = gazd_map[ta]

        for eloiras_azon, vallalas_oszlop, leiras in _VALLALASOK_TIPUSOK:
            if str(sor[vallalas_oszlop]).strip().lower() != 'igen':
                continue

            if mod == 'osszeflzes':
                meglevo = munkamenet.query(Vallalasok).filter_by(
                    gazdalkodo_gid=g.gid,
                    eloiras_azonosito=eloiras_azon,
                ).one_or_none()
                if meglevo:
                    vallalasok_map[(ta, eloiras_azon)] = meglevo
                    continue

            v = Vallalasok(eloiras_azonosito=eloiras_azon, leiras=leiras)
            v.gazdalkodo = g
            munkamenet.add(v)
            vallalasok_map[(ta, eloiras_azon)] = v

    munkamenet.flush()   # vid-ek kiosztása

    # ── 5. KETs ───────────────────────────────────────────────────────────────
    # ket_azonosito → Ket ORM obj
    ket_map: dict[int, Ket] = {}

    for pandas_idx, sor in ket_df.iterrows():
        excel_sor = int(pandas_idx) + 2
        ta      = int(sor['támogatási azonosító'])
        ket_azon = int(sor['KET azonosító'])

        if ta not in gazd_map:
            figyelmeztetesek.append(Figyelmeztetés(
                fajl='KETEK.xlsx',
                munkalap=ket_munkalap,
                sor=excel_sor,
                oszlop='támogatási azonosító',
                ertek=ta,
                magyarazat=(
                    f'A {ta} támogatási azonosítójú gazdálkodó nem szerepel '
                    f'a Gazd_alapadatok.xlsx fájlban.'
                ),
            ))
            continue

        if mod == 'osszeflzes':
            meglevo = munkamenet.query(Ket).filter_by(
                ket_azonosito=ket_azon
            ).one_or_none()
            if meglevo:
                meglevo.terulet_ha = float(sor['KET terület [ha]'])
                ket_map[ket_azon] = meglevo
                continue

        k = Ket(ket_azonosito=ket_azon, terulet_ha=float(sor['KET terület [ha]']))
        k.gazdalkodo = gazd_map[ta]
        munkamenet.add(k)
        ket_map[ket_azon] = k

    munkamenet.flush()   # kid-ek kiosztása

    # ── 6. Táblák + teljesítési adatok gyűjtése ───────────────────────────────
    # tablaazonosito → Tablak ORM obj
    tabla_map: dict[str, Tablak] = {}

    # Trágyázási események: (ta, tablaazon) → dátumok listája (rendezés előtt)
    tragyazas: dict[tuple[int, str], list[date]] = defaultdict(list)
    # Egyszeri dátumok (legelső előfordulás minden KET-en belüli tábla–gazda párra)
    mellektermek_dat: dict[tuple[int, str], date] = {}
    lazitas_dat:      dict[tuple[int, str], date] = {}

    for fajlnev, munkalap, df in tabla_adatok:
        ev = int(fajlnev.split('_')[1].split('.')[0])

        # ── Validáció: azonos tábla kétszer trágyázva ugyanabban az évben ─────
        # Csak a dátumot tartalmazó sorok között keresünk ismétlődést,
        # hogy ne keletkezzen hamis pozitív ott, ahol az egyik duplikát üres.
        has_dat_df   = df[df[_TRAGYAZAS_OSZLOP].apply(pd.notna)]
        duplik_idx   = has_dat_df[
            has_dat_df.duplicated(subset=['tábla azonosító'], keep=False)
        ].index
        for pidx in duplik_idx:
            vsor = df.loc[pidx]
            figyelmeztetesek.append(Figyelmeztetés(
                fajl=fajlnev,
                munkalap=munkalap,
                sor=int(pidx) + 2,
                oszlop=_TRAGYAZAS_OSZLOP,
                ertek=str(vsor[_TRAGYAZAS_OSZLOP]),
                magyarazat=(
                    f'A(z) {vsor["tábla azonosító"]} azonosítójú tábla '
                    f'{ev}-ben kétszer szerepel trágyázási dátummal. '
                    f'Ugyanazon tábla ugyanabban az évben nem trágyázható kétszer.'
                ),
            ))

        # ── Sorok feldolgozása ─────────────────────────────────────────────────
        # Nyomon követjük, melyik tábla-év kombinációt láttuk már trágyázással,
        # hogy a duplikált sorokat csak egyszer számítsuk be.
        tragy_latott_evben: set[str] = set()

        for pandas_idx, sor in df.iterrows():
            excel_sor  = int(pandas_idx) + 2
            ta         = int(sor['támogatási azonosító'])
            tablaazon  = str(sor['tábla azonosító'])
            ket_azon   = int(sor['KET azonosító'])

            if ta not in gazd_map:
                figyelmeztetesek.append(Figyelmeztetés(
                    fajl=fajlnev,
                    munkalap=munkalap,
                    sor=excel_sor,
                    oszlop='támogatási azonosító',
                    ertek=ta,
                    magyarazat=(
                        f'A {ta} támogatási azonosítójú gazdálkodó nem szerepel '
                        f'a Gazd_alapadatok.xlsx fájlban.'
                    ),
                ))
                continue

            if ket_azon not in ket_map:
                figyelmeztetesek.append(Figyelmeztetés(
                    fajl=fajlnev,
                    munkalap=munkalap,
                    sor=excel_sor,
                    oszlop='KET azonosító',
                    ertek=ket_azon,
                    magyarazat=(
                        f'A {ket_azon} KET azonosító nem szerepel '
                        f'a KETEK.xlsx fájlban.'
                    ),
                ))
                continue

            # ── Tábla létrehozása (az első előforduláskor) ─────────────────────
            if tablaazon not in tabla_map:
                if mod == 'osszeflzes':
                    meglevo = munkamenet.query(Tablak).filter_by(
                        tablaazonosito=tablaazon
                    ).one_or_none()
                    if meglevo:
                        tabla_map[tablaazon] = meglevo
                    else:
                        t = _uj_tablak(sor, ket_map[ket_azon])
                        munkamenet.add(t)
                        tabla_map[tablaazon] = t
                else:
                    t = _uj_tablak(sor, ket_map[ket_azon])
                    munkamenet.add(t)
                    tabla_map[tablaazon] = t

            kulcs = (ta, tablaazon)

            # ── Trágyázás ─────────────────────────────────────────────────────
            # Duplikált soroknál csak az elsőt vesszük figyelembe.
            tragy_ev_kulcs = f'{tablaazon}:{ev}'
            tr_dat = sor[_TRAGYAZAS_OSZLOP]
            if pd.notna(tr_dat) and isinstance(tr_dat, pd.Timestamp):
                if tragy_ev_kulcs not in tragy_latott_evben:
                    tragyazas[kulcs].append(tr_dat.date())
                    tragy_latott_evben.add(tragy_ev_kulcs)

            # ── Melléktermék beforgatás ────────────────────────────────────────
            mel_dat = sor[_MELLEKTERMEK_OSZLOP]
            if pd.notna(mel_dat) and isinstance(mel_dat, pd.Timestamp):
                mellektermek_dat.setdefault(kulcs, mel_dat.date())

            # ── Középmély lazítás ─────────────────────────────────────────────
            laz_dat = sor[_LAZITAS_OSZLOP]
            if pd.notna(laz_dat) and isinstance(laz_dat, pd.Timestamp):
                lazitas_dat.setdefault(kulcs, laz_dat.date())

    munkamenet.flush()   # tid-ek kiosztása

    # ── 7. Teljesítések létrehozása ───────────────────────────────────────────
    telj_szam = 0

    # Trágyázás → feladatok 1 és 2
    # Legfeljebb 2 esemény: a legkorábbi az 1., a második a 2. feladathoz.
    for (ta, tablaazon), datumok in tragyazas.items():
        t = tabla_map.get(tablaazon)
        if t is None:
            continue
        for eloiras_azon, dat in zip([1, 2], sorted(datumok)):
            v = vallalasok_map.get((ta, eloiras_azon))
            if v is None:
                continue
            if _teljesites_betesz(munkamenet, v, t, dat, mod):
                telj_szam += 1

    # Melléktermék beforgatás → feladat 3
    for (ta, tablaazon), dat in mellektermek_dat.items():
        v = vallalasok_map.get((ta, 3))
        t = tabla_map.get(tablaazon)
        if v and t:
            if _teljesites_betesz(munkamenet, v, t, dat, mod):
                telj_szam += 1

    # Középmély lazítás → feladat 4
    for (ta, tablaazon), dat in lazitas_dat.items():
        v = vallalasok_map.get((ta, 4))
        t = tabla_map.get(tablaazon)
        if v and t:
            if _teljesites_betesz(munkamenet, v, t, dat, mod):
                telj_szam += 1

    munkamenet.commit()

    return ImportOsszegzo(
        gazdalkodok=len(gazd_map),
        ketek=len(ket_map),
        tablak=len(tabla_map),
        teljesitesek=telj_szam,
        figyelmeztetesek=figyelmeztetesek,
    )


# ─── Privát segédfüggvények ───────────────────────────────────────────────────

def _excel_beolvas(ut: Path) -> tuple[str, pd.DataFrame]:
    with pd.ExcelFile(ut, engine='calamine') as xf:
        munkalap = xf.sheet_names[0]
        df = xf.parse(munkalap)
    return munkalap, df


def _torol_mindent(munkamenet: Session) -> None:
    # FK-sorrend: először a gyermekek, aztán a szülők
    munkamenet.execute(delete(Teljesitesek))
    munkamenet.execute(delete(Tablak))
    munkamenet.execute(delete(Vallalasok))
    munkamenet.execute(delete(Ket))
    munkamenet.execute(delete(Gazdalkodo))
    munkamenet.flush()


def _szoveg_vagy_none(ertek: Any) -> str | None:
    try:
        if pd.isna(ertek):
            return None
    except (TypeError, ValueError):
        pass
    s = str(ertek).strip()
    return s if s else None


def _uj_tablak(sor: pd.Series, ket: Ket) -> Tablak:
    t = Tablak(
        tablasorszam=int(sor['táblasorszám']),
        tablaazonosito=str(sor['tábla azonosító']),
        terulet_ha=(
            float(sor['tábla terület [ha]'])
            if pd.notna(sor['tábla terület [ha]']) else None
        ),
    )
    t.ket = ket
    return t


def _teljesites_betesz(
    munkamenet: Session,
    v: Vallalasok,
    t: Tablak,
    dat: date,
    mod: str,
) -> bool:
    """Teljesítés sort illeszt be; összefűzés módban kihagyja, ha már létezik.

    Visszaad True-t, ha valóban beillesztett.
    """
    if mod == 'osszeflzes':
        meglevo = munkamenet.query(Teljesitesek).filter_by(
            vallalasok_vid=v.vid,
            tablak_tid=t.tid,
        ).one_or_none()
        if meglevo:
            return False
    telj = Teljesitesek(
        teljesules_datuma=dat,
        vallalasok_vid=v.vid,
        tablak_tid=t.tid,
    )
    munkamenet.add(telj)
    return True
