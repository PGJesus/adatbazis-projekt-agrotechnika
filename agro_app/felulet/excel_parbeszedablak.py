from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from adatbazis.modellek import Gazdalkodo
from logika.excel_logika import Figyelmeztetés, ImportOsszegzo, importal


class ExcelParbeszedablak(QDialog):
    def __init__(self, munkamenet: Session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = munkamenet
        self._mappa: Path | None = None
        self._van_adat = self._adat_van_e()
        self._osszefuzes_radio: QRadioButton | None = None

        self.setWindowTitle('Excel importálás')
        self.setMinimumWidth(540)
        self._init_ui()

    def _adat_van_e(self) -> bool:
        szam = self._db.execute(
            select(func.count()).select_from(Gazdalkodo)
        ).scalar_one()
        return szam > 0

    # ── UI felépítése ─────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        fo = QVBoxLayout(self)
        fo.setContentsMargins(20, 16, 20, 16)
        fo.setSpacing(12)

        # Mappa kiválasztás
        fo.addWidget(QLabel('Importálandó mappa (az összes Excel fájlt tartalmazza):'))

        mappa_sor = QHBoxLayout()
        self._mappa_cimke = QLabel('(nincs kiválasztva)')
        self._mappa_cimke.setObjectName('szoveg2')
        self._mappa_cimke.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._mappa_cimke.setWordWrap(True)
        talloz_gomb = QPushButton('Tallózás…')
        talloz_gomb.clicked.connect(self._mappa_kivalaszt)
        mappa_sor.addWidget(self._mappa_cimke, stretch=1)
        mappa_sor.addWidget(talloz_gomb)
        fo.addLayout(mappa_sor)

        # Import mód (csak ha már van adat az adatbázisban)
        if self._van_adat:
            mod_cimke = QLabel(
                'Az adatbázis már tartalmaz adatokat. Válasszon importálási módot:'
            )
            mod_cimke.setWordWrap(True)
            fo.addWidget(mod_cimke)

            self._feluliras_radio = QRadioButton(
                'Felülírás — adatbázis törlése és teljes újraépítés'
            )
            self._feluliras_radio.setChecked(True)
            self._osszefuzes_radio = QRadioButton(
                'Összefűzés — meglévő adatok megőrzése, új adatok hozzáadása'
            )
            fo.addWidget(self._feluliras_radio)
            fo.addWidget(self._osszefuzes_radio)

        # Gombok
        self._import_gomb = QPushButton('Importálás')
        self._import_gomb.setEnabled(False)
        self._import_gomb.clicked.connect(self._import_indit)

        megse_gomb = QPushButton('Mégse')
        megse_gomb.clicked.connect(self.reject)

        gomb_sor = QHBoxLayout()
        gomb_sor.addStretch()
        gomb_sor.addWidget(self._import_gomb)
        gomb_sor.addWidget(megse_gomb)
        fo.addLayout(gomb_sor)

    # ── Mappa kiválasztás ─────────────────────────────────────────────────────

    def _mappa_kivalaszt(self) -> None:
        mappa = QFileDialog.getExistingDirectory(
            self, 'Importálandó mappa kiválasztása', str(Path.home())
        )
        if not mappa:
            return
        self._mappa = Path(mappa)
        self._mappa_cimke.setText(str(self._mappa))
        self._import_gomb.setEnabled(True)

    # ── Import futtatás ───────────────────────────────────────────────────────

    def _import_indit(self) -> None:
        if self._mappa is None:
            return

        mod = 'feluliras'
        if self._van_adat and self._osszefuzes_radio is not None:
            if self._osszefuzes_radio.isChecked():
                mod = 'osszeflzes'

        self._import_gomb.setEnabled(False)
        self._import_gomb.setText('Importálás folyamatban…')

        try:
            osszegzo = importal(self._mappa, self._db, mod=mod)
        except Exception as e:
            hiba = QMessageBox(self)
            hiba.setWindowTitle('Import hiba')
            hiba.setText(f'Az import során hiba lépett fel:\n{e}')
            hiba.exec()
            self._import_gomb.setEnabled(True)
            self._import_gomb.setText('Importálás')
            return

        self._eredmeny_mutat(osszegzo)
        self.accept()

    # ── Eredmény / figyelmeztetések dialog ────────────────────────────────────

    def _eredmeny_mutat(self, osszegzo: ImportOsszegzo) -> None:
        eredmeny = QDialog(self)
        eredmeny.setWindowTitle('Import eredménye')
        eredmeny.setMinimumWidth(700)
        eredmeny.setMinimumHeight(360)

        fo = QVBoxLayout(eredmeny)
        fo.setContentsMargins(20, 16, 20, 16)
        fo.setSpacing(8)

        fo.addWidget(QLabel(f'Gazdálkodók betöltve: {osszegzo.gazdalkodok}'))
        fo.addWidget(QLabel(f'KET-ek betöltve: {osszegzo.ketek}'))
        fo.addWidget(QLabel(f'Táblák betöltve: {osszegzo.tablak}'))
        fo.addWidget(QLabel(f'Teljesítések betöltve: {osszegzo.teljesitesek}'))

        if osszegzo.figyelmeztetesek:
            figy_szam = len(osszegzo.figyelmeztetesek)
            fo.addWidget(QLabel(f'Figyelmeztetések ({figy_szam} db):'))

            figy_tabla = QTableWidget()
            figy_tabla.setColumnCount(6)
            figy_tabla.setHorizontalHeaderLabels(
                ['Fájl', 'Munkalap', 'Sor', 'Oszlop', 'Érték', 'Magyarázat']
            )
            figy_tabla.setRowCount(figy_szam)
            figy_tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            figy_tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            figy_tabla.verticalHeader().setVisible(False)
            hh = figy_tabla.horizontalHeader()
            hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

            for i, figy in enumerate(osszegzo.figyelmeztetesek):
                for j, szoveg in enumerate([
                    figy.fajl,
                    figy.munkalap,
                    str(figy.sor),
                    figy.oszlop,
                    str(figy.ertek),
                    figy.magyarazat,
                ]):
                    elem = QTableWidgetItem(szoveg)
                    elem.setFlags(elem.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    figy_tabla.setItem(i, j, elem)

            fo.addWidget(figy_tabla, stretch=1)
        else:
            fo.addWidget(QLabel('Figyelmeztetések: nincs'))

        bezar_gomb = QPushButton('Bezárás')
        bezar_gomb.clicked.connect(eredmeny.accept)
        gomb_sor = QHBoxLayout()
        gomb_sor.addStretch()
        gomb_sor.addWidget(bezar_gomb)
        fo.addLayout(gomb_sor)

        eredmeny.exec()
