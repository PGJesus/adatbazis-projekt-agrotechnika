"""
Gyors importteszt — futtatás a projekt gyökéréből:

    cd agro_app
    python ..\import_test.py

Szükséges: működő MySQL kapcsolat (main.py-val már beállított konfig).
"""

import sys
import os

# agro_app csomagok elérhetővé tétele
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agro_app'))

from pathlib import Path

from PyQt6.QtWidgets import QApplication

from logika.beallitasok import beallitasok_betolt, _ALKALMAZAS_NEV
from adatbazis.kapcsolat import kapcsolat_inicializal, munkamenet
from logika.excel_logika import importal, ImportOsszegzo, Figyelmeztetés

TEST_MAPPA = Path(__file__).parent / 'test_data'


def osszegzo_kiir(o: ImportOsszegzo) -> None:
    print()
    print('=' * 60)
    print('  Import összegző')
    print('=' * 60)
    print(f'  Gazdálkodók:  {o.gazdalkodok:>6}')
    print(f'  KETs:         {o.ketek:>6}')
    print(f'  Táblák:       {o.tablak:>6}')
    print(f'  Teljesítések: {o.teljesitesek:>6}')
    print(f'  Figyelmeztetések: {len(o.figyelmeztetesek)}')
    print('=' * 60)

    if o.figyelmeztetesek:
        print()
        print('Figyelmeztetések:')
        for f in o.figyelmeztetesek:
            print(
                f'  [{f.fajl} / {f.munkalap}] '
                f'sor {f.sor}, oszlop „{f.oszlop}", '
                f'érték: {f.ertek!r}'
            )
            print(f'    → {f.magyarazat}')
    else:
        print('  Nincs figyelmeztetés.')
    print()


def main() -> None:
    alkalmazas = QApplication(sys.argv)
    alkalmazas.setApplicationName(_ALKALMAZAS_NEV)
    alkalmazas.setOrganizationName('')

    konfig = beallitasok_betolt()
    if konfig is None:
        print('HIBA: Nincs beállítási fájl. Futtasd előbb a main.py-t.')
        sys.exit(1)

    print('Adatbázishoz kapcsolódás…')
    kapcsolat_inicializal(konfig)
    print('Kapcsolódás sikeres.')

    print(f'Import indítása: {TEST_MAPPA}')
    munkamenet_obj = munkamenet()
    try:
        osszegzo = importal(TEST_MAPPA, munkamenet_obj, mod='feluliras')
    except Exception as kiv:
        munkamenet_obj.rollback()
        print(f'HIBA az import során: {kiv}')
        raise
    finally:
        munkamenet_obj.close()

    osszegzo_kiir(osszegzo)


if __name__ == '__main__':
    main()
