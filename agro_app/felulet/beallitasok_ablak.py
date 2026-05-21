import configparser

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from logika.beallitasok import beallitasok_ment, uj_konfig


class BeallitasokAblak(QDialog):
    def __init__(
        self,
        konfig: configparser.ConfigParser | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle('Adatbázis beállítások — Agrotechnika Figyelő')
        self.setMinimumWidth(380)

        db = konfig['adatbazis'] if konfig else {}
        meg = konfig['megjelenes'] if konfig else {}

        self._host = QLineEdit(db.get('host', 'localhost'))
        self._port = QLineEdit(db.get('port', '3306'))
        self._felhasznalo = QLineEdit(db.get('felhasznalo', 'root'))
        self._jelszo = QLineEdit(db.get('jelszo', ''))
        self._jelszo.setEchoMode(QLineEdit.EchoMode.Password)
        self._adatbazis_nev = QLineEdit(db.get('adatbazis_nev', 'agrotechdb'))

        self._tema = QComboBox()
        self._tema.addItems(['vilagos', 'sotet'])
        self._tema.setCurrentText(meg.get('tema', 'vilagos'))

        urlap = QFormLayout()
        urlap.addRow(QLabel('Szerver:'), self._host)
        urlap.addRow(QLabel('Port:'), self._port)
        urlap.addRow(QLabel('Felhasználó:'), self._felhasznalo)
        urlap.addRow(QLabel('Jelszó:'), self._jelszo)
        urlap.addRow(QLabel('Adatbázis neve:'), self._adatbazis_nev)
        urlap.addRow(QLabel('Téma:'), self._tema)

        gombok = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        gombok.button(QDialogButtonBox.StandardButton.Ok).setText('Mentés')
        gombok.button(QDialogButtonBox.StandardButton.Cancel).setText('Mégse')
        gombok.accepted.connect(self._mentes)
        gombok.rejected.connect(self.reject)

        elrendezes = QVBoxLayout()
        elrendezes.addLayout(urlap)
        elrendezes.addWidget(gombok)
        self.setLayout(elrendezes)

    def _mentes(self) -> None:
        konfig = uj_konfig(
            host=self._host.text().strip(),
            port=self._port.text().strip(),
            felhasznalo=self._felhasznalo.text().strip(),
            jelszo=self._jelszo.text(),
            adatbazis_nev=self._adatbazis_nev.text().strip(),
            tema=self._tema.currentText(),
        )
        beallitasok_ment(konfig)
        self.accept()
