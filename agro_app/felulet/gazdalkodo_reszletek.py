from __future__ import annotations

from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
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

from felulet.jelveny import Jelveny
from felulet.stilus import tokenek
from logika.gazdalkodo_logika import egy
from logika.ket_logika import Allapot, allapot, haladas


class KattinthatoTablazat(QTableWidget):
    """QTableWidget mutatóujj-kurzorral és hoverre váltó nyíl-oszloppal."""

    def __init__(self, tema: str) -> None:
        super().__init__()
        self.tema = tema
        self._hovert_sor = -1
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event) -> None:
        index = self.indexAt(event.pos())
        uj_sor = index.row() if index.isValid() else -1
        if uj_sor != self._hovert_sor:
            self._chevron_szin(self._hovert_sor, False)
            self._hovert_sor = uj_sor
            self._chevron_szin(self._hovert_sor, True)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if uj_sor >= 0
            else Qt.CursorShape.ArrowCursor
        )
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._chevron_szin(self._hovert_sor, False)
        self._hovert_sor = -1
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def _chevron_szin(self, sor: int, hovert: bool) -> None:
        if sor < 0 or sor >= self.rowCount():
            return
        elem = self.item(sor, self.columnCount() - 1)
        if elem is None:
            return
        tok = tokenek(self.tema)
        elem.setForeground(QBrush(QColor(tok['TEXT0'] if hovert else tok['TEXT2'])))


class GazdalkodoReszletek(QWidget):
    vissza = pyqtSignal()
    ket_megnyit = pyqtSignal(int)

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
        fo.setContentsMargins(24, 20, 24, 20)
        fo.setSpacing(16)

        vissza_sor = QHBoxLayout()
        vissza_gomb = QPushButton('← Vissza')
        vissza_gomb.setFixedWidth(120)
        vissza_gomb.setCursor(Qt.CursorShape.PointingHandCursor)
        vissza_gomb.clicked.connect(lambda: self.vissza.emit())
        vissza_sor.addWidget(vissza_gomb)
        vissza_sor.addStretch()
        fo.addLayout(vissza_sor)

        fo.addWidget(self._adatkartya_felep())

        elvalaszto = QFrame()
        elvalaszto.setFrameShape(QFrame.Shape.HLine)
        elvalaszto.setObjectName('oldalsav_elvalaszto')
        fo.addWidget(elvalaszto)

        ket_cim = QLabel('KET-ek')
        ket_cim.setObjectName('szekció_cim')
        fo.addWidget(ket_cim)

        self._ket_tabla = KattinthatoTablazat(self._tema)
        self._ket_tabla.setColumnCount(5)
        self._ket_tabla.setHorizontalHeaderLabels(
            ['KET azonosító', 'Terület (ha)', 'Haladás', 'Állapot', '']
        )
        hh = self._ket_tabla.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._ket_tabla.setColumnWidth(4, 32)
        self._ket_tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._ket_tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._ket_tabla.verticalHeader().setVisible(False)
        self._ket_tabla.setAlternatingRowColors(False)
        self._ket_tabla.setShowGrid(False)
        self._ket_tabla.verticalHeader().setDefaultSectionSize(44)
        self._ket_tabla.clicked.connect(self._ket_kattintva)

        fo.addWidget(self._ket_tabla, stretch=1)

    def _adatkartya_felep(self) -> QWidget:
        keret = QWidget()
        el = QVBoxLayout(keret)
        el.setContentsMargins(0, 0, 0, 8)
        el.setSpacing(4)

        self._nev_cimke = QLabel()
        self._nev_cimke.setObjectName('oldal_cim')
        self._cim_cimke   = QLabel()
        self._tel_cimke   = QLabel()
        self._email_cimke = QLabel()
        self._ta_cimke    = QLabel()
        self._ta_cimke.setObjectName('szoveg1')

        for w in (self._nev_cimke, self._cim_cimke, self._tel_cimke,
                  self._email_cimke, self._ta_cimke):
            el.addWidget(w)

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

        self._ket_tabla.tema = self._tema
        self._ket_tabla.setSortingEnabled(False)
        self._ket_tabla.setRowCount(0)

        for k in gazd.ketek:
            keszult, osszesen = haladas(self._db, k.kid)
            all_enum = allapot(self._db, k.kid)

            sor = self._ket_tabla.rowCount()
            self._ket_tabla.insertRow(sor)
            self._ket_tabla.setRowHeight(sor, 44)

            azon_elem = QTableWidgetItem(str(k.ket_azonosito))
            azon_elem.setData(Qt.ItemDataRole.UserRole, k.kid)
            azon_elem.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self._ket_tabla.setItem(sor, 0, azon_elem)

            ter_elem = QTableWidgetItem(f'{k.terulet_ha:.4f}')
            ter_elem.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._ket_tabla.setItem(sor, 1, ter_elem)

            hal_szoveg = f'{keszult}/{osszesen}' if osszesen > 0 else '—'
            hal_elem = QTableWidgetItem(hal_szoveg)
            hal_elem.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._ket_tabla.setItem(sor, 2, hal_elem)

            jelveny = Jelveny(all_enum)
            self._ket_tabla.setCellWidget(sor, 3, self._jelveny_kozepre(jelveny))

            tok = tokenek(self._tema)
            chevron = QTableWidgetItem('›')
            chevron.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            chevron.setFlags(Qt.ItemFlag.ItemIsEnabled)
            f = QFont()
            f.setPointSize(12)
            chevron.setFont(f)
            chevron.setForeground(QBrush(QColor(tok['TEXT2'])))
            self._ket_tabla.setItem(sor, 4, chevron)

        self._ket_tabla.setSortingEnabled(True)

    def _jelveny_kozepre(self, jelveny: Jelveny) -> QWidget:
        tartaly = QWidget()
        tartaly.setStyleSheet('background: transparent;')
        el = QHBoxLayout(tartaly)
        el.setContentsMargins(8, 0, 8, 0)
        el.addStretch()
        el.addWidget(jelveny)
        el.addStretch()
        return tartaly

    def refresh(self) -> None:
        self._betolt()

    # ── Navigáció ─────────────────────────────────────────────────────────────

    def _ket_kattintva(self, index: QModelIndex) -> None:
        elem = self._ket_tabla.item(index.row(), 0)
        if elem is None:
            return
        kid = elem.data(Qt.ItemDataRole.UserRole)
        if kid is not None:
            self.ket_megnyit.emit(kid)
