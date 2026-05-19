# Getting Started — Agrotechnika Figyelő with Claude Code

A walkthrough for building the v1 app from a clean machine. Keep this open while you
work; CLAUDE.md is for Claude Code, this is for you.

---

## 1. Prerequisites (one-time)

Install in this order:

1. **MySQL 8.x** — running locally. On Windows use the MySQL Installer; on Linux
   `sudo apt install mysql-server`. Note the root password.
2. **Python 3.11 or 3.12** — make sure `python --version` works in a new terminal.
   On Windows tick "Add Python to PATH" during install.
3. **Node.js 20+** — Claude Code needs it. Verify with `node --version`.
4. **Git** — `git --version`.
5. **Claude Code** — `npm install -g @anthropic-ai/claude-code`, then
   `claude --version` to confirm. Sign in with `claude` on first launch. Latest
   install instructions: https://docs.claude.com/en/docs/claude-code/overview
6. **An editor** — VS Code is a good default. Claude Code runs in the terminal,
   not in the editor, but you'll want the editor side-by-side.

### Create the empty database

In a MySQL shell (`mysql -u root -p`):

```sql
CREATE DATABASE agrotechdb CHARACTER SET utf8mb4 COLLATE utf8mb4_hungarian_ci;
CREATE USER 'agro_admin'@'localhost' IDENTIFIED BY 'PICK_A_PASSWORD';
GRANT ALL PRIVILEGES ON agrotechdb.* TO 'agro_admin'@'localhost';
FLUSH PRIVILEGES;
```

Save the user and password — you'll type them into the app's first-run config dialog.

---

## 2. Project setup (one-time)

```bash
mkdir agrotechnika_figyelo
cd agrotechnika_figyelo
git init
```

Drop **CLAUDE.md** in the project root.

Create a `test_data/` folder and put the 8 generated Excel files in it
(`Gazd_alapadatok.xlsx`, `Agrotechnika_vállalások.xlsx`, `KETEK.xlsx`,
`Táblák_2025.xlsx` … `Táblák_2029.xlsx`).

Create a minimal `.gitignore`:

```
__pycache__/
*.pyc
.venv/
venv/
build/
dist/
*.spec
.idea/
.vscode/
test_data/   # remove this line if you want the test files committed
```

Launch Claude Code from inside the project directory:

```bash
claude
```

---

## 3. How to actually work with Claude Code

A few habits that make the difference between a smooth build and a frustrating one:

- **Start every session with**: *"Read CLAUDE.md before anything else."* Claude
  Code is supposed to pick it up automatically, but a one-line reminder costs
  nothing.
- **Plan mode** (toggle with `Shift+Tab`) is for the start of each phase — Claude
  writes the plan, you adjust, then it executes. Use it for anything bigger than
  one file.
- **One phase per session.** Use `/clear` between phases so context doesn't get
  polluted. Old phase details aren't useful once that code is committed.
- **Esc** stops Claude mid-action without losing context — use it the moment
  something feels off. **Esc, Esc** or `/rewind` steps back through history if
  you want to undo a turn.
- **Commit after every working phase.** Git is your safety net. If a phase goes
  sideways you can roll back without losing the previous one.
- **When errors happen, paste the full traceback.** Don't summarize. Claude
  reads stack traces fluently.
- **Don't accept large diffs blindly.** If Claude produces 800 lines across 6
  files in one go, scroll through it. Catching a wrong assumption early is
  10× cheaper than chasing the bug later.
- **Push back when Claude over-engineers.** It's a real failure mode. "Simpler,
  please — drop the abstraction layer" works fine.
- **Permissions:** Claude Code asks before writing files and running commands.
  This is annoying but useful while you're learning the project's shape. Once
  you trust a phase, `Tab` accepts the current prompt. Don't enable full
  auto-mode until you've shipped v1.

---

## 4. Phase-by-phase build prompts

Each phase has: **goal**, **prompt to paste into Claude Code**, **what to verify**,
**what to commit**. Run them in order. Don't skip the verification steps — they
catch the bugs cheaply.

### Phase 0 — Scaffolding

**Goal:** project skeleton, no logic.

**Prompt:**

> Read CLAUDE.md. Scaffold the project per the Project layout section: create all
> directories with `__init__.py` files, an empty `main.py` placeholder, and a
> `requirements.txt` with pinned recent stable versions of the libraries listed
> under Tech stack (PyQt6, SQLAlchemy, mysql-connector-python, pandas,
> python-calamine, openpyxl, pyinstaller). Do not write any business logic. Stop
> when the skeleton is ready so I can create a venv and install.

**Verify:**

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# or: source .venv/bin/activate # Linux/macOS
pip install -r requirements.txt
```

All packages should install without errors.

**Commit:** `git add . && git commit -m "Phase 0: project skeleton"`

---

### Phase 1 — Database layer + first-run config

**Goal:** SQLAlchemy models, config file handling, first-run dialog.

**Prompt:**

> Read CLAUDE.md. Implement Phase 1 of the Build order:
>
> 1. `adatbazis/modellek.py` — SQLAlchemy models for all 5 tables, matching the
>    Schema SQL exactly (column types, FKs, the unique constraint on teljesitesek).
> 2. `adatbazis/kapcsolat.py` — engine and session factory that reads its config
>    via `logika/beallitasok.py`. On engine creation, run `Base.metadata.create_all`
>    so the schema is created if missing.
> 3. `logika/beallitasok.py` — load/save the `.ini` file at the OS-appropriate
>    user-config dir per CLAUDE.md's Configuration section.
> 4. `felulet/beallitasok_ablak.py` — a `QDialog` with fields for host, port,
>    user, password, db name, and theme; saves on OK.
> 5. `main.py` — on launch, if the config file is missing, open the dialog; on
>    OK, attempt to connect; on success, print "Kapcsolódás sikeres" and exit.
>
> Stop after this so I can run main.py and verify the schema appears in MySQL.

**Verify:**

```bash
python main.py
# Fill in the dialog, click OK.
# Should print "Kapcsolódás sikeres".
```

Then in MySQL:

```sql
USE agrotechdb;
SHOW TABLES;
-- Should list: gazdalkodo, ket, tablak, vallalasok, teljesitesek
```

**Commit:** `git commit -am "Phase 1: DB layer + first-run config"`

---

### Phase 2 — Excel import

**Goal:** populate the DB from the 8 test files.

**Prompt:**

> Read CLAUDE.md. Implement `logika/excel_logika.py` with the full import logic
> from the Import logic section. Cover:
> - Reading all 8 files with pandas + python-calamine.
> - Dropping `vetett kultúra` and `vetési idő` columns.
> - Inserting the 4 hardcoded `vallalasok` rows per farmer based on the igen/nem
>   columns, with the eloiras_azonosito → leiras mapping from the Task type
>   seeding table.
> - The fertilization counting across the 5-year window: ≥1 event fulfills task
>   1, ≥2 fulfills task 2.
> - The same-year same-field fertilization validation rule.
> - The structured warning format (file, sheet, row, column, value, explanation)
>   accumulated and returned from the import function — don't print, return.
> - Returning a summary object (counts of farmers, KETs, fields, completions, and
>   the list of warnings).
>
> Then add `import_test.py` at the project root that imports from `./test_data/`
> and pretty-prints the summary. Stop so I can run it.

**Verify:**

```bash
python import_test.py
```

Expect ~100 farmers, ~150–250 KETs, more fields, and a sensible number of
completions. Then in MySQL:

```sql
SELECT COUNT(*) FROM gazdalkodo;
SELECT COUNT(*) FROM ket;
SELECT COUNT(*) FROM tablak;
SELECT COUNT(*) FROM vallalasok;
SELECT COUNT(*) FROM teljesitesek;
```

Numbers should match the summary.

**Commit:** `git commit -am "Phase 2: Excel import"`

---

### Phase 3 — Service layer

**Goal:** the logic the UI will call.

**Prompt:**

> Read CLAUDE.md. Implement the service layer:
>
> - `logika/gazdalkodo_logika.py`: `keres(reszlet)` for prefix-matching name and
>   `tamogatasi_azonosito` (returns suggestions for the autocomplete);
>   `osszes()`; `egy(gid)` returning the farmer with KETs, fields, vallalasok,
>   and teljesitesek eager-loaded.
> - `logika/ket_logika.py`: `haladas(kid)` returning (kész, összes) tuple for
>   X/Y; `allapot(kid)` returning the `Allapot` enum (ZOLD/SARGA/PIROS/SZANKCIO/KESZ)
>   per the Deadline section; helper to get the current 5-year window end date.
> - `logika/tabla_logika.py`: `teljesit(vid, tid)` inserts a teljesitesek row with
>   today's date after validating the farmer owns the field; `visszavon(vid, tid)`
>   deletes it.
>
> Add `service_test.py` at the project root that exercises each function against
> the imported data and prints results. Stop so I can run it.

**Verify:** run `service_test.py`; pick a farmer, check that progress and state
match what you'd compute by hand. Mark a task done, run again, see X go up by 1.
Unmark it, see X go back down.

**Commit:** `git commit -am "Phase 3: service layer"`

---

### Phase 4 — UI part 1: theme + dashboard

**Goal:** the app launches with a working main window.

**Prompt:**

> Read CLAUDE.md. Implement:
>
> - `felulet/stilus.py` with two QSS stylesheets (light and dark) matching the
>   palette in CLAUDE.md's Visual design section. Export a `betoltes(tema)`
>   function returning the stylesheet string.
> - `felulet/fo_ablak.py` — main window per the UI workflow section. Toolbar
>   with title, theme toggle (persists to config via beallitasok), import button
>   (no-op for now), export button (no-op), settings button (reopens
>   `beallitasok_ablak`). Below: search box wired to QCompleter against
>   gazdalkodo_logika.keres; filter chips `Mind` / `Teljesített` / `Nem
>   teljesített` that compose with search; main table with columns name,
>   támogatási azonosító, progress, state badge. Double-click row → for now
>   just print the farmer's gid.
>
> Update `main.py` to launch the main window after a successful DB connection.
> Stop so I can click around.

**Verify:** `python main.py`, click through. Theme toggle works. Search
autocompletes. Filters change the table contents. Badges show correct colors.

**Commit:** `git commit -am "Phase 4: theme and dashboard"`

---

### Phase 5 — UI part 2: detail screens + import dialog

**Goal:** the full drill-down flow and Excel import dialog.

**Prompt:**

> Read CLAUDE.md. Implement:
>
> - `felulet/gazdalkodo_reszletek.py` — farmer detail per UI workflow. Top:
>   master data. Below: KETs with progress and badges, double-click → KET detail.
>   Back button returns to the dashboard preserving its search/filter state.
> - `felulet/ket_reszletek.py` — per-field × per-task table. Cells show either
>   the completion date or a "Teljesít" button. Click Teljesít → confirmation
>   dialog with the exact wording from CLAUDE.md → call tabla_logika.teljesit.
>   Click a completed cell → "Visszavon" confirmation → tabla_logika.visszavon.
>   Update the cell after each action.
> - `felulet/excel_parbeszedablak.py` — folder picker for the 8 files. If DB has
>   data, show felülírás / összefűzés / mégse choice. Run excel_logika and show
>   the returned warnings in a dialog listing every skipped row with full source
>   info.
>
> Wire double-click navigation in fo_ablak (dashboard → farmer detail), the
> import button to the dialog, and the back buttons. Stop so I can drive the
> full flow.

**Verify:** import a fresh dataset, drill down to a KET, mark/unmark tasks, check
that progress updates everywhere (dashboard, farmer detail, KET detail).

**Commit:** `git commit -am "Phase 5: detail screens + import dialog"`

---

### Phase 6 — Excel export

**Goal:** roundtrip — export current DB state back to the 8-file format.

**Prompt:**

> Read CLAUDE.md. Add export functions to `logika/excel_logika.py` that
> reproduce all 8 files in the exact documented format. For Táblák_YYYY.xlsx,
> bucket teljesitesek rows by year (based on teljesules_datuma) and write the
> dates into the right columns; leave `vetett kultúra` and `vetési idő` empty
> since they weren't stored. Wire the export button to a folder picker.
> Stop so I can diff exported files against the originals.

**Verify:**

```bash
# Export to a temp folder, then compare structurally:
python -c "import pandas as pd; print(pd.read_excel('test_data/KETEK.xlsx').equals(pd.read_excel('exported/KETEK.xlsx')))"
```

Columns and rows should match (order may differ — that's fine for v1).

**Commit:** `git commit -am "Phase 6: Excel export"`

---

### Phase 7 — Packaging with PyInstaller

**Goal:** a single `.exe` runnable on a machine without Python installed.

**Prompt:**

> Read CLAUDE.md. Configure PyInstaller to build a single-file Windows
> executable named `AgrotechnikaFigyelo.exe`. Bundle all PyQt6 plugins needed
> for the UI to render correctly (qt6_plugins). Suggest a small app icon
> (.ico) — generate placeholder if needed — and include it. Provide a single
> build command and a brief README note on how to run it.

**Verify:**

```bash
.\dist\AgrotechnikaFigyelo.exe
```

App launches, config dialog appears on first run, full flow works.

**Commit:** `git commit -am "Phase 7: PyInstaller packaging"` then tag:
`git tag v1.0.0`.

---

## 5. Troubleshooting

| Symptom | Try |
| --- | --- |
| Claude writes too much / too fast | "Stop. Do only step 1 first, show me, then we'll continue." |
| Wrong direction halfway through | Press Esc. Redirect with a one-liner. |
| Bad assumption baked into earlier code | `/rewind` to that turn, restart from there. |
| DB connection fails | Run the Phase 1 verify SQL by hand. The error message in Hungarian comes from `kapcsolat.py`; the real cause is usually the password or the user's grants. |
| Import fills DB with zeros | Run `import_test.py` and read the warnings list — almost always a column-name mismatch in one of the Excel files. |
| PyQt6 install fails on Windows | Update pip first: `python -m pip install --upgrade pip`. PyQt6 wheels need pip ≥ 21. |
| `python-calamine` install fails | It needs a recent pip. If still broken, drop it and let pandas use `openpyxl` for reads too — slower but works. |
| App launches blank / wrong theme | The QSS path is wrong or the file is empty. Check `felulet/stilus.py` output by printing the loaded stylesheet. |
| Mark-done updates the DB but not the UI | The cell isn't reloading after the service call. Tell Claude: "Repaint the row after teljesit/visszavon returns." |
| PyInstaller .exe crashes on launch with PyQt error | Almost always missing plugins. Add `--collect-all PyQt6` to the build command. |

---

## 6. After v1

Things to consider once v1 ships:

- **Backup button** — `mysqldump agrotechdb > backup_YYYYMMDD.sql` triggered from
  the toolbar. One-day task.
- **Logging** — a rotating log file under the user-config dir for errors and
  imports. Helps when something goes wrong on the admin's machine.
- **Custom skill** — if you find yourself re-explaining the import quirks to
  Claude Code repeatedly, codify them as a project skill under `.claude/skills/`.
- **Tests** — pytest against a SQLite-backed fixture for the service layer. The
  import logic in particular benefits from regression tests.
- **Migrations** — if the schema starts evolving, add Alembic before the second
  schema change, not after the fifth.

---

## 7. Quick reference

**Start a session:**
```bash
cd agrotechnika_figyelo
claude
```

**First message of every session:**
> Read CLAUDE.md before anything else.

**Useful Claude Code commands:**
- `/init` — auto-generate a CLAUDE.md (we already have one, skip)
- `/clear` — wipe conversation context
- `/rewind` — restore to a previous turn
- `Esc` — stop current action, keep context
- `Esc Esc` — open the rewind menu
- `Shift+Tab` — toggle plan mode
- `/permissions` — manage what Claude can do without asking

**Project commands you'll re-run a lot:**
```bash
.venv\Scripts\activate          # activate venv (Windows)
python main.py                  # launch the app
python import_test.py           # re-run a test import
python service_test.py          # exercise the service layer
git status                      # before every commit
```
