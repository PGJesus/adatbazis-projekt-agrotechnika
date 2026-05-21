from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt, QModelIndex, QStringListModel
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCompleter,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from adatbazis.modellek import Ket, Tablak, Teljesitesek, Vallalasok
from felulet.beallitasok_ablak import BeallitasokAblak
from felulet.stilus import betoltes
from logika.beallitasok import beallitasok_betolt, beallitasok_ment
from logika.gazdalkodo_logika import keres, osszes
from logika.ket_logika import Allapot, aktualis_ablak_vege, _honap_marad


# ─── Állapot megjelenítési konstansok ────────────────────────────────────────

_ALLAPOT_SZOVEG: dict[Allapot, str] = {
    Allapot.ZOLD:     'Zöld',
    Allapot.SARGA:    'Sárga',
    Allapot.PIROS:    'Piros',
    Allapot.SZANKCIO: 'Szankció',
    Allapot.KESZ:     'Kész',
}

# (háttér, előtér) per téma per állapot
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

_ALLAPOT_PRIORITAS: dict[Allapot, int] = {
    Allapot.SZANKCIO: 4,
    Allapot.PIROS:    3,
    Allapot.SARGA:    2,
    Allapot.ZOLD:     1,
    Allapot.KESZ:     0,
}


# ─── FoAblak ─────────────────────────────────────────────────────────────────

class FoAblak(QMainWindow):
    def __init__(self, munkamenet: Session, konfig) -> None:
        super().__init__()
        self._db = munkamenet
        self._konfig = konfig
        self._tema = konfig.get('megjelenes', 'tema', fallback='vilagos')

        # Belső állapot
        self._gazd_adatok: list[dict] = []
        self._tipp_terkep: dict[str, int] = {}   # javaslat szöveg → gid
        self._szurt_gid: int | None = None
        self._kereses_szoveg: str = ''
        self._szuro_allapot: str = 'mind'        # 'mind' | 'teljesitett' | 'nem_teljesitett'

        # Navigációs widgetek
        self._gazd_widget = None
        self._ket_widget  = None

        self._init_ui()
        self._betolt()

    # ── UI felépítése ─────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle('Agrotechnika Figyelő')
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        self._eszkoztar_felep()
        self._kozponti_widget_felep()

    def _eszkoztar_felep(self) -> None:
        eszk = QToolBar()
        eszk.setMovable(False)
        eszk.setFloatable(False)
        self.addToolBar(eszk)

        cim = QLabel('Agrotechnika Figyelő')
        cim.setObjectName('fo_cim')
        eszk.addWidget(cim)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        eszk.addWidget(spacer)

        self._tema_gomb = QPushButton(self._tema_gomb_felirat())
        self._tema_gomb.setToolTip('Téma váltása')
        self._tema_gomb.clicked.connect(self._tema_valtas)
        eszk.addWidget(self._tema_gomb)

        eszk.addSeparator()

        import_gomb = QPushButton('Importálás')
        import_gomb.setToolTip('Adatok importálása Excel fájlokból')
        import_gomb.clicked.connect(self._import_megnyit)
        eszk.addWidget(import_gomb)

        export_gomb = QPushButton('Exportálás')
        export_gomb.setToolTip('Adatok exportálása Excel fájlokba')
        export_gomb.clicked.connect(lambda: None)   # no-op
        eszk.addWidget(export_gomb)

        eszk.addSeparator()

        beall_gomb = QPushButton('Beállítások')
        beall_gomb.setToolTip('Adatbázis kapcsolat és téma beállítása')
        beall_gomb.clicked.connect(self._beallitasok_megnyit)
        eszk.addWidget(beall_gomb)

    def _kozponti_widget_felep(self) -> None:
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        dashboard = QWidget()
        self._stack.addWidget(dashboard)   # index 0 — mindig itt marad

        fo = QVBoxLayout(dashboard)
        fo.setContentsMargins(16, 12, 16, 12)
        fo.setSpacing(10)

        # ── Keresősor ──────────────────────────────────────────────────────
        kereses_sor = QHBoxLayout()
        kereses_sor.setSpacing(8)

        self._kereses_mezo = QLineEdit()
        self._kereses_mezo.setPlaceholderText('Keresés neve vagy támogatási azonosítója alapján…')
        self._kereses_mezo.setClearButtonEnabled(True)

        self._kompleter_modell = QStringListModel()
        self._kompleter = QCompleter(self._kompleter_modell, self)
        self._kompleter.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._kompleter.setCompletionMode(
            QCompleter.CompletionMode.UnfilteredPopupCompletion
        )
        self._kereses_mezo.setCompleter(self._kompleter)

        self._kereses_mezo.textChanged.connect(self._kereses_valtozas)
        self._kompleter.activated.connect(self._kompleter_kivalasztva)

        osszes_gomb = QPushButton('Összes mutatása')
        osszes_gomb.setToolTip('Keresés törlése, összes gazdálkodó megjelenítése')
        osszes_gomb.clicked.connect(self._kereses_torol)

        kereses_sor.addWidget(self._kereses_mezo, stretch=1)
        kereses_sor.addWidget(osszes_gomb)

        # ── Szűrősor ───────────────────────────────────────────────────────
        szuro_sor = QHBoxLayout()
        szuro_sor.setSpacing(8)

        self._szuro_csoport = QButtonGroup(self)
        self._szuro_csoport.setExclusive(True)

        for felirat, azon, szuro in [
            ('Mind',             0, 'mind'),
            ('Teljesített',      1, 'teljesitett'),
            ('Nem teljesített',  2, 'nem_teljesitett'),
        ]:
            gomb = QPushButton(felirat)
            gomb.setObjectName('szuro')
            gomb.setCheckable(True)
            gomb.setChecked(azon == 0)
            gomb.setProperty('szuro_allapot', szuro)
            self._szuro_csoport.addButton(gomb, azon)
            szuro_sor.addWidget(gomb)

        szuro_sor.addStretch()

        self._szuro_csoport.idClicked.connect(self._szuro_valtozas)

        # ── Táblázat ───────────────────────────────────────────────────────
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(4)
        self._tabla.setHorizontalHeaderLabels(
            ['Gazdálkodó neve', 'Tám. azonosító', 'Haladás', 'Állapot']
        )
        self._tabla.horizontalHeader().setStretchLastSection(False)
        self._tabla.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._tabla.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._tabla.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._tabla.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tabla.setSortingEnabled(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.setShowGrid(True)
        self._tabla.doubleClicked.connect(self._sor_duplakattintva)

        fo.addLayout(kereses_sor)
        fo.addLayout(szuro_sor)
        fo.addWidget(self._tabla)

    # ── Adatbetöltés ─────────────────────────────────────────────────────────

    def _betolt(self) -> None:
        """Betölti az összes gazdálkodó összesített haladását 4 kötegelt lekérdezéssel."""
        gazdalkodok = osszes(self._db)   # selectinload(ketek) már bent van

        # Vállalások száma gazdálkodónként
        gazd_vall_szam: dict[int, int] = dict(
            self._db.execute(
                select(Vallalasok.gazdalkodo_gid, func.count().label('szam'))
                .group_by(Vallalasok.gazdalkodo_gid)
            ).all()
        )

        # Táblák száma KET-enként
        ket_tabla_szam: dict[int, int] = dict(
            self._db.execute(
                select(Tablak.ket_kid, func.count().label('szam'))
                .group_by(Tablak.ket_kid)
            ).all()
        )

        # Teljesített párok száma KET-enként
        ket_keszult: dict[int, int] = dict(
            self._db.execute(
                select(Tablak.ket_kid, func.count().label('keszult'))
                .select_from(Teljesitesek)
                .join(Vallalasok, Teljesitesek.vallalasok_vid == Vallalasok.vid)
                .join(Tablak,    Teljesitesek.tablak_tid     == Tablak.tid)
                .join(Ket,       Tablak.ket_kid              == Ket.kid)
                .where(Vallalasok.gazdalkodo_gid == Ket.gazdalkodo_gid)
                .group_by(Tablak.ket_kid)
            ).all()
        )

        ma = date.today()
        ablak_vege = aktualis_ablak_vege(ma)
        ablak_vege_mult = ma > ablak_vege
        honapok = _honap_marad(ma, ablak_vege)

        self._gazd_adatok = []
        for g in gazdalkodok:
            vall_szam = gazd_vall_szam.get(g.gid, 0)
            ossz_keszult = 0
            ossz_osszesen = 0
            legrosszabb = Allapot.KESZ

            for k in g.ketek:
                tab_szam  = ket_tabla_szam.get(k.kid, 0)
                keszult   = ket_keszult.get(k.kid, 0)
                osszesen  = vall_szam * tab_szam

                ossz_keszult  += keszult
                ossz_osszesen += osszesen

                if osszesen > 0 and keszult >= osszesen:
                    ket_allapot = Allapot.KESZ
                elif ablak_vege_mult:
                    ket_allapot = Allapot.SZANKCIO
                elif honapok <= 12:
                    ket_allapot = Allapot.PIROS
                elif honapok <= 18:
                    ket_allapot = Allapot.SARGA
                else:
                    ket_allapot = Allapot.ZOLD

                if _ALLAPOT_PRIORITAS[ket_allapot] > _ALLAPOT_PRIORITAS[legrosszabb]:
                    legrosszabb = ket_allapot

            self._gazd_adatok.append({
                'gid':                    g.gid,
                'nev':                    g.nev,
                'tamogatasi_azonosito':   g.tamogatasi_azonosito,
                'ta_str':                 str(g.tamogatasi_azonosito),
                'ossz_keszult':           ossz_keszult,
                'ossz_osszesen':          ossz_osszesen,
                'keszult_e':              ossz_osszesen > 0 and ossz_keszult >= ossz_osszesen,
                'legrosszabb_allapot':    legrosszabb,
            })

        self._frissit_tabla()

    # ── Táblázat frissítése ───────────────────────────────────────────────────

    def _frissit_tabla(self) -> None:
        szoveg = self._kereses_szoveg.lower()
        szint = _ALLAPOT_SZIN.get(self._tema, _ALLAPOT_SZIN['vilagos'])

        szurt: list[dict] = []
        for adat in self._gazd_adatok:
            # Keresési szűrő
            if self._szurt_gid is not None:
                if adat['gid'] != self._szurt_gid:
                    continue
            elif szoveg:
                if not (
                    szoveg in adat['nev'].lower()
                    or adat['ta_str'].startswith(szoveg)
                ):
                    continue

            # Állapot szűrő
            if self._szuro_allapot == 'teljesitett' and not adat['keszult_e']:
                continue
            if self._szuro_allapot == 'nem_teljesitett' and adat['keszult_e']:
                continue

            szurt.append(adat)

        self._tabla.setSortingEnabled(False)
        self._tabla.setRowCount(0)

        for adat in szurt:
            sor = self._tabla.rowCount()
            self._tabla.insertRow(sor)

            # Gazdálkodó neve (tárolja a gid-et is)
            nev_elem = QTableWidgetItem(adat['nev'])
            nev_elem.setData(Qt.ItemDataRole.UserRole, adat['gid'])
            self._tabla.setItem(sor, 0, nev_elem)

            # Támogatási azonosító (numerikus rendezéshez int-ként is tároljuk)
            ta_elem = QTableWidgetItem()
            ta_elem.setData(Qt.ItemDataRole.DisplayRole, adat['tamogatasi_azonosito'])
            ta_elem.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self._tabla.setItem(sor, 1, ta_elem)

            # Haladás (X/Y)
            hal_szoveg = (
                f'{adat["ossz_keszult"]}/{adat["ossz_osszesen"]}'
                if adat['ossz_osszesen'] > 0 else '—'
            )
            hal_elem = QTableWidgetItem(hal_szoveg)
            hal_elem.setData(Qt.ItemDataRole.UserRole, adat['ossz_keszult'])  # rendezéshez
            hal_elem.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self._tabla.setItem(sor, 2, hal_elem)

            # Állapot jelvény (szín a cell háttérén)
            all_enum = adat['legrosszabb_allapot']
            bg_szin, fg_szin = szint.get(all_enum, ('#888888', '#FFFFFF'))
            all_elem = QTableWidgetItem(_ALLAPOT_SZOVEG[all_enum])
            all_elem.setBackground(QBrush(QColor(bg_szin)))
            all_elem.setForeground(QBrush(QColor(fg_szin)))
            all_elem.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            all_elem.setFlags(all_elem.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._tabla.setItem(sor, 3, all_elem)

        self._tabla.setSortingEnabled(True)

    # ── Keresés és autocomplete ───────────────────────────────────────────────

    def _kereses_valtozas(self, szoveg: str) -> None:
        self._szurt_gid = None
        self._kereses_szoveg = szoveg.strip()

        gazdak = keres(self._db, szoveg)
        self._tipp_terkep = {g.nev: g.gid for g in gazdak}
        self._kompleter_modell.setStringList(list(self._tipp_terkep))

        self._frissit_tabla()

    def _kompleter_kivalasztva(self, kivalasztott: str) -> None:
        """Felhasználó kiválasztott egy javaslatot — szűkíts erre a gazdálkodóra."""
        gid = self._tipp_terkep.get(kivalasztott)
        self._szurt_gid = gid

        # Megakadályozzuk, hogy a setText újra triggerelje a keresőt
        self._kereses_mezo.blockSignals(True)
        self._kereses_mezo.setText(kivalasztott)
        self._kereses_mezo.blockSignals(False)

        self._frissit_tabla()

    def _kereses_torol(self) -> None:
        self._szurt_gid = None
        self._kereses_szoveg = ''
        self._kompleter_modell.setStringList([])
        self._kereses_mezo.blockSignals(True)
        self._kereses_mezo.clear()
        self._kereses_mezo.blockSignals(False)
        self._frissit_tabla()

    # ── Szűrő chipek ─────────────────────────────────────────────────────────

    def _szuro_valtozas(self, gomb_id: int) -> None:
        gomb = self._szuro_csoport.button(gomb_id)
        if gomb:
            self._szuro_allapot = gomb.property('szuro_allapot')
        self._frissit_tabla()

    # ── Dupla kattintás a táblán ──────────────────────────────────────────────

    def _sor_duplakattintva(self, index: QModelIndex) -> None:
        nev_elem = self._tabla.item(index.row(), 0)
        if nev_elem is None:
            return
        gid = nev_elem.data(Qt.ItemDataRole.UserRole)
        if gid is not None:
            self._gazd_megnyit(gid)

    # ── Navigáció ─────────────────────────────────────────────────────────────

    def _gazd_megnyit(self, gid: int) -> None:
        from felulet.gazdalkodo_reszletek import GazdalkodoReszletek
        if self._gazd_widget is not None:
            self._stack.removeWidget(self._gazd_widget)
            self._gazd_widget.deleteLater()
        self._gazd_widget = GazdalkodoReszletek(self._db, gid, self._tema)
        self._gazd_widget.vissza.connect(self._vissza_dashboardra)
        self._gazd_widget.ket_megnyit.connect(self._ket_megnyit)
        self._stack.addWidget(self._gazd_widget)
        self._stack.setCurrentWidget(self._gazd_widget)

    def _ket_megnyit(self, kid: int) -> None:
        from felulet.ket_reszletek import KetReszletek
        if self._ket_widget is not None:
            self._stack.removeWidget(self._ket_widget)
            self._ket_widget.deleteLater()
        self._ket_widget = KetReszletek(self._db, kid, self._tema)
        self._ket_widget.vissza.connect(self._vissza_gazd_reszletekre)
        self._stack.addWidget(self._ket_widget)
        self._stack.setCurrentWidget(self._ket_widget)

    def _vissza_dashboardra(self) -> None:
        if self._ket_widget is not None:
            self._stack.removeWidget(self._ket_widget)
            self._ket_widget.deleteLater()
            self._ket_widget = None
        if self._gazd_widget is not None:
            self._stack.removeWidget(self._gazd_widget)
            self._gazd_widget.deleteLater()
            self._gazd_widget = None
        self._stack.setCurrentIndex(0)
        self._betolt()

    def _vissza_gazd_reszletekre(self) -> None:
        if self._ket_widget is not None:
            self._stack.removeWidget(self._ket_widget)
            self._ket_widget.deleteLater()
            self._ket_widget = None
        if self._gazd_widget is not None:
            self._stack.setCurrentWidget(self._gazd_widget)
            self._gazd_widget.refresh()

    # ── Import ────────────────────────────────────────────────────────────────

    def _import_megnyit(self) -> None:
        from felulet.excel_parbeszedablak import ExcelParbeszedablak
        parbeszed = ExcelParbeszedablak(self._db, parent=self)
        if parbeszed.exec() == QDialog.DialogCode.Accepted:
            self._betolt()

    # ── Téma ─────────────────────────────────────────────────────────────────

    def _tema_gomb_felirat(self) -> str:
        return 'Sötét mód' if self._tema == 'vilagos' else 'Világos mód'

    def _tema_valtas(self) -> None:
        self._tema = 'sotet' if self._tema == 'vilagos' else 'vilagos'
        self._konfig.set('megjelenes', 'tema', self._tema)
        beallitasok_ment(self._konfig)
        QApplication.instance().setStyleSheet(betoltes(self._tema))
        self._tema_gomb.setText(self._tema_gomb_felirat())
        # Táblázat újrafestése az új színekkel
        self._frissit_tabla()

    # ── Beállítások ───────────────────────────────────────────────────────────

    def _beallitasok_megnyit(self) -> None:
        ablak = BeallitasokAblak(konfig=self._konfig, parent=self)
        if ablak.exec() == QDialog.DialogCode.Accepted:
            self._konfig = beallitasok_betolt()
            self._tema = self._konfig.get('megjelenes', 'tema', fallback='vilagos')
            QApplication.instance().setStyleSheet(betoltes(self._tema))
            self._tema_gomb.setText(self._tema_gomb_felirat())
            self._frissit_tabla()
