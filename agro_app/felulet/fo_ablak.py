from __future__ import annotations

from datetime import date

from PyQt6.QtCore import (
    QEasingCurve,
    QModelIndex,
    QPropertyAnimation,
    QStringListModel,
    Qt,
)
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCompleter,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from adatbazis.modellek import Ket, Tablak, Teljesitesek, Vallalasok
from felulet.beallitasok_ablak import BeallitasokAblak
from felulet.jelveny import Jelveny
from felulet.stilus import betoltes, tokenek
from logika.beallitasok import beallitasok_betolt, beallitasok_ment
from logika.gazdalkodo_logika import keres, osszes
from logika.ket_logika import Allapot, aktualis_ablak_vege, _honap_marad


_ALLAPOT_PRIORITAS: dict[Allapot, int] = {
    Allapot.SZANKCIO: 4,
    Allapot.PIROS:    3,
    Allapot.SARGA:    2,
    Allapot.ZOLD:     1,
    Allapot.KESZ:     0,
}

_OLDALSAV_NYITOTT  = 240
_OLDALSAV_ZART     = 52
_ANIMACIO_MS       = 180


# ─── Oldalsáv ─────────────────────────────────────────────────────────────────

class Oldalsav(QFrame):
    def __init__(self, fo_ablak: 'FoAblak') -> None:
        super().__init__(fo_ablak)
        self.setObjectName('oldalsav')
        self._fo = fo_ablak
        self._nyitott = True
        self._nav_gombok: list[QPushButton] = []
        self._nav_cimkek: list[QLabel] = []
        self._alkalmazas_nev_cimke: QLabel | None = None
        self._becsuk_gomb: QPushButton | None = None
        self._init_ui()
        self.setFixedWidth(_OLDALSAV_NYITOTT)

    def _init_ui(self) -> None:
        fo = QVBoxLayout(self)
        fo.setContentsMargins(8, 12, 8, 12)
        fo.setSpacing(2)

        # ── Fejléc (ikon + név) ──
        fejlec = QHBoxLayout()
        fejlec.setSpacing(10)

        ikon_cimke = QLabel('⬛')
        ikon_cimke.setFixedSize(24, 24)
        ikon_cimke.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ikon_cimke.setStyleSheet('color: #4A7C59; font-size: 16px; background: transparent;')

        self._alkalmazas_nev_cimke = QLabel('Agrotechnika Figyelő')
        self._alkalmazas_nev_cimke.setObjectName('alkalmazas_nev')

        fejlec.addWidget(ikon_cimke)
        fejlec.addWidget(self._alkalmazas_nev_cimke, stretch=1)
        fo.addLayout(fejlec)
        fo.addSpacing(8)

        # ── Navigáció ──
        self._sor_felep(fo, '⊞', 'Áttekintés',  self._fo._mutass_attekintest, checked=True)
        self._sor_felep(fo, '👤', 'Gazdálkodók', self._fo._mutass_attekintest)

        self._elvalaszto_felep(fo)

        self._sor_felep(fo, '↑', 'Importálás', self._fo._import_megnyit)
        self._sor_felep(fo, '↓', 'Exportálás', self._fo._export_megnyit)

        self._elvalaszto_felep(fo)

        self._sor_felep(fo, '⚙', 'Beállítások', self._fo._beallitasok_megnyit)

        fo.addStretch()

        # ── Alul: téma + összecsukás ──
        self._tema_gomb = self._gomb_letrehoz('☀', self._fo._tema_valtas)
        self._tema_gomb.setObjectName('nav_elem')
        self._tema_cimke = QLabel(self._tema_felirat())
        self._tema_cimke.setStyleSheet('color: inherit; background: transparent; font-size: 10pt;')

        tema_sor = QHBoxLayout()
        tema_sor.setSpacing(10)
        tema_sor.addWidget(self._tema_gomb)
        tema_sor.addWidget(self._tema_cimke, stretch=1)
        fo.addLayout(tema_sor)

        self._becsuk_gomb = self._gomb_letrehoz('‹', self._osszecsukas_kapcsol)
        self._becsuk_gomb.setObjectName('nav_elem')
        self._becsuk_cimke = QLabel('Összecsukás')
        self._becsuk_cimke.setStyleSheet('color: inherit; background: transparent; font-size: 10pt;')

        becsuk_sor = QHBoxLayout()
        becsuk_sor.setSpacing(10)
        becsuk_sor.addWidget(self._becsuk_gomb)
        becsuk_sor.addWidget(self._becsuk_cimke, stretch=1)
        fo.addLayout(becsuk_sor)

        self._nav_cimkek.append(self._tema_cimke)
        self._nav_cimkek.append(self._becsuk_cimke)

    def _elvalaszto_felep(self, fo: QVBoxLayout) -> None:
        vo = QFrame()
        vo.setObjectName('oldalsav_elvalaszto')
        vo.setFrameShape(QFrame.Shape.HLine)
        fo.addSpacing(4)
        fo.addWidget(vo)
        fo.addSpacing(4)

    def _gomb_letrehoz(self, ikon: str, slot) -> QPushButton:
        g = QPushButton(ikon)
        g.setFixedSize(36, 40)
        g.setCheckable(False)
        g.clicked.connect(slot)
        return g

    def _sor_felep(self, fo: QVBoxLayout, ikon: str, felirat: str, slot, checked: bool = False) -> None:
        sor = QHBoxLayout()
        sor.setSpacing(10)
        sor.setContentsMargins(0, 0, 0, 0)

        gomb = QPushButton(ikon)
        gomb.setObjectName('nav_elem')
        gomb.setFixedSize(36, 40)
        gomb.setCheckable(True)
        gomb.setChecked(checked)
        gomb.setToolTip(felirat)
        gomb.clicked.connect(lambda _, s=slot: self._nav_kattintva(s))

        cimke = QLabel(felirat)
        cimke.setStyleSheet('color: inherit; background: transparent; font-size: 10pt;')

        sor.addWidget(gomb)
        sor.addWidget(cimke, stretch=1)
        fo.addLayout(sor)

        self._nav_gombok.append(gomb)
        self._nav_cimkek.append(cimke)

    def _nav_kattintva(self, slot) -> None:
        for g in self._nav_gombok:
            g.setChecked(False)
        sender = self.sender()
        if isinstance(sender, QPushButton):
            sender.setChecked(True)
        slot()

    def _tema_felirat(self) -> str:
        return 'Sötét mód' if self._fo._tema == 'vilagos' else 'Világos mód'

    def tema_frissit(self) -> None:
        self._tema_cimke.setText(self._tema_felirat())

    def _osszecsukas_kapcsol(self) -> None:
        self._nyitott = not self._nyitott
        cel_sz = _OLDALSAV_NYITOTT if self._nyitott else _OLDALSAV_ZART

        anim = QPropertyAnimation(self, b'minimumWidth', self)
        anim.setDuration(_ANIMACIO_MS)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(self.width())
        anim.setEndValue(cel_sz)

        anim2 = QPropertyAnimation(self, b'maximumWidth', self)
        anim2.setDuration(_ANIMACIO_MS)
        anim2.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim2.setStartValue(self.width())
        anim2.setEndValue(cel_sz)

        for cimke in self._nav_cimkek:
            cimke.setVisible(self._nyitott)
        if self._alkalmazas_nev_cimke:
            self._alkalmazas_nev_cimke.setVisible(self._nyitott)

        if self._becsuk_gomb:
            self._becsuk_gomb.setText('›' if not self._nyitott else '‹')

        anim.start()
        anim2.start()
        self._animaciok = (anim, anim2)


# ─── FoAblak ─────────────────────────────────────────────────────────────────

class FoAblak(QMainWindow):
    def __init__(self, munkamenet: Session, konfig) -> None:
        super().__init__()
        self._db = munkamenet
        self._konfig = konfig
        self._tema = konfig.get('megjelenes', 'tema', fallback='vilagos')

        self._gazd_adatok: list[dict] = []
        self._tipp_terkep: dict[str, int] = {}
        self._szurt_gid: int | None = None
        self._kereses_szoveg: str = ''
        self._szuro_allapot: str = 'mind'

        self._gazd_widget = None
        self._ket_widget  = None

        self._init_ui()
        self._betolt()

    # ── UI felépítése ─────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle('Agrotechnika Figyelő')
        self.setMinimumSize(900, 600)
        self.resize(1200, 750)

        gyoker = QWidget()
        self.setCentralWidget(gyoker)

        foszint = QHBoxLayout(gyoker)
        foszint.setContentsMargins(0, 0, 0, 0)
        foszint.setSpacing(0)

        self._oldalsav = Oldalsav(self)
        foszint.addWidget(self._oldalsav)

        tartalom = QWidget()
        tartalom_fo = QVBoxLayout(tartalom)
        tartalom_fo.setContentsMargins(0, 0, 0, 0)
        tartalom_fo.setSpacing(0)

        self._felso_sav = self._felso_sav_felep()
        tartalom_fo.addWidget(self._felso_sav)

        self._stack = QStackedWidget()
        tartalom_fo.addWidget(self._stack, stretch=1)

        foszint.addWidget(tartalom, stretch=1)

        self._dashboard_felep()

    def _felso_sav_felep(self) -> QFrame:
        sav = QFrame()
        sav.setObjectName('felso_sav')
        el = QHBoxLayout(sav)
        el.setContentsMargins(24, 0, 24, 0)

        self._oldal_cim = QLabel('Áttekintés')
        self._oldal_cim.setObjectName('oldal_cim')
        el.addWidget(self._oldal_cim)
        el.addStretch()
        return sav

    def _dashboard_felep(self) -> None:
        dashboard = QWidget()
        self._stack.addWidget(dashboard)

        fo = QVBoxLayout(dashboard)
        fo.setContentsMargins(24, 20, 24, 20)
        fo.setSpacing(16)

        # ── Stat kártyák ──
        stat_sor = QHBoxLayout()
        stat_sor.setSpacing(12)
        self._gazd_szam_lab   = self._stat_kartya_felep(stat_sor, 'GAZDÁLKODÓK', '—')
        self._teljesit_lab    = self._stat_kartya_felep(stat_sor, 'TELJESÍTVE', '—')
        self._kozeledik_lab   = self._stat_kartya_felep(stat_sor, 'KÖZELEDIK', '0')
        self._szankcio_lab    = self._stat_kartya_felep(stat_sor, 'SZANKCIÓ', '0')
        fo.addLayout(stat_sor)

        # ── Keresősor ──
        self._kereses_mezo = QLineEdit()
        self._kereses_mezo.setPlaceholderText('Keresés neve vagy támogatási azonosítója alapján…')
        self._kereses_mezo.setClearButtonEnabled(True)

        self._kompleter_modell = QStringListModel()
        self._kompleter = QCompleter(self._kompleter_modell, self)
        self._kompleter.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._kompleter.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self._kereses_mezo.setCompleter(self._kompleter)
        self._kereses_mezo.textChanged.connect(self._kereses_valtozas)
        self._kompleter.activated.connect(self._kompleter_kivalasztva)

        fo.addWidget(self._kereses_mezo)

        # ── Szűrő chipek ──
        szuro_sor = QHBoxLayout()
        szuro_sor.setSpacing(8)
        self._szuro_csoport = QButtonGroup(self)
        self._szuro_csoport.setExclusive(True)
        for felirat, azon, allapot_str in [
            ('Mind',            0, 'mind'),
            ('Teljesített',     1, 'teljesitett'),
            ('Nem teljesített', 2, 'nem_teljesitett'),
        ]:
            g = QPushButton(felirat)
            g.setObjectName('szuro')
            g.setCheckable(True)
            g.setChecked(azon == 0)
            g.setProperty('szuro_allapot', allapot_str)
            self._szuro_csoport.addButton(g, azon)
            szuro_sor.addWidget(g)
        szuro_sor.addStretch()
        self._szuro_csoport.idClicked.connect(self._szuro_valtozas)
        fo.addLayout(szuro_sor)

        # ── Táblázat ──
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(4)
        self._tabla.setHorizontalHeaderLabels(
            ['Gazdálkodó neve', 'Tám. azonosító', 'Haladás', 'Állapot']
        )
        hh = self._tabla.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._tabla.setColumnWidth(1, 140)
        self._tabla.setColumnWidth(2, 100)
        self._tabla.setColumnWidth(3, 160)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tabla.setSortingEnabled(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setAlternatingRowColors(False)
        self._tabla.setShowGrid(False)
        self._tabla.verticalHeader().setDefaultSectionSize(44)
        self._tabla.clicked.connect(self._sor_kattintva)

        fo.addWidget(self._tabla)

    def _stat_kartya_felep(self, sor: QHBoxLayout, cimke: str, ertek: str) -> QLabel:
        kartya = QFrame()
        kartya.setObjectName('stat_kartya')
        kartya.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        el = QVBoxLayout(kartya)
        el.setContentsMargins(20, 16, 20, 16)
        el.setSpacing(8)

        cimke_lab = QLabel(cimke)
        cimke_lab.setObjectName('szoveg2')

        ertek_lab = QLabel(ertek)
        ertek_lab.setStyleSheet(
            'font-size: 20pt; font-weight: 600; background: transparent; color: inherit;'
        )

        el.addWidget(cimke_lab)
        el.addWidget(ertek_lab)
        el.addStretch()

        sor.addWidget(kartya)
        return ertek_lab

    # ── Adatbetöltés ─────────────────────────────────────────────────────────

    def _betolt(self) -> None:
        gazdalkodok = osszes(self._db)

        gazd_vall_szam: dict[int, int] = dict(
            self._db.execute(
                select(Vallalasok.gazdalkodo_gid, func.count().label('szam'))
                .group_by(Vallalasok.gazdalkodo_gid)
            ).all()
        )
        ket_tabla_szam: dict[int, int] = dict(
            self._db.execute(
                select(Tablak.ket_kid, func.count().label('szam'))
                .group_by(Tablak.ket_kid)
            ).all()
        )
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

        ossz_szukseges = 0
        ossz_teljesitett = 0
        kozeledik_szam = 0
        szankcio_szam = 0

        self._gazd_adatok = []
        for g in gazdalkodok:
            vall_szam = gazd_vall_szam.get(g.gid, 0)
            ossz_keszult = 0
            ossz_osszesen = 0
            legrosszabb = Allapot.KESZ
            van_kozeledik = False
            van_szankcio = False

            for k in g.ketek:
                tab_szam = ket_tabla_szam.get(k.kid, 0)
                keszult  = ket_keszult.get(k.kid, 0)
                osszesen = vall_szam * tab_szam

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
                if ket_allapot in (Allapot.SARGA, Allapot.PIROS):
                    van_kozeledik = True
                if ket_allapot == Allapot.SZANKCIO:
                    van_szankcio = True

            ossz_szukseges   += ossz_osszesen
            ossz_teljesitett += ossz_keszult
            if van_kozeledik:
                kozeledik_szam += 1
            if van_szankcio:
                szankcio_szam += 1

            self._gazd_adatok.append({
                'gid':                  g.gid,
                'nev':                  g.nev,
                'tamogatasi_azonosito': g.tamogatasi_azonosito,
                'ta_str':               str(g.tamogatasi_azonosito),
                'ossz_keszult':         ossz_keszult,
                'ossz_osszesen':        ossz_osszesen,
                'keszult_e':            ossz_osszesen > 0 and ossz_keszult >= ossz_osszesen,
                'legrosszabb_allapot':  legrosszabb,
            })

        # Stat kártyák
        self._gazd_szam_lab.setText(str(len(gazdalkodok)))
        self._teljesit_lab.setText(
            f'{ossz_teljesitett}/{ossz_szukseges}' if ossz_szukseges > 0 else '—'
        )
        tok = tokenek(self._tema)
        self._kozeledik_lab.setText(str(kozeledik_szam))
        self._kozeledik_lab.setStyleSheet(
            f'font-size: 20pt; font-weight: 600; background: transparent; '
            f'color: {tok["SARGA"] if kozeledik_szam > 0 else tok["TEXT0"]};'
        )
        self._szankcio_lab.setText(str(szankcio_szam))
        self._szankcio_lab.setStyleSheet(
            f'font-size: 20pt; font-weight: 600; background: transparent; '
            f'color: {tok["PIROS"] if szankcio_szam > 0 else tok["TEXT0"]};'
        )

        self._frissit_tabla()

    # ── Táblázat frissítése ───────────────────────────────────────────────────

    def _frissit_tabla(self) -> None:
        szoveg = self._kereses_szoveg.lower()

        szurt: list[dict] = []
        for adat in self._gazd_adatok:
            if self._szurt_gid is not None:
                if adat['gid'] != self._szurt_gid:
                    continue
            elif szoveg:
                if not (
                    szoveg in adat['nev'].lower()
                    or adat['ta_str'].startswith(szoveg)
                ):
                    continue
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
            self._tabla.setRowHeight(sor, 44)

            nev_elem = QTableWidgetItem(adat['nev'])
            nev_elem.setData(Qt.ItemDataRole.UserRole, adat['gid'])
            self._tabla.setItem(sor, 0, nev_elem)

            ta_elem = QTableWidgetItem()
            ta_elem.setData(Qt.ItemDataRole.DisplayRole, adat['tamogatasi_azonosito'])
            ta_elem.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._tabla.setItem(sor, 1, ta_elem)

            hal_szoveg = (
                f'{adat["ossz_keszult"]}/{adat["ossz_osszesen"]}'
                if adat['ossz_osszesen'] > 0 else '—'
            )
            hal_elem = QTableWidgetItem(hal_szoveg)
            hal_elem.setData(Qt.ItemDataRole.UserRole, adat['ossz_keszult'])
            hal_elem.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._tabla.setItem(sor, 2, hal_elem)

            jelveny = Jelveny(adat['legrosszabb_allapot'])
            self._tabla.setCellWidget(sor, 3, self._jelveny_kozepre(jelveny))

        self._tabla.setSortingEnabled(True)

    def _jelveny_kozepre(self, jelveny: Jelveny) -> QWidget:
        tartaly = QWidget()
        tartaly.setStyleSheet('background: transparent;')
        el = QHBoxLayout(tartaly)
        el.setContentsMargins(8, 0, 8, 0)
        el.addStretch()
        el.addWidget(jelveny)
        el.addStretch()
        return tartaly

    # ── Keresés és autocomplete ───────────────────────────────────────────────

    def _kereses_valtozas(self, szoveg: str) -> None:
        self._szurt_gid = None
        self._kereses_szoveg = szoveg.strip()
        gazdak = keres(self._db, szoveg)
        self._tipp_terkep = {g.nev: g.gid for g in gazdak}
        self._kompleter_modell.setStringList(list(self._tipp_terkep))
        self._frissit_tabla()

    def _kompleter_kivalasztva(self, kivalasztott: str) -> None:
        gid = self._tipp_terkep.get(kivalasztott)
        self._szurt_gid = gid
        self._kereses_mezo.blockSignals(True)
        self._kereses_mezo.setText(kivalasztott)
        self._kereses_mezo.blockSignals(False)
        self._frissit_tabla()

    # ── Szűrő ─────────────────────────────────────────────────────────────────

    def _szuro_valtozas(self, gomb_id: int) -> None:
        g = self._szuro_csoport.button(gomb_id)
        if g:
            self._szuro_allapot = g.property('szuro_allapot')
        self._frissit_tabla()

    # ── Kattintás a táblán ────────────────────────────────────────────────────

    def _sor_kattintva(self, index: QModelIndex) -> None:
        nev_elem = self._tabla.item(index.row(), 0)
        if nev_elem is None:
            return
        gid = nev_elem.data(Qt.ItemDataRole.UserRole)
        if gid is not None:
            self._gazd_megnyit(gid)

    # ── Navigáció ─────────────────────────────────────────────────────────────

    def _mutass_attekintest(self) -> None:
        self._stack.setCurrentIndex(0)
        self._oldal_cim.setText('Áttekintés')

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
        nev = self._gazd_widget._nev_cimke.text() if hasattr(self._gazd_widget, '_nev_cimke') else ''
        self._oldal_cim.setText(f'Gazdálkodók › {nev}' if nev else 'Gazdálkodók')

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
        self._oldal_cim.setText('Áttekintés')
        self._betolt()

    def _vissza_gazd_reszletekre(self) -> None:
        if self._ket_widget is not None:
            self._stack.removeWidget(self._ket_widget)
            self._ket_widget.deleteLater()
            self._ket_widget = None
        if self._gazd_widget is not None:
            self._stack.setCurrentWidget(self._gazd_widget)
            self._gazd_widget.refresh()

    # ── Import / Export ───────────────────────────────────────────────────────

    def _import_megnyit(self) -> None:
        from felulet.excel_parbeszedablak import ExcelParbeszedablak
        parbeszed = ExcelParbeszedablak(self._db, parent=self)
        if parbeszed.exec() == QDialog.DialogCode.Accepted:
            self._betolt()

    def _export_megnyit(self) -> None:
        from pathlib import Path
        from logika.excel_logika import exportal
        mappa = QFileDialog.getExistingDirectory(
            self, 'Exportálási mappa kiválasztása', str(Path.home())
        )
        if not mappa:
            return
        try:
            exportal(mappa, self._db)
        except Exception as e:
            hiba = QMessageBox(self)
            hiba.setWindowTitle('Export hiba')
            hiba.setText(f'Az export során hiba lépett fel:\n{e}')
            hiba.exec()
            return
        siker = QMessageBox(self)
        siker.setWindowTitle('Export kész')
        siker.setText(f'Az összes fájl sikeresen exportálva:\n{mappa}')
        siker.exec()

    # ── Téma ─────────────────────────────────────────────────────────────────

    def _tema_valtas(self) -> None:
        self._tema = 'sotet' if self._tema == 'vilagos' else 'vilagos'
        self._konfig.set('megjelenes', 'tema', self._tema)
        beallitasok_ment(self._konfig)
        QApplication.instance().setStyleSheet(betoltes(self._tema))
        self._oldalsav.tema_frissit()
        self._betolt()

    # ── Beállítások ───────────────────────────────────────────────────────────

    def _beallitasok_megnyit(self) -> None:
        ablak = BeallitasokAblak(konfig=self._konfig, parent=self)
        if ablak.exec() == QDialog.DialogCode.Accepted:
            self._konfig = beallitasok_betolt()
            self._tema = self._konfig.get('megjelenes', 'tema', fallback='vilagos')
            QApplication.instance().setStyleSheet(betoltes(self._tema))
            self._oldalsav.tema_frissit()
            self._betolt()
