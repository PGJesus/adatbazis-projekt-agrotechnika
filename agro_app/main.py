import sys

from PyQt6.QtWidgets import QApplication

from adatbazis.kapcsolat import kapcsolat_inicializal
from logika.beallitasok import beallitasok_betolt
from felulet.fo_ablak import FoAblak


def main() -> None:
    alkalmazas = QApplication(sys.argv)
    # TODO: beállítások betöltése, első indulás kezelése, főablak megnyitása
    sys.exit(alkalmazas.exec())


if __name__ == "__main__":
    main()
