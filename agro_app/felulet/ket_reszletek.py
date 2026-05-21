from __future__ import annotations

from datetime import date

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from adatbazis.modellek import Gazdalkodo, Ket, Tablak, Vallalasok
from logika.tabla_logika import (
    GazdalkodoElteres,
    TeljesitesMarLetezik,
    TeljesitesNemTalalhato,
    teljesit,
    visszavon,
)


class KetReszletek(QWidget):
    vissza = pyqtSignal()

    def __init__(
        self,
        munkamenet: Session,
        kid: int,
        tema: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = munkamenet
        self._kid = kid
        self._tema = tema
        self._vallalasok: list[Vallalasok] = []
        self._tablak: list[Tablak] = []
        self._teljesit_map: dict[tuple[int, int], date] = {}
        self._init_ui()
        self._betolt()

    # ── UI felépítése ─────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        fo = QVBoxLayout(self)
        fo.setContentsMargins(16, 12, 16, 12)
        fo.setSpacing(12)

        vissza_sor = QHBoxLayout()
        vissza_gomb = QPushButton('← Vissza')
        vissza_gomb.setFixedWidth(120)
        vissza_gomb.clicked.connect(lambda: self.vissza.emit())
        vissza_sor.addWidget(vissza_gomb)
        vissza_sor.addStretch()
        fo.addLayout(vissza_sor)

        self._cim_cimke = QLabel()
        self._cim_cimke.setObjectName('fo_cim')
        fo.addWidget(self._cim_cimke)

        self._racs = QTableWidget()
        self._racs.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._racs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._racs.verticalHeader().setVisible(True)
        self._racs.setAlternatingRowColors(True)
        self._racs.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._racs.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        fo.addWidget(self._racs, stretch=1)

    # ── Adatbetöltés ─────────────────────────────────────────────────────────

    def _betolt(self) -> None:
        ket = self._db.execute(
            select(Ket)
            .options(
                selectinload(Ket.tablak).selectinload(Tablak.teljesitesek),
                selectinload(Ket.gazdalkodo).selectinload(Gazdalkodo.vallalasok),
            )
            .where(Ket.kid == self._kid)
        ).scalar_one_or_none()

        if ket is None:
            return

        self._cim_cimke.setText(f'KET {ket.ket_azonosito} — {ket.gazdalkodo.nev}')

        self._tablak = sorted(ket.tablak, key=lambda t: t.tablasorszam)
        self._vallalasok = sorted(
            ket.gazdalkodo.vallalasok, key=lambda v: v.eloiras_azonosito
        )

        farmer_vids = {v.vid for v in self._vallalasok}
        self._teljesit_map = {}
        for t in self._tablak:
            for tel in t.teljesitesek:
                if tel.vallalasok_vid in farmer_vids:
                    self._teljesit_map[(tel.vallalasok_vid, t.tid)] = tel.teljesules_datuma

        self._racs.setRowCount(len(self._tablak))
        self._racs.setColumnCount(len(self._vallalasok))

        self._racs.setHorizontalHeaderLabels(
            [v.leiras or str(v.eloiras_azonosito) for v in self._vallalasok]
        )
        self._racs.setVerticalHeaderLabels(
            [t.tablaazonosito for t in self._tablak]
        )

        for sor, tabla in enumerate(self._tablak):
            for oszlop, vallalas in enumerate(self._vallalasok):
                self._racs.setCellWidget(
                    sor, oszlop,
                    self._cella_letrehoz(sor, oszlop, vallalas.vid, tabla.tid),
                )

    def _cella_letrehoz(self, sor: int, oszlop: int, vid: int, tid: int) -> QPushButton:
        datum = self._teljesit_map.get((vid, tid))
        if datum is not None:
            gomb = QPushButton(str(datum))
            gomb.setObjectName('teljesitett_cella')
            gomb.setToolTip('Kattintás a visszavonáshoz')
            gomb.clicked.connect(
                lambda _, v=vid, t=tid, s=sor, o=oszlop: self._visszavon_keres(v, t, s, o)
            )
        else:
            gomb = QPushButton('Teljesít')
            gomb.clicked.connect(
                lambda _, v=vid, t=tid, s=sor, o=oszlop: self._teljesit_keres(v, t, s, o)
            )
        return gomb

    def _cella_frissit(self, sor: int, oszlop: int) -> None:
        vid = self._vallalasok[oszlop].vid
        tid = self._tablak[sor].tid
        self._racs.setCellWidget(sor, oszlop, self._cella_letrehoz(sor, oszlop, vid, tid))

    # ── Teljesítés és visszavonás ─────────────────────────────────────────────

    def _teljesit_keres(self, vid: int, tid: int, sor: int, oszlop: int) -> None:
        vallalas = self._vallalasok[oszlop]
        tabla = self._tablak[sor]

        msg = QMessageBox(self)
        msg.setWindowTitle('Teljesítés megerősítése')
        msg.setText(
            f'Biztosan teljesítettnek jelöli a következő vállalást: '
            f'{vallalas.leiras} a {tabla.tablaazonosito} táblán?'
        )
        igen_gomb = msg.addButton('Igen', QMessageBox.ButtonRole.AcceptRole)
        megse_gomb = msg.addButton('Mégse', QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(megse_gomb)
        msg.exec()

        if msg.clickedButton() != igen_gomb:
            return

        try:
            telj = teljesit(self._db, vid, tid)
            self._teljesit_map[(vid, tid)] = telj.teljesules_datuma
            self._cella_frissit(sor, oszlop)
        except (TeljesitesMarLetezik, GazdalkodoElteres, ValueError) as e:
            hiba = QMessageBox(self)
            hiba.setWindowTitle('Hiba')
            hiba.setText(str(e))
            hiba.exec()

    def _visszavon_keres(self, vid: int, tid: int, sor: int, oszlop: int) -> None:
        vallalas = self._vallalasok[oszlop]
        tabla = self._tablak[sor]

        msg = QMessageBox(self)
        msg.setWindowTitle('Visszavonás megerősítése')
        msg.setText(
            f'Biztosan visszavonja a teljesítést: '
            f'{vallalas.leiras} a {tabla.tablaazonosito} táblán?'
        )
        igen_gomb = msg.addButton('Igen', QMessageBox.ButtonRole.AcceptRole)
        megse_gomb = msg.addButton('Mégse', QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(megse_gomb)
        msg.exec()

        if msg.clickedButton() != igen_gomb:
            return

        try:
            visszavon(self._db, vid, tid)
            self._teljesit_map.pop((vid, tid), None)
            self._cella_frissit(sor, oszlop)
        except (TeljesitesNemTalalhato, ValueError) as e:
            hiba = QMessageBox(self)
            hiba.setWindowTitle('Hiba')
            hiba.setText(str(e))
            hiba.exec()
