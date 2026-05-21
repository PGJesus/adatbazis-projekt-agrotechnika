"""
Service layer teszt — futtatás a projekt gyökéréből (import_test.py után):

    python service_test.py

Szükséges: működő MySQL kapcsolat és már importált adat (import_test.py lefutott).
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agro_app'))

from PyQt6.QtWidgets import QApplication
from sqlalchemy import select

from logika.beallitasok import beallitasok_betolt, _ALKALMAZAS_NEV
from adatbazis.kapcsolat import kapcsolat_inicializal, munkamenet as uj_munkamenet
from adatbazis.modellek import Gazdalkodo, Ket, Tablak, Vallalasok, Teljesitesek
from logika.gazdalkodo_logika import keres, osszes, egy
from logika.ket_logika import haladas, allapot, Allapot, aktualis_ablak_vege
from logika.tabla_logika import (
    teljesit, visszavon,
    GazdalkodoElteres, TeljesitesMarLetezik, TeljesitesNemTalalhato,
)


def elvalaszto(cim: str) -> None:
    print()
    print('─' * 60)
    print(f'  {cim}')
    print('─' * 60)


def main() -> None:
    alkalmazas = QApplication(sys.argv)
    alkalmazas.setApplicationName(_ALKALMAZAS_NEV)
    alkalmazas.setOrganizationName('')

    konfig = beallitasok_betolt()
    if konfig is None:
        print('HIBA: Nincs beállítási fájl. Futtasd előbb a main.py-t.')
        sys.exit(1)

    kapcsolat_inicializal(konfig)
    db = uj_munkamenet()

    try:
        _tesztek(db)
    finally:
        db.close()

    print()
    print('Minden teszt sikeresen lefutott.')


def _tesztek(db) -> None:

    # ── aktualis_ablak_vege ───────────────────────────────────────────────────
    elvalaszto('aktualis_ablak_vege')
    ablak = aktualis_ablak_vege()
    print(f'  Mai dátum: {date.today()}')
    print(f'  Aktuális ablak vége: {ablak}')
    assert ablak == date(2029, 12, 31), f'Várt 2029-12-31, kapott {ablak}'
    print('  OK')

    # ── keres: névprefix ──────────────────────────────────────────────────────
    elvalaszto('keres — névprefix')
    eredmenyek = keres(db, 'He')
    print(f'  "He" → {len(eredmenyek)} találat')
    for g in eredmenyek[:5]:
        print(f'    {g.nev} ({g.tamogatasi_azonosito})')
    assert len(eredmenyek) > 0, 'Várt legalább 1 találat "He" keresésre'

    # ── keres: azonosító-prefix ───────────────────────────────────────────────
    elvalaszto('keres — azonosítóprefix')
    # Az első gazdálkodó azonosítójának első 3 jegyével keresünk
    minta = str(eredmenyek[0].tamogatasi_azonosito)[:3]
    ered2 = keres(db, minta)
    print(f'  "{minta}" → {len(ered2)} találat')
    assert len(ered2) > 0
    print('  OK')

    # ── keres: üres keresés ───────────────────────────────────────────────────
    elvalaszto('keres — üres bemenet')
    ered3 = keres(db, '   ')
    assert ered3 == [], f'Várt üres lista, kapott {ered3}'
    print('  Üres keresés → [] OK')

    # ── osszes ────────────────────────────────────────────────────────────────
    elvalaszto('osszes')
    gazd_lista = osszes(db)
    print(f'  Gazdálkodók száma: {len(gazd_lista)}')
    assert len(gazd_lista) == 100, f'Várt 100, kapott {len(gazd_lista)}'
    print(f'  Első: {gazd_lista[0].nev}, KETs száma: {len(gazd_lista[0].ketek)}')
    print('  OK')

    # ── egy ───────────────────────────────────────────────────────────────────
    elvalaszto('egy — teljes betöltés')
    minta_g = gazd_lista[0]
    g = egy(db, minta_g.gid)
    assert g is not None
    print(f'  Gazdálkodó: {g.nev} (gid={g.gid})')
    print(f'  KETs: {len(g.ketek)}')
    print(f'  Vállalások: {len(g.vallalasok)}')
    tabla_szam = sum(len(k.tablak) for k in g.ketek)
    print(f'  Táblák összesen: {tabla_szam}')
    telj_tablaban = sum(len(t.teljesitesek) for k in g.ketek for t in k.tablak)
    telj_vallalas = sum(len(v.teljesitesek) for v in g.vallalasok)
    print(f'  Teljesítések (tábla oldalról): {telj_tablaban}')
    print(f'  Teljesítések (vállalás oldalról): {telj_vallalas}')
    print('  OK')

    # ── haladas ───────────────────────────────────────────────────────────────
    elvalaszto('haladas')
    for k in g.ketek[:3]:
        kesz, osz = haladas(db, k.kid)
        print(f'  KET {k.ket_azonosito}: {kesz}/{osz}')
        assert 0 <= kesz <= osz, f'Érvénytelen haladás: {kesz}/{osz}'
    print('  OK')

    # ── allapot ───────────────────────────────────────────────────────────────
    elvalaszto('allapot (valós mai dátummal)')
    allapot_szamlalo: dict[str, int] = {}
    for k in g.ketek:
        a = allapot(db, k.kid)
        allapot_szamlalo[a.value] = allapot_szamlalo.get(a.value, 0) + 1
    for nev, szam in sorted(allapot_szamlalo.items()):
        print(f'  {nev}: {szam} KET')
    print('  OK')

    elvalaszto('allapot — szimulált dátumok')
    teszt_ket = g.ketek[0]
    kid = teszt_ket.kid
    keszult, osszesen = haladas(db, kid)
    if keszult < osszesen:   # csak nem-teljes KET-en teszteljük
        assert allapot(db, kid, ma=date(2026, 1, 1)) == Allapot.ZOLD,  'Várt ZOLD 2026-01-01'
        assert allapot(db, kid, ma=date(2028, 7, 1)) == Allapot.SARGA, 'Várt SARGA 2028-07-01'
        assert allapot(db, kid, ma=date(2029, 2, 1)) == Allapot.PIROS, 'Várt PIROS 2029-02-01'
        assert allapot(db, kid, ma=date(2030, 1, 1)) == Allapot.SZANKCIO, 'Várt SZANKCIO 2030-01-01'
        print('  ZOLD / SARGA / PIROS / SZANKCIO határok OK')
    else:
        print(f'  KET {teszt_ket.ket_azonosito} már kész, határok teszteléséhez más KET kell')

    # ── teljesit / visszavon ──────────────────────────────────────────────────
    elvalaszto('teljesit és visszavon')

    # Keressünk egy (vid, tid) párt, ami még NEM teljesített
    vallalasok_lista = g.vallalasok
    if not vallalasok_lista:
        print('  KIHAGYVA — gazdálkodónak nincs vállalása')
        return

    tabla_lista = [t for k in g.ketek for t in k.tablak]
    if not tabla_lista:
        print('  KIHAGYVA — gazdálkodónak nincs táblája')
        return

    # Vegyen az első vállalás + táblát, ami még nincs teljesítve
    teszt_vid = vallalasok_lista[0].vid
    teszt_tid = None
    for t in tabla_lista:
        mar_van = db.execute(
            select(Teljesitesek).where(
                Teljesitesek.vallalasok_vid == teszt_vid,
                Teljesitesek.tablak_tid    == t.tid,
            )
        ).scalar_one_or_none()
        if mar_van is None:
            teszt_tid = t.tid
            break

    if teszt_tid is None:
        print('  KIHAGYVA — az összes (vállalás, tábla) pár már teljesített')
        return

    print(f'  Teszt pár: vid={teszt_vid}, tid={teszt_tid}')

    teszt_datum = date(2026, 3, 15)
    telj = teljesit(db, teszt_vid, teszt_tid, datum=teszt_datum)
    print(f'  teljesit() → telid={telj.telid}, dátum={telj.teljesules_datuma}')
    assert telj.teljesules_datuma == teszt_datum

    # Duplikált teljesítés → kivétel
    try:
        teljesit(db, teszt_vid, teszt_tid)
        assert False, 'Várt TeljesitesMarLetezik kivétel'
    except TeljesitesMarLetezik:
        print('  Duplikált teljesítés → TeljesitesMarLetezik OK')

    visszavon(db, teszt_vid, teszt_tid)
    print('  visszavon() OK')

    # Visszavont tétel ismételt visszavonása → kivétel
    try:
        visszavon(db, teszt_vid, teszt_tid)
        assert False, 'Várt TeljesitesNemTalalhato kivétel'
    except TeljesitesNemTalalhato:
        print('  Ismételt visszavon → TeljesitesNemTalalhato OK')

    # Idegen tábla → gazdálkodó-eltérés
    idegen_tabla = db.execute(
        select(Tablak)
        .join(Ket, Tablak.ket_kid == Ket.kid)
        .where(Ket.gazdalkodo_gid != g.gid)
        .limit(1)
    ).scalar_one_or_none()

    if idegen_tabla:
        try:
            teljesit(db, teszt_vid, idegen_tabla.tid)
            assert False, 'Várt GazdalkodoElteres kivétel'
        except GazdalkodoElteres:
            print('  Idegen tábla → GazdalkodoElteres OK')
    else:
        print('  GazdalkodoElteres teszt kihagyva — nincs idegen tábla')


if __name__ == '__main__':
    main()
