"""QSS stiluslapok — világos és sötét téma."""
from __future__ import annotations

# ─── Paletta ─────────────────────────────────────────────────────────────────

def _paletta(tema: str) -> dict[str, str]:
    if tema == 'sotet':
        return {
            'BG':          '#1E1E1E',
            'FELSZIN':     '#2A2825',
            'SZOVEG':      '#F0EBE0',
            'SZOVEG2':     '#A8A39A',
            'AKCENT':      '#6BA77B',
            'AK_HOVER':    '#7DB88B',
            'SARGA':       '#E8B83C',
            'PIROS':       '#E74C3C',
            'SZANKCIO':    '#A03030',
            'KERET':       '#3A3835',
        }
    return {
        'BG':          '#FFFFFF',
        'FELSZIN':     '#FAF7F0',
        'SZOVEG':      '#1A1A1A',
        'SZOVEG2':     '#555555',
        'AKCENT':      '#4A7C59',
        'AK_HOVER':    '#3D6649',
        'SARGA':       '#D4A017',
        'PIROS':       '#C0392B',
        'SZANKCIO':    '#6B1A1A',
        'KERET':       '#E0DCD0',
    }


# ─── QSS sablon (egyedi @KULCS@ helyőrzőkkel) ────────────────────────────────

_SABLON = """
/* ── Alap ── */
QMainWindow, QDialog {
    background-color: @BG@;
}
QWidget {
    background-color: @BG@;
    color: @SZOVEG@;
    font-size: 10pt;
}

/* ── Eszköztár ── */
QToolBar {
    background-color: @FELSZIN@;
    border: none;
    border-bottom: 1px solid @KERET@;
    padding: 4px 12px;
    spacing: 6px;
}
QToolBar QLabel {
    background: transparent;
}

/* ── Feliratok ── */
QLabel {
    background: transparent;
    color: @SZOVEG@;
}
QLabel#fo_cim {
    font-size: 15pt;
    font-weight: bold;
    color: @AKCENT@;
    padding: 0 6px;
}
QLabel#szoveg2 {
    color: @SZOVEG2@;
}

/* ── Gombok (általános) ── */
QPushButton {
    background-color: @FELSZIN@;
    color: @SZOVEG@;
    border: 1px solid @KERET@;
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 26px;
}
QPushButton:hover {
    background-color: @BG@;
    border-color: @AKCENT@;
    color: @AKCENT@;
}
QPushButton:pressed {
    background-color: @AKCENT@;
    color: #FFFFFF;
    border-color: @AKCENT@;
}
QPushButton:disabled {
    color: @SZOVEG2@;
    border-color: @KERET@;
}

/* ── Szűrő chip gombok ── */
QPushButton#szuro {
    border-radius: 13px;
    padding: 4px 16px;
    min-height: 26px;
    font-size: 9pt;
}
QPushButton#szuro:checked {
    background-color: @AKCENT@;
    border-color: @AKCENT@;
    color: #FFFFFF;
}
QPushButton#szuro:checked:hover {
    background-color: @AK_HOVER@;
    border-color: @AK_HOVER@;
    color: #FFFFFF;
}

/* ── Szövegbevitel ── */
QLineEdit {
    background-color: @BG@;
    color: @SZOVEG@;
    border: 1px solid @KERET@;
    border-radius: 6px;
    padding: 5px 10px;
    selection-background-color: @AKCENT@;
    selection-color: #FFFFFF;
    min-height: 26px;
}
QLineEdit:focus {
    border-color: @AKCENT@;
}
QLineEdit:disabled {
    background-color: @FELSZIN@;
    color: @SZOVEG2@;
}

/* ── Legördülő lista ── */
QComboBox {
    background-color: @FELSZIN@;
    color: @SZOVEG@;
    border: 1px solid @KERET@;
    border-radius: 6px;
    padding: 4px 10px;
    min-height: 26px;
}
QComboBox:focus {
    border-color: @AKCENT@;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}
QComboBox QAbstractItemView {
    background-color: @FELSZIN@;
    color: @SZOVEG@;
    border: 1px solid @KERET@;
    selection-background-color: @AKCENT@;
    selection-color: #FFFFFF;
    outline: none;
}

/* ── Táblázat ── */
QTableWidget {
    background-color: @BG@;
    color: @SZOVEG@;
    border: none;
    gridline-color: @KERET@;
    alternate-background-color: @FELSZIN@;
    font-size: 10pt;
    outline: none;
}
QTableWidget::item {
    padding: 6px 10px;
    border: none;
}
QTableWidget::item:selected {
    background-color: @AKCENT@;
    color: #FFFFFF;
}
QTableWidget::item:focus {
    outline: none;
}
QHeaderView {
    background-color: @FELSZIN@;
}
QHeaderView::section {
    background-color: @FELSZIN@;
    color: @SZOVEG@;
    border: none;
    border-bottom: 2px solid @AKCENT@;
    border-right: 1px solid @KERET@;
    padding: 7px 10px;
    font-weight: bold;
}
QHeaderView::section:last {
    border-right: none;
}
QHeaderView::section:hover {
    background-color: @BG@;
    color: @AKCENT@;
}

/* ── Görgetősávok ── */
QScrollBar:vertical {
    background-color: @FELSZIN@;
    width: 8px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: @KERET@;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background-color: @SZOVEG2@;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background-color: @FELSZIN@;
    height: 8px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: @KERET@;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background-color: @SZOVEG2@;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Popup / autocomplete lista ── */
QAbstractItemView {
    background-color: @FELSZIN@;
    color: @SZOVEG@;
    border: 1px solid @KERET@;
    selection-background-color: @AKCENT@;
    selection-color: #FFFFFF;
    outline: none;
}

/* ── Párbeszédablak ── */
QDialog {
    background-color: @FELSZIN@;
}
QDialogButtonBox QPushButton {
    min-width: 80px;
}

/* ── Üzenetablak ── */
QMessageBox {
    background-color: @FELSZIN@;
}
QMessageBox QPushButton {
    min-width: 80px;
}
"""


# ─── Nyilvános API ───────────────────────────────────────────────────────────

def betoltes(tema: str) -> str:
    """Visszaadja a megadott téma QSS stiluslapját ('vilagos' vagy 'sotet')."""
    qss = _SABLON
    for kulcs, ertek in _paletta(tema).items():
        qss = qss.replace(f'@{kulcs}@', ertek)
    return qss
