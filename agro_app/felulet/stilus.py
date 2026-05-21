"""QSS stiluslapok — token-alapú sötét és világos téma."""
from __future__ import annotations

# ─── Tokenek ─────────────────────────────────────────────────────────────────

def _tokenek(tema: str) -> dict[str, str]:
    if tema == 'sotet':
        return {
            'BG0':           '#0E0E10',
            'BG1':           '#18181B',
            'BG2':           '#1F1F23',
            'BG3':           '#27272A',
            'KERET':         '#2D2D31',
            'KERET_EROS':    '#3A3A3F',
            'TEXT0':         '#FAFAFA',
            'TEXT1':         '#A1A1AA',
            'TEXT2':         '#71717A',
            'AKCENT':        '#4A7C59',
            'AK_HOVER':      '#5E9170',
            'AK_TINT':       'rgba(74,124,89,0.10)',
            'SARGA':         '#B8860B',
            'PIROS':         '#C0392B',
            'SZANKCIO_BG':   '#6B1A1A',
            'SZANKCIO_FG':   '#FFFFFF',
        }
    return {
        'BG0':           '#FFFFFF',
        'BG1':           '#FAFAFA',
        'BG2':           '#F4F4F5',
        'BG3':           '#E4E4E7',
        'KERET':         '#E4E4E7',
        'KERET_EROS':    '#D4D4D8',
        'TEXT0':         '#18181B',
        'TEXT1':         '#52525B',
        'TEXT2':         '#71717A',
        'AKCENT':        '#3D6649',
        'AK_HOVER':      '#2F5039',
        'AK_TINT':       'rgba(61,102,73,0.08)',
        'SARGA':         '#B8860B',
        'PIROS':         '#C0392B',
        'SZANKCIO_BG':   '#6B1A1A',
        'SZANKCIO_FG':   '#FFFFFF',
    }


# ─── QSS sablon ──────────────────────────────────────────────────────────────

_SABLON = """
/* ── Alap ── */
QMainWindow, QDialog {
    background-color: @BG0@;
}
QWidget {
    background-color: @BG0@;
    color: @TEXT0@;
    font-family: "Inter", "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 10pt;
}

/* ── Feliratok ── */
QLabel {
    background: transparent;
    color: @TEXT0@;
}
QLabel#oldal_cim {
    font-size: 14pt;
    font-weight: 600;
    color: @TEXT0@;
}
QLabel#alkalmazas_nev {
    font-size: 10pt;
    font-weight: 600;
    color: @AKCENT@;
}
QLabel#szoveg1 {
    color: @TEXT1@;
}
QLabel#szoveg2 {
    color: @TEXT2@;
    font-size: 8pt;
    font-weight: 500;
}
QLabel#szekció_cim {
    font-size: 12pt;
    font-weight: 600;
    color: @TEXT0@;
}
QLabel#info_cimke {
    font-size: 8pt;
    font-weight: 500;
    color: @TEXT2@;
    letter-spacing: 0.5px;
}
QLabel#info_ertek {
    font-size: 11pt;
    font-weight: 500;
    color: @TEXT0@;
}

/* ── Gombok — alap (ghost) ── */
QPushButton {
    background-color: transparent;
    color: @TEXT0@;
    border: 1px solid @KERET@;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 10pt;
    font-weight: 500;
    min-height: 36px;
    max-height: 36px;
}
QPushButton:hover {
    background-color: @BG2@;
    color: @TEXT0@;
}
QPushButton:pressed {
    background-color: @BG3@;
}
QPushButton:disabled {
    color: @TEXT2@;
    border-color: @KERET@;
}

/* ── Elsődleges gomb ── */
QPushButton#elso_gomb {
    background-color: @AKCENT@;
    color: #FFFFFF;
    border: none;
}
QPushButton#elso_gomb:hover {
    background-color: @AK_HOVER@;
    color: #FFFFFF;
}
QPushButton#elso_gomb:pressed {
    background-color: @AK_HOVER@;
}

/* ── Teljesít cella gomb ── */
QPushButton#teljesit_gomb {
    background-color: @AKCENT@;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 10pt;
    font-weight: 500;
    min-height: 32px;
    max-height: 32px;
}
QPushButton#teljesit_gomb:hover {
    background-color: @AK_HOVER@;
}

/* ── Szűrő chip gombok ── */
QPushButton#szuro {
    border-radius: 20px;
    padding: 4px 16px;
    font-size: 9pt;
    min-height: 28px;
    max-height: 28px;
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

/* ── Oldalsáv ── */
QFrame#oldalsav {
    background-color: @BG1@;
    border: none;
    border-right: 1px solid @KERET@;
}
QFrame#oldalsav_elvalaszto {
    background-color: @KERET@;
    min-height: 1px;
    max-height: 1px;
    border: none;
}

/* ── Navigációs elem ── */
QPushButton#nav_elem {
    background-color: transparent;
    color: @TEXT1@;
    border: none;
    border-radius: 6px;
    padding: 0px 12px;
    text-align: left;
    font-size: 10pt;
    font-weight: 400;
    min-height: 40px;
    max-height: 40px;
}
QPushButton#nav_elem:hover {
    background-color: @BG2@;
    color: @TEXT0@;
}
QPushButton#nav_elem:checked {
    background-color: @AK_TINT@;
    color: @AKCENT@;
    border-left: 2px solid @AKCENT@;
    font-weight: 500;
}

/* ── Felső sáv ── */
QFrame#felso_sav {
    background-color: @BG0@;
    border: none;
    border-bottom: 1px solid @KERET@;
    min-height: 48px;
    max-height: 48px;
}

/* ── Szövegbevitel ── */
QLineEdit {
    background-color: @BG1@;
    color: @TEXT0@;
    border: 1px solid @KERET@;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 10pt;
    selection-background-color: @AKCENT@;
    selection-color: #FFFFFF;
    min-height: 36px;
    max-height: 36px;
}
QLineEdit:focus {
    border-color: @AKCENT@;
}
QLineEdit:disabled {
    background-color: @BG2@;
    color: @TEXT2@;
}

/* ── Táblázat ── */
QTableWidget {
    background-color: @BG0@;
    color: @TEXT0@;
    border: none;
    gridline-color: @KERET@;
    font-size: 10pt;
    outline: none;
    alternate-background-color: @BG0@;
    show-decoration-selected: 0;
}
QTableWidget::item {
    padding: 6px 12px;
    border: none;
    border-bottom: 1px solid @KERET@;
}
QTableWidget::item:selected {
    background-color: @AK_TINT@;
    color: @TEXT0@;
}
QTableWidget::item:focus {
    outline: none;
}
QTableWidget::item:hover {
    background-color: @BG2@;
}
QHeaderView {
    background-color: @BG0@;
}
QHeaderView::section {
    background-color: @BG0@;
    color: @TEXT1@;
    border: none;
    border-bottom: 1px solid @KERET_EROS@;
    padding: 8px 12px;
    font-size: 10pt;
    font-weight: 500;
}
QHeaderView::section:hover {
    background-color: @BG2@;
}

/* ── Görgetősávok ── */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: @KERET@;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background-color: @TEXT2@;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: @KERET@;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background-color: @TEXT2@;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Popup / autocomplete lista ── */
QAbstractItemView {
    background-color: @BG1@;
    color: @TEXT0@;
    border: 1px solid @KERET@;
    selection-background-color: @AK_TINT@;
    selection-color: @TEXT0@;
    outline: none;
}

/* ── Legördülő lista ── */
QComboBox {
    background-color: @BG1@;
    color: @TEXT0@;
    border: 1px solid @KERET@;
    border-radius: 6px;
    padding: 4px 10px;
    min-height: 36px;
    font-size: 10pt;
}
QComboBox:focus {
    border-color: @AKCENT@;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: @BG1@;
    color: @TEXT0@;
    border: 1px solid @KERET@;
    selection-background-color: @AK_TINT@;
    selection-color: @TEXT0@;
    outline: none;
}

/* ── Párbeszédablak ── */
QDialog {
    background-color: @BG1@;
}
QDialogButtonBox QPushButton { min-width: 80px; }

/* ── Üzenetablak ── */
QMessageBox { background-color: @BG1@; }
QMessageBox QPushButton { min-width: 80px; }

/* ── Stat kártya ── */
QFrame#stat_kartya {
    background-color: @BG1@;
    border: 1px solid @KERET@;
    border-radius: 6px;
    min-height: 100px;
    max-height: 100px;
}

/* ── Folyamatjelző ── */
QProgressBar {
    background-color: @BG3@;
    border: none;
    border-radius: 3px;
    min-height: 4px;
    max-height: 4px;
}
QProgressBar::chunk {
    background-color: @AKCENT@;
    border-radius: 3px;
}
"""


# ─── Nyilvános API ────────────────────────────────────────────────────────────

def betoltes(tema: str) -> str:
    """Visszaadja a megadott téma QSS stiluslapját ('vilagos' vagy 'sotet')."""
    qss = _SABLON
    for kulcs, ertek in _tokenek(tema).items():
        qss = qss.replace(f'@{kulcs}@', ertek)
    return qss


def tokenek(tema: str) -> dict[str, str]:
    """Visszaadja a token szótárat közvetlen Python használathoz."""
    return _tokenek(tema)
