import configparser
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL as MotorURL
from sqlalchemy.orm import sessionmaker, Session

from adatbazis.modellek import Alap

_gyar: Optional[sessionmaker[Session]] = None


def _url_keszit(db: configparser.SectionProxy, adatbazis: str = '') -> MotorURL:
    return MotorURL.create(
        drivername='mysql+mysqlconnector',
        username=db['felhasznalo'],
        password=db['jelszo'],
        host=db['host'],
        port=int(db['port']),
        database=adatbazis or None,
    )


def kapcsolat_inicializal(konfig: configparser.ConfigParser) -> None:
    global _gyar

    db = konfig['adatbazis']
    adatbazis_nev = db['adatbazis_nev']

    # Kapcsolódás adatbázis nélkül, hogy létrehozhassuk a sémát, ha hiányzik.
    alap_motor = create_engine(_url_keszit(db), echo=False)
    with alap_motor.connect() as kapcsolat:
        kapcsolat.execute(
            text(
                f'CREATE SCHEMA IF NOT EXISTS `{adatbazis_nev}`'
                f' DEFAULT CHARACTER SET utf8'
            )
        )
        kapcsolat.commit()
    alap_motor.dispose()

    motor = create_engine(_url_keszit(db, adatbazis_nev), echo=False)
    Alap.metadata.create_all(motor)
    _gyar = sessionmaker(motor)


def munkamenet() -> Session:
    if _gyar is None:
        raise RuntimeError('Az adatbázis kapcsolat nincs inicializálva.')
    return _gyar()
