# CLAUDE.md

Context for Claude Code working on this project. Read this first.

---

## Goal

Desktop application for **Hungarian agrotechnology administration**. Single admin user.
Tracks farmers, their land commitments (KETs), the fields inside each KET, and the
completion status of agrotechnology obligations on those fields. Data is bootstrapped
from a fixed set of Excel files and maintained through the GUI afterward — for v1,
the GUI handles completion marking only; all other data comes from Excel.

App name: **Agrotechnika Figyelő**.

---

## Tech stack

- **Language:** Python
- **GUI:** PyQt6
- **ORM / DB driver:** SQLAlchemy + `mysql-connector-python`
- **Excel I/O:** pandas + `python-calamine` (fast read) + `openpyxl` (write/format)
- **Database:** MySQL
- **Config storage:** `configparser` (stdlib) over a `.ini` file in the user-config dir
- **Packaging:** PyInstaller (produces a single `.exe`)

No web layer, no cross-platform requirement.

---

## Language convention (important)

- **Conversation / planning / commit messages / this doc:** English.
- **Everything in the code:** Hungarian. Table names, column names, ORM class names,
  attribute names, filenames, folder names, UI strings, error messages, comments.
  Don't mix English identifiers into Hungarian code.
- **Python keywords / standard library / third-party APIs:** English (unavoidable).
- **`main.py` stays as `main.py`** — Python convention for the entry point.

---

## Domain glossary

| Hungarian             | English meaning                                          |
| --------------------- | -------------------------------------------------------- |
| gazdálkodó            | farmer (the master entity)                               |
| támogatási azonosító  | farmer's external support ID (8-digit)                   |
| KET                   | land commitment grouping ≥1 fields under obligations     |
| KET azonosító         | KET's external ID (6-digit)                              |
| tábla                 | individual field parcel inside a KET                     |
| táblasorszám          | admin-assigned sequence number for a field (2–20)        |
| tábla azonosító       | composite field ID, format `00000000-00` (from Excel)    |
| vállalás              | obligation / task the farmer committed to                |
| előírás azonosító     | the task's prescription number                           |
| teljesítés            | a single (task, field) completion record                 |
| szankció              | post-deadline sanction state for unfinished obligations  |
| terület [ha]          | area in hectares (4 decimal precision)                   |

---

## Project layout

```
agro_app/
├── main.py
├── adatbazis/
│   ├── __init__.py
│   ├── modellek.py             # SQLAlchemy models mirroring the 5 DB tables
│   └── kapcsolat.py            # engine, session, config loading
├── logika/
│   ├── __init__.py
│   ├── gazdalkodo_logika.py    # farmer read ops, search/autocomplete
│   ├── ket_logika.py           # KET progress (X/Y), deadline state, szankció check
│   ├── tabla_logika.py         # field reads, mark/unmark completion
│   ├── excel_logika.py         # import + export
│   └── beallitasok.py          # config file load/save (DB creds, theme)
├── felulet/
│   ├── __init__.py
│   ├── fo_ablak.py             # main window — dashboard, search, filters
│   ├── gazdalkodo_reszletek.py # farmer detail with KETs and X/Y progress
│   ├── ket_reszletek.py        # per-field table, mark/unmark buttons
│   ├── excel_parbeszedablak.py # file picker, preview, import/export dialog
│   ├── beallitasok_ablak.py    # first-run config dialog (DB creds)
│   └── stilus.py               # light + dark QSS theme definitions
└── requirements.txt
```

---

## Data model

Five tables, schema name `agrotechdb`, all identifiers Hungarian.

```
gazdalkodo ──┬── ket ── tablak
             │
             └── vallalasok ── teljesitesek ── (also FK to tablak)
```

**Key relationships:**
- A `gazdalkodo` owns many `ket`s and many `vallalasok`.
- A `ket` contains many `tablak` (1–3 per KET in our test data).
- `vallalasok` are assigned **at farmer level**, not KET level. If a farmer has
  3 KETs with 2 fields each, every task must be completed 6 times.
- `teljesitesek` is the (task, field, date) join: one row = "task X done on field Y
  on date Z." Unique constraint on (vallalasok_vid, tablak_tid) → a task can be
  completed only once per field.

**Derived, never stored:**
- Field completion status (= does a `teljesitesek` row exist for this task+field?)
- KET completion progress, shown as **X/Y** (= count of completed field-task pairs
  vs total required for that KET).
- KET "fully complete" = every (task, field) pair under it has a `teljesitesek` row.
- Farmer-level completion summary (aggregate of all the farmer's KETs).
- Deadline state (zöld / sárga / piros / szankció) — see Deadline section.

### Schema SQL

```sql
CREATE SCHEMA IF NOT EXISTS `agrotechdb` DEFAULT CHARACTER SET utf8;
USE `agrotechdb`;

CREATE TABLE IF NOT EXISTS `agrotechdb`.`gazdalkodo` (
  `gid`                   INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Gazdálkodó azonosító',
  `nev`                   VARCHAR(150) NOT NULL                COMMENT 'Gazdálkodó neve',
  `cim`                   VARCHAR(255) NOT NULL                COMMENT 'Lakcím',
  `telefonszam`           VARCHAR(20)  NOT NULL                COMMENT 'Telefonszám',
  `email`                 VARCHAR(100) NULL                    COMMENT 'E-mail cím',
  `tamogatasi_azonosito`  INT          NOT NULL                COMMENT 'Támogatási azonosító',
  PRIMARY KEY (`gid`)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS `agrotechdb`.`ket` (
  `kid`             INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'KET azonosító',
  `ket_azonosito`   INT          NOT NULL                COMMENT 'KET külső azonosítója',
  `terulet_ha`      DOUBLE       NOT NULL                COMMENT 'KET teljes területe (ha)',
  `gazdalkodo_gid`  INT UNSIGNED NOT NULL                COMMENT 'Gazdálkodó hivatkozás',
  PRIMARY KEY (`kid`),
  UNIQUE INDEX `ket_azonosito_UNIQUE` (`ket_azonosito` ASC),
  INDEX `fk_ket_gazdalkodo_idx` (`gazdalkodo_gid` ASC),
  CONSTRAINT `fk_ket_gazdalkodo`
    FOREIGN KEY (`gazdalkodo_gid`) REFERENCES `agrotechdb`.`gazdalkodo` (`gid`)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS `agrotechdb`.`tablak` (
  `tid`             INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Tábla azonosító',
  `tablasorszam`    INT          NOT NULL                COMMENT 'Admin által adott sorszám',
  `tablaazonosito`  VARCHAR(50)  NOT NULL                COMMENT 'Összetett azonosító (Excel importból)',
  `terulet_ha`      DOUBLE       NULL                    COMMENT 'Tábla területe (ha)',
  `ket_kid`         INT UNSIGNED NOT NULL                COMMENT 'KET hivatkozás',
  PRIMARY KEY (`tid`),
  INDEX `fk_tablak_ket_idx` (`ket_kid` ASC),
  CONSTRAINT `fk_tablak_ket`
    FOREIGN KEY (`ket_kid`) REFERENCES `agrotechdb`.`ket` (`kid`)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS `agrotechdb`.`vallalasok` (
  `vid`               INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Vállalás azonosító',
  `eloiras_azonosito` INT          NOT NULL                COMMENT 'Előírás sorszáma',
  `leiras`            TEXT         NULL                    COMMENT 'Vállalás leírása',
  `gazdalkodo_gid`    INT UNSIGNED NOT NULL                COMMENT 'Gazdálkodó hivatkozás',
  PRIMARY KEY (`vid`),
  INDEX `fk_vallalasok_gazdalkodo_idx` (`gazdalkodo_gid` ASC),
  CONSTRAINT `fk_vallalasok_gazdalkodo`
    FOREIGN KEY (`gazdalkodo_gid`) REFERENCES `agrotechdb`.`gazdalkodo` (`gid`)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS `agrotechdb`.`teljesitesek` (
  `telid`             INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Teljesítés azonosító',
  `vallalasok_vid`    INT UNSIGNED NOT NULL                COMMENT 'Vállalás hivatkozás',
  `tablak_tid`        INT UNSIGNED NOT NULL                COMMENT 'Tábla hivatkozás',
  `teljesules_datuma` DATE         NOT NULL                COMMENT 'Teljesítés dátuma',
  PRIMARY KEY (`telid`),
  UNIQUE INDEX `uq_vallalasok_tabla` (`vallalasok_vid` ASC, `tablak_tid` ASC)
    COMMENT 'Egy vállalás egy táblán csak egyszer teljesíthető',
  INDEX `fk_teljesitesek_vallalasok_idx` (`vallalasok_vid` ASC),
  INDEX `fk_teljesitesek_tablak_idx` (`tablak_tid` ASC),
  CONSTRAINT `fk_teljesitesek_vallalasok`
    FOREIGN KEY (`vallalasok_vid`) REFERENCES `agrotechdb`.`vallalasok` (`vid`),
  CONSTRAINT `fk_teljesitesek_tablak`
    FOREIGN KEY (`tablak_tid`) REFERENCES `agrotechdb`.`tablak` (`tid`)
) ENGINE = InnoDB;
```

### Task type seeding

The four `vallalasok` types are hardcoded constants. On import, each farmer with
`igen` in a given Agrotechnika_vállalások column gets one `vallalasok` row inserted:

| `eloiras_azonosito` | `leiras`                       |
| ------------------- | ------------------------------ |
| 1                   | istállótrágya kijuttatás 1     |
| 2                   | istállótrágya kijuttatás 2     |
| 3                   | melléktermék beforgatás        |
| 4                   | középmély lazítás              |

These four are fixed for v1. No lookup table.

---

## Excel files (import + export format)

Eight files, all custom but consistent. A test set of 100 farmers has been generated.
Export must produce the same format.

**`Gazd_alapadatok.xlsx`** — farmer master data
| Column                  | Type            |
| ----------------------- | --------------- |
| név                     | string          |
| Lakcím                  | string          |
| telefonszám             | string          |
| email                   | string          |
| támogatási azonosító    | int, 8 digits   |

**`Agrotechnika_vállalások.xlsx`** — what each farmer committed to
| Column                       | Type                            |
| ---------------------------- | ------------------------------- |
| név                          | string (must match Gazd_alap)   |
| támogatási azonosító         | int (must match Gazd_alap)      |
| istállótrágya kijuttatás 1   | `igen` / `nem`                  |
| istállótrágya kijuttatás 2   | `igen` / `nem`                  |
| melléktermék beforgatás      | `igen` / `nem`                  |
| középmély lazítás            | `igen` / `nem`                  |

**`KETEK.xlsx`** — KET commitments
| Column                | Type                                |
| --------------------- | ----------------------------------- |
| név                   | string                              |
| támogatási azonosító  | int                                 |
| KET azonosító         | int, 6 digits                       |
| KET terület [ha]      | double, 4 decimals, range 0.25–50   |

**`Táblák_YYYY.xlsx`** — one file per year (2025–2029), same structure
| Column                            | Type                                       |
| --------------------------------- | ------------------------------------------ |
| név                               | string                                     |
| támogatási azonosító              | int                                        |
| táblasorszám                      | int, 2–20                                  |
| tábla azonosító                   | string, `00000000-00`                      |
| tábla terület [ha]                | double, 4 decimals                         |
| vetett kultúra                    | string — **dropped on import**             |
| vetési idő                        | date — **dropped on import**               |
| KET azonosító                     | int, FK-style link to KETEK.xlsx           |
| istállótrágya kijuttatás dátum    | date or empty                              |
| melléktermék beforgatás dátum     | date or empty                              |
| középmély lazítás dátum           | date or empty                              |

`vetett kultúra` and `vetési idő` exist in the source files but have no role in the
app — read past them, don't store them.

---

## Import logic

The five yearly Táblák files are processed together as a 5-year window — not
independently. The fertilization task is split into two `vallalasok` records but the
Excel has only one `istállótrágya kijuttatás dátum` column. Map by counting:

| Task                          | Source column                       | Fulfilled when                  | Date stored        |
| ----------------------------- | ----------------------------------- | ------------------------------- | ------------------ |
| istállótrágya kijuttatás 1    | `istállótrágya kijuttatás dátum`    | ≥ 1 event across 5 years        | earliest date      |
| istállótrágya kijuttatás 2    | same column, counted again          | ≥ 2 events across 5 years       | second-earliest    |
| melléktermék beforgatás       | `melléktermék beforgatás dátum`     | any non-empty date              | that date          |
| középmély lazítás             | `középmély lazítás dátum`           | any non-empty date              | that date          |

**Fertilization validation rule:** the same field cannot be fertilized twice in the
same calendar year. Two fertilizations on the **same** field must be in different
years; two fertilizations in the **same** year must be on different fields. Flag a
violation if the same field has two non-empty fertilization dates within a single
`Táblák_YYYY.xlsx`.

### Re-import behavior

When the admin starts a new import and the DB already contains data, prompt them
with three choices:
- **Felülírás** — wipe DB and rebuild from the new files.
- **Összefűzés** — merge (upsert farmers/KETs/fields by external IDs, add new
  completions).
- **Mégse** — cancel.

### Validation behavior on bad data

If an Excel row references something missing (farmer not in `Gazd_alapadatok`,
KET not in `KETEK`, etc.), **skip the row and accumulate a warning**. After the
import finishes, show a dialog listing every skipped row. Each warning must include:

- File name (e.g. `Táblák_2027.xlsx`)
- Sheet name
- Row number (1-indexed, matching Excel)
- Column that failed
- The offending value
- A plain-Hungarian explanation of what went wrong

Reuse the same structured error format anywhere else validation fails (e.g. the
fertilization same-year rule).

### Other notes

- `tábla azonosító` (format `00000000-00`) is the stable cross-year field key —
  store it as-is, don't derive it.
- A farmer's task can only be marked done on a field belonging to that same farmer
  (DB doesn't enforce this — app logic must).
- Use `python-calamine` via pandas for read performance; `openpyxl` for writes
  that need styling.

---

## UI workflow

Three-level drill-down with a top-level dashboard:

```
Dashboard / main window  (search + filters + farmer list)
        ↓
Farmer detail            (KETs with X/Y progress)
        ↓
KET detail               (per-field table, mark/unmark)
```

### Main window (`fo_ablak.py`) — dashboard

Top toolbar: app title, light/dark theme toggle, import button, export button,
settings button.

Below the toolbar:
- **Search box** with autocomplete (`QCompleter`) — matches against `nev` and
  `tamogatasi_azonosito` as the user types, search-engine style. Selecting a
  suggestion filters the table to that one farmer. An "Összes mutatása" button
  clears the search.
- **Filter chips / toggles** — always visible, persist across search:
  - `Mind` (default)
  - `Teljesített` — show only farmer/KET rows with completed tasks
  - `Nem teljesített` — show only rows with outstanding tasks
  - When filtering by task status, **show the entire row** for any farmer/KET with
    at least one matching task. Don't collapse rows.

Main content: table of all farmers with columns for name, támogatási azonosító,
aggregate progress ("14/22 teljesítve"), and deadline state badge (see Deadline
section). Sortable. Double-click → farmer detail.

### Farmer detail (`gazdalkodo_reszletek.py`)

Top: farmer's master data (name, cím, telefon, email, támogatási azonosító).
Below: their list of KETs with KET-level X/Y progress and deadline badge per KET.
Optional: flat list of all their fields with field-level status.
Back button returns to dashboard preserving search/filter state.

### KET detail (`ket_reszletek.py`)

Per-field table for one KET. Rows = fields, columns = the farmer's `vallalasok`
tasks. Each cell shows either the completion date or a "Teljesít" button.
Clicking "Teljesít" inserts a `teljesitesek` row with today's date (after
confirmation). Clicking a completed cell offers "Visszavon" (after confirmation).

### Mark / unmark confirmation

Every toggle (mark or unmark) opens a `QMessageBox` confirmation:

- **Mark:** *"Biztosan teljesítettnek jelöli a következő vállalást: `{vallalas}` a `{tabla}` táblán?"*
- **Unmark:** *"Biztosan visszavonja a teljesítést: `{vallalas}` a `{tabla}` táblán?"*

Both have **Igen** / **Mégse** buttons.

---

## Deadline states & szankció

The 5-year window is **calendar-aligned**, not per-KET. Current window: **2025-01-01
through 2029-12-31**. Next: 2030-01-01 through 2034-12-31, and so on.

For each KET that is **not yet fully complete**, compute the months remaining until
the current window's end date and assign a state:

| State    | Color (light)   | Color (dark)    | Condition                                  |
| -------- | --------------- | --------------- | ------------------------------------------ |
| Zöld     | `#4A7C59`       | `#6BA77B`       | More than 18 months remaining              |
| Sárga    | `#D4A017`       | `#E8B83C`       | 18 months or less remaining                |
| Piros    | `#C0392B`       | `#E74C3C`       | 12 months or less remaining                |
| Szankció | `#6B1A1A`       | `#A03030`       | Window has ended, tasks still unfinished   |

Fully complete KETs show a neutral "Kész" indicator (success green check).

**Szankció flagging** is the post-deadline state. When the current window has
ended (today > 2029-12-31) and a KET still has unfinished `vallalasok × tablak`
pairs, every such pair carries a **SZANKCIÓ** badge in the KET detail. The KET
row in the dashboard and farmer detail also shows a szankció badge. Aggregate the
worst state up the hierarchy — a farmer with any szankció KET shows a szankció
badge at the dashboard level.

The deadline state calculation lives in `logika/ket_logika.py` and returns a
small enum (`Allapot.ZOLD`, `SARGA`, `PIROS`, `SZANKCIO`, `KESZ`) so the UI just
renders whatever the logic layer says.

---

## Visual design

**Title:** Agrotechnika Figyelő.

**Themes:** light and dark, toggleable from the toolbar. Theme preference saved to
the config file. Implement as two QSS stylesheets in `felulet/stilus.py`, applied
via `QApplication.setStyleSheet()`.

**Palette:**

| Role             | Light       | Dark        |
| ---------------- | ----------- | ----------- |
| Background       | `#FFFFFF`   | `#1E1E1E`   |
| Surface / card   | `#FAF7F0`   | `#2A2825`   |
| Text primary     | `#1A1A1A`   | `#F0EBE0`   |
| Text secondary   | `#555555`   | `#A8A39A`   |
| Accent (növény)  | `#4A7C59`   | `#6BA77B`   |
| Accent hover     | `#3D6649`   | `#7DB88B`   |
| Sárga warning    | `#D4A017`   | `#E8B83C`   |
| Piros warning    | `#C0392B`   | `#E74C3C`   |
| Szankció         | `#6B1A1A`   | `#A03030`   |
| Border / divider | `#E0DCD0`   | `#3A3835`   |

**Design principles:**
- Clean modern desktop look. No skeuomorphism.
- Generous whitespace, eye-friendly contrast.
- Plant green as the single accent color — used for primary buttons, active
  state, success indicators.
- Beige (`#FAF7F0`) for surface cards in light mode gives warmth without yellow.
- Rounded corners on cards and buttons (6–8 px radius).
- System font (PyQt6 default) with slight size bump for table content
  (10–11 pt).
- Status badges (zöld/sárga/piros/szankció) as small pill-shaped labels with
  matching background tint and dark text.

Specific layout decisions (button placement, exact sizes) are left to v1
implementation — pick reasonable defaults.

---

## Configuration / first run

DB credentials live in a `.ini` file at the OS-appropriate user config dir:

- **Windows:** `%APPDATA%\AgrotechnikaFigyelo\kapcsolat.ini`
- **Linux/macOS:** `~/.config/AgrotechnikaFigyelo/kapcsolat.ini`

Resolve the path with `QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)`.

File format:

```ini
[adatbazis]
host = localhost
port = 3306
felhasznalo = root
jelszo = ...
adatbazis_nev = agrotechdb

[megjelenes]
tema = vilagos   ; or "sotet"
```

**First run flow:** `main.py` checks for the config file. If absent or unreadable,
open `beallitasok_ablak.py` (a `QDialog`) where the admin enters credentials.
On save, write the file and proceed. On subsequent runs, load directly.

Provide a "Beállítások" button in the main window toolbar to edit credentials
and theme later.

---

## Decisions already made (don't relitigate)

- Python + PyQt6 + SQLAlchemy + MySQL + pandas/openpyxl/python-calamine,
  packaged with PyInstaller. **Not C#, not WinForms, not Tkinter, not SQLite.**
- KET completion is **derived, never stored**.
- Obligations live at farmer level (`vallalasok.gazdalkodo_gid`), not per-KET.
- Fertilization = two `vallalasok` rows, fulfilled by counting Excel events.
  Same field can't be fertilized twice in one year.
- `tablaazonosito` stored as `VARCHAR(50)` from Excel directly.
- All identifiers, filenames, and folder names Hungarian. `main.py` is the sole
  English exception.
- The 4 task types are hardcoded with `eloiras_azonosito` 1–4. No lookup table.
- `vetett kultúra` and `vetési idő` columns are dropped on import.
- 5-year window is calendar-aligned (2025-2029, 2030-2034, ...), not per-KET.
- Deadline thresholds: sárga at ≤18 months, piros at ≤12 months, szankció after
  window end.
- v1: manual entry restricted to marking/unmarking completions. Farmers / KETs /
  fields come only from Excel.
- Re-import asks felülírás / összefűzés / mégse.
- Bad-data import errors skip the row, warn afterward, with file/sheet/row/column
  detail in the message.
- DB config in OS-appropriate user config dir, set on first run via dialog.
- Light + dark theme with the palette above.
- Mark / unmark requires a confirmation dialog each time.
- Search is autocomplete-style on name and támogatási azonosító.
- Task status filter (`Teljesített` / `Nem teljesített`) is always visible and
  composes with farmer search.

---

## Build order

1. `adatbazis/modellek.py` + `adatbazis/kapcsolat.py` — SQLAlchemy models, engine,
   session, config loading.
2. `logika/beallitasok.py` + `felulet/beallitasok_ablak.py` — config file
   handling and first-run dialog.
3. `logika/excel_logika.py` — import logic (including the fertilization counting
   and structured validation errors). Test against the 100-farmer dataset.
4. Service layer: `gazdalkodo_logika`, `ket_logika` (incl. deadline state),
   `tabla_logika` (mark/unmark).
5. `felulet/stilus.py` — light + dark QSS stylesheets.
6. UI screens — `fo_ablak`, `gazdalkodo_reszletek`, `ket_reszletek`,
   `excel_parbeszedablak`. Wire search, filters, badges, theme toggle.
7. Excel export (back into `excel_logika.py`).
8. PyInstaller build at the end.

---

## Current state

Planning / architecture complete. **No code written yet.** Schema finalized, Excel
format finalized, 100-farmer test dataset generated and available for import
testing. All v1 design decisions resolved — no blocking open questions remain.
