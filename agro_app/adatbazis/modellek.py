from sqlalchemy import (
    Column, Date, Double, ForeignKey, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.mysql import INTEGER as MySQLINTEGER
from sqlalchemy.orm import DeclarativeBase, relationship


class Alap(DeclarativeBase):
    pass


class Gazdalkodo(Alap):
    __tablename__ = 'gazdalkodo'

    gid = Column(
        MySQLINTEGER(unsigned=True), primary_key=True, autoincrement=True,
        comment='Gazdálkodó azonosító',
    )
    nev = Column(String(150), nullable=False, comment='Gazdálkodó neve')
    cim = Column(String(255), nullable=False, comment='Lakcím')
    telefonszam = Column(String(20), nullable=False, comment='Telefonszám')
    email = Column(String(100), nullable=True, comment='E-mail cím')
    tamogatasi_azonosito = Column(Integer, nullable=False, comment='Támogatási azonosító')

    ketek = relationship('Ket', back_populates='gazdalkodo')
    vallalasok = relationship('Vallalasok', back_populates='gazdalkodo')


class Ket(Alap):
    __tablename__ = 'ket'

    kid = Column(
        MySQLINTEGER(unsigned=True), primary_key=True, autoincrement=True,
        comment='KET azonosító',
    )
    ket_azonosito = Column(Integer, nullable=False, unique=True, comment='KET külső azonosítója')
    terulet_ha = Column(Double, nullable=False, comment='KET teljes területe (ha)')
    gazdalkodo_gid = Column(
        MySQLINTEGER(unsigned=True),
        ForeignKey('gazdalkodo.gid', name='fk_ket_gazdalkodo'),
        nullable=False,
        comment='Gazdálkodó hivatkozás',
    )

    gazdalkodo = relationship('Gazdalkodo', back_populates='ketek')
    tablak = relationship('Tablak', back_populates='ket')


class Tablak(Alap):
    __tablename__ = 'tablak'

    tid = Column(
        MySQLINTEGER(unsigned=True), primary_key=True, autoincrement=True,
        comment='Tábla azonosító',
    )
    tablasorszam = Column(Integer, nullable=False, comment='Admin által adott sorszám')
    tablaazonosito = Column(String(50), nullable=False, comment='Összetett azonosító (Excel importból)')
    terulet_ha = Column(Double, nullable=True, comment='Tábla területe (ha)')
    ket_kid = Column(
        MySQLINTEGER(unsigned=True),
        ForeignKey('ket.kid', name='fk_tablak_ket'),
        nullable=False,
        comment='KET hivatkozás',
    )

    ket = relationship('Ket', back_populates='tablak')
    teljesitesek = relationship('Teljesitesek', back_populates='tabla')


class Vallalasok(Alap):
    __tablename__ = 'vallalasok'

    vid = Column(
        MySQLINTEGER(unsigned=True), primary_key=True, autoincrement=True,
        comment='Vállalás azonosító',
    )
    eloiras_azonosito = Column(Integer, nullable=False, comment='Előírás sorszáma')
    leiras = Column(Text, nullable=True, comment='Vállalás leírása')
    gazdalkodo_gid = Column(
        MySQLINTEGER(unsigned=True),
        ForeignKey('gazdalkodo.gid', name='fk_vallalasok_gazdalkodo'),
        nullable=False,
        comment='Gazdálkodó hivatkozás',
    )

    gazdalkodo = relationship('Gazdalkodo', back_populates='vallalasok')
    teljesitesek = relationship('Teljesitesek', back_populates='vallalasok')


class Teljesitesek(Alap):
    __tablename__ = 'teljesitesek'
    __table_args__ = (
        UniqueConstraint(
            'vallalasok_vid', 'tablak_tid',
            name='uq_vallalasok_tabla',
            comment='Egy vállalás egy táblán csak egyszer teljesíthető',
        ),
    )

    telid = Column(
        MySQLINTEGER(unsigned=True), primary_key=True, autoincrement=True,
        comment='Teljesítés azonosító',
    )
    vallalasok_vid = Column(
        MySQLINTEGER(unsigned=True),
        ForeignKey('vallalasok.vid', name='fk_teljesitesek_vallalasok'),
        nullable=False,
        comment='Vállalás hivatkozás',
    )
    tablak_tid = Column(
        MySQLINTEGER(unsigned=True),
        ForeignKey('tablak.tid', name='fk_teljesitesek_tablak'),
        nullable=False,
        comment='Tábla hivatkozás',
    )
    teljesules_datuma = Column(Date, nullable=False, comment='Teljesítés dátuma')

    vallalasok = relationship('Vallalasok', back_populates='teljesitesek')
    tabla = relationship('Tablak', back_populates='teljesitesek')
