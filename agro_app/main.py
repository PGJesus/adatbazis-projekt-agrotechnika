import sys

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from logika.beallitasok import beallitasok_betolt, _ALKALMAZAS_NEV
from felulet.beallitasok_ablak import BeallitasokAblak
from adatbazis.kapcsolat import kapcsolat_inicializal


def main() -> None:
    alkalmazas = QApplication(sys.argv)
    alkalmazas.setApplicationName(_ALKALMAZAS_NEV)
    alkalmazas.setOrganizationName('')

    konfig = beallitasok_betolt()

    if konfig is None:
        ablak = BeallitasokAblak()
        if ablak.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        konfig = beallitasok_betolt()

    try:
        kapcsolat_inicializal(konfig)
        print('Kapcsolódás sikeres')
    except Exception as kiv:
        QMessageBox.critical(
            None,
            'Kapcsolódási hiba',
            f'Nem sikerült csatlakozni az adatbázishoz:\n\n{kiv}',
        )
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
