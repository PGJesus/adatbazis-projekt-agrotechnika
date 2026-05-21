import configparser
from pathlib import Path

from PyQt6.QtCore import QStandardPaths


_ALKALMAZAS_NEV = 'AgrotechnikaFigyelo'
_KONFIG_FAJL = 'kapcsolat.ini'


def konfig_ut() -> Path:
    konyvtar = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )
    return Path(konyvtar) / _KONFIG_FAJL


def beallitasok_betolt() -> configparser.ConfigParser | None:
    ut = konfig_ut()
    if not ut.exists():
        return None
    konfig = configparser.ConfigParser()
    konfig.read(ut, encoding='utf-8')
    return konfig


def beallitasok_ment(konfig: configparser.ConfigParser) -> None:
    ut = konfig_ut()
    ut.parent.mkdir(parents=True, exist_ok=True)
    with open(ut, 'w', encoding='utf-8') as f:
        konfig.write(f)


def uj_konfig(
    host: str,
    port: str,
    felhasznalo: str,
    jelszo: str,
    adatbazis_nev: str,
    tema: str = 'vilagos',
) -> configparser.ConfigParser:
    konfig = configparser.ConfigParser()
    konfig['adatbazis'] = {
        'host': host,
        'port': port,
        'felhasznalo': felhasznalo,
        'jelszo': jelszo,
        'adatbazis_nev': adatbazis_nev,
    }
    konfig['megjelenes'] = {'tema': tema}
    return konfig
