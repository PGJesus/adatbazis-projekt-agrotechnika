from __future__ import annotations

from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from logika.gazdalkodo_logika import egy
from logika.ket_logika import Allapot, allapot, haladas


_ALLAPOT_SZOVEG: dict[Allapot, str] = {
    Allapot.ZOLD:     'Zöld',
    Allapot.SARGA:    'Sárga',
    Allapot.PIROS:    'Piros',
    Allapot.SZANKCIO: 'Szankció',
    Allapot.KESZ:     'Kész',
}

_ALLAPOT_SZIN: dict[str, dict[Allapot, tuple[str, str]]] = {
    'vilagos': {
        Allapot.ZOLD:     ('#4A7C59', '#FFFFFF'),
        Allapot.SARGA:    ('#D4A017', '#000000'),
        Allapot.PIROS:    ('#C0392B', '#FFFFFF'),
        Allapot.SZANKCIO: ('#6B1A1A', '#FFFFFF'),
        Allapot.KESZ:     ('#4A7C59', '#FFFFFF'),
    },
    'sotet': {
        Allapot.ZOLD:     ('#6BA77B', '#1A1A1A'),
        Allapot.SARGA:    ('#E8B83C', '#1A1A1A'),
        Allapot.PIROS:    ('#E74C3C', '#FFFFFF'),
        Allapot.SZANKCIO: ('#A03030', '#FFFFFF'),
        Allapot.KESZ:     ('#6BA77B', '#1A1A1A'),
    },
}


class GazdalkodoReszletek(QWidget):
    vissza = pyqtSignal()
    ket_megnyit = pyqtSignal(int)   # kid

    def __init__(
        self,
        munkamenet: Session,
        gid: int,
        tema: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = munkamenet
        self._gid = gid
        self._tema = tema
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

        fo.addWidget(self._adatkartya_felep())

        ket_cimke = QLabel('KET-ek')
        ket_cimke.setStyleSheet('font-weight: bold; font-size: 12pt;')
        fo.addWidget(ket_cimke)

        self._ket_tabla = QTableWidget()
        self._ket_tabla.setColumnCount(4)
        self._ket_tabla.setHorizontalHeaderLabels(
            ['KET azonosító', 'Terület (ha)', 'Haladás', 'Állapot']
        )
        hh = self._ket_tabla.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._ket_tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._ket_tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._ket_tabla.verticalHeader().setVisible(False)
        self._ket_tabla.setAlternatingRowColors(True)
        self._ket_tabla.doubleClicked.connect(self._ket_duplakattintva)

        fo.addWidget(self._ket_tabla, stretch=1)

    def _adatkartya_felep(self) -> QWidget:
        keret = QWidget()
        elrendezas = QVBoxLayout(keret)
        elrendezas.setContentsMargins(0, 0, 0, 8)
        elrendezas.setSpacing(4)

        self._nev_cimke   = QLabel()
        self._nev_cimke.setObjectName('fo_cim')
        self._cim_cimke   = QLabel()
        self._tel_cimke   = QLabel()
        self._email_cimke = QLabel()
        self._ta_cimke    = QLabel()
        self._ta_cimke.setObjectName('szoveg2')

        for w in (self._nev_cimke, self._cim_cimke, self._tel_cimke,
                  self._email_cimke, self._ta_cimke):
            elrendezas.addWidget(w)

        return keret

    # ── Adatbetöltés ─────────────────────────────────────────────────────────

    def _betolt(self) -> None:
        gazd = egy(self._db, self._gid)
        if gazd is None:
            return

        self._nev_cimke.setText(gazd.nev)
        self._cim_cimke.setText(f'Lakcím: {gazd.cim}')
        self._tel_cimke.setText(f'Telefon: {gazd.telefonszam}')
        self._email_cimke.setText(f'E-mail: {gazd.email or "—"}')
        self._ta_cimke.setText(f'Támogatási azonosító: {gazd.tamogatasi_azonosito}')

        szint = _ALLAPOT_SZIN.get(self._tema, _ALLAPOT_SZIN['vilagos'])

        self._ket_tabla.setSortingEnabled(False)
        self._ket_tabla.setRowCount(0)

        for k in gazd.ketek:
            keszult, osszesen = haladas(self._db, k.kid)
            all_enum = allapot(self._db, k.kid)

            sor = self._ket_tabla.rowCount()
            self._ket_tabla.insertRow(sor)

            azon_elem = QTableWidgetItem(str(k.ket_azonosito))
            azon_elem.setData(Qt.ItemDataRole.UserRole, k.kid)
            azon_elem.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self._ket_tabla.setItem(sor, 0, azon_elem)

            ter_elem = QTableWidgetItem(f'{k.terulet_ha:.4f}')
            ter_elem.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self._ket_tabla.setItem(sor, 1, ter_elem)

            hal_szoveg = f'{keszult}/{osszesen}' if osszesen > 0 else '—'
            hal_elem = QTableWidgetItem(hal_szoveg)
            hal_elem.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self._ket_tabla.setItem(sor, 2, hal_elem)

            bg_szin, fg_szin = szint.get(all_enum, ('#888888', '#FFFFFF'))
            all_elem = QTableWidgetItem(_ALLAPOT_SZOVEG[all_enum])
            all_elem.setBackground(QBrush(QColor(bg_szin)))
            all_elem.setForeground(QBrush(QColor(fg_szin)))
            all_elem.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            all_elem.setFlags(all_elem.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._ket_tabla.setItem(sor, 3, all_elem)

        self._ket_tabla.setSortingEnabled(True)

    def refresh(self) -> None:
        self._betolt()

    # ── Navigáció ─────────────────────────────────────────────────────────────

    def _ket_duplakattintva(self, index: QModelIndex) -> None:
        elem = self._ket_tabla.item(index.row(), 0)
        if elem is None:
            return
        kid = elem.data(Qt.ItemDataRole.UserRole)
        if kid is not None:
            self.ket_megnyit.emit(kid)
