"""Jelveny widget — Allapot enum értékét vizuálisan jeleníti meg."""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QFont
from PyQt6.QtWidgets import QWidget

from logika.ket_logika import Allapot


_ALLAPOT_SZIN: dict[Allapot, str] = {
    Allapot.KESZ:     '#4A7C59',
    Allapot.ZOLD:     '#4A7C59',
    Allapot.SARGA:    '#B8860B',
    Allapot.PIROS:    '#C0392B',
    Allapot.SZANKCIO: '#6B1A1A',
}

_ALLAPOT_FELIRAT: dict[Allapot, str] = {
    Allapot.KESZ:     'Kész',
    Allapot.ZOLD:     'Rendben',
    Allapot.SARGA:    'Közeledik',
    Allapot.PIROS:    'Sürgős',
    Allapot.SZANKCIO: '⚠ SZANKCIÓ',
}

_SZOVEG_SZIN: dict[Allapot, str] = {
    Allapot.KESZ:     '#52525B',
    Allapot.ZOLD:     '#52525B',
    Allapot.SARGA:    '#52525B',
    Allapot.PIROS:    '#52525B',
    Allapot.SZANKCIO: '#FFFFFF',
}

_KOR_ATMERÖ = 16
_RES = 8


class Jelveny(QWidget):
    def __init__(self, allapot: Allapot, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._allapot = allapot
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedHeight(24)

    @property
    def allapot(self) -> Allapot:
        return self._allapot

    @allapot.setter
    def allapot(self, uj: Allapot) -> None:
        if uj != self._allapot:
            self._allapot = uj
            self.update()

    def sizeHint(self) -> QSize:
        fm = self.fontMetrics()
        szoveg_sz = fm.horizontalAdvance('⚠ SZANKCIÓ')
        if self._allapot == Allapot.SZANKCIO:
            # pill: padding 10px each side + text
            return QSize(szoveg_sz + 20, 24)
        return QSize(_KOR_ATMERÖ + _RES + szoveg_sz, 24)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        szin = _ALLAPOT_SZIN.get(self._allapot, '#888888')
        felirat = _ALLAPOT_FELIRAT.get(self._allapot, '')
        szoveg_szin = _SZOVEG_SZIN.get(self._allapot, '#FFFFFF')

        if self._allapot == Allapot.SZANKCIO:
            self._rajzol_pill(p, szin, szoveg_szin, felirat)
        else:
            self._rajzol_kor_cimke(p, szin, szoveg_szin, felirat)

        p.end()

    def _rajzol_pill(self, p: QPainter, bg: str, fg: str, felirat: str) -> None:
        r = self.rect()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(bg))
        p.drawRoundedRect(r, 20, 20)

        betutipus = QFont()
        betutipus.setPointSize(8)
        betutipus.setWeight(QFont.Weight.DemiBold)
        p.setFont(betutipus)
        p.setPen(QColor(fg))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, felirat)

    def _rajzol_kor_cimke(self, p: QPainter, kor_szin: str, szoveg_szin: str, felirat: str) -> None:
        cy = self.height() // 2
        r = _KOR_ATMERÖ // 2

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(kor_szin))
        p.drawEllipse(0, cy - r, _KOR_ATMERÖ, _KOR_ATMERÖ)

        if self._allapot == Allapot.KESZ:
            self._rajzol_pipa(p, r, cy)

        betutipus = QFont()
        betutipus.setPointSize(8)
        betutipus.setWeight(QFont.Weight.Normal)
        p.setFont(betutipus)
        p.setPen(QColor(szoveg_szin))

        szoveg_x = _KOR_ATMERÖ + _RES
        szoveg_ter = self.rect().adjusted(szoveg_x, 0, 0, 0)
        p.drawText(szoveg_ter, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, felirat)

    def _rajzol_pipa(self, p: QPainter, r: int, cy: int) -> None:
        toll = QPen(QColor('#FFFFFF'))
        toll.setWidth(2)
        toll.setCapStyle(Qt.PenCapStyle.RoundCap)
        toll.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(toll)
        p.setBrush(Qt.BrushStyle.NoBrush)

        cx = r
        p.drawLine(cx - 4, cy, cx - 1, cy + 3)
        p.drawLine(cx - 1, cy + 3, cx + 4, cy - 3)
