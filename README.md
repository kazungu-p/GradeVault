# GradeVault

Offline-first school analytics and administration system for Kenyan secondary schools.

## Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| UI         | CustomTkinter (Python/Tkinter)    |
| Database   | SQLite (Python stdlib)            |
| Auth       | bcrypt                            |
| PDF export | ReportLab                         |
| Import     | openpyxl (Excel), csv (stdlib)    |
| Language   | Python 3.11+                      |

## Getting started

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/gradevault.git
cd gradevault

# 2. Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python main.py
```

On first run, a setup wizard will guide you through:
- School name and motto
- Selecting your current classes (8-4-4, CBE Junior, CBE Senior)
- Configuring streams (optional)
- Loading subjects
- Setting your admin password

## Features

- **First-run setup wizard** — configure the school once, never again
- **Student management** — register, edit, transfer, archive students
- **Bulk import** — upload students from CSV or Excel
- **Class & subject management** — add/edit/delete classes, streams and subjects
- **Bulk promotion** — move an entire class to the next grade at year end
- **User & teacher management** — create accounts, assign permissions per teacher
- **Teacher assignments** — assign teachers to specific subjects and classes
- **PDF class lists** — generate and print class lists per class or all at once
- **Term management** — set and switch the current academic term
- **Audit logs** — every action is logged with user and timestamp
- **Role-based access** — Admin vs Teacher with 7 granular permissions
- **Fully offline** — no internet required after installation

## Permissions (teacher level)

| Permission         | Description                                      |
|--------------------|--------------------------------------------------|
| `enter_marks`      | Enter marks for assigned subjects & classes      |
| `manage_students`  | Add, edit, transfer and archive students         |
| `manage_exams`     | Create and manage assessments & CATs             |
| `generate_reports` | Export report cards and performance reports      |
| `view_all_classes` | View students and marks across all classes       |
| `manage_users`     | Add and edit teacher accounts (e.g. for a DOS)   |
| `manage_subjects`  | Add, edit and delete subjects and classes        |

## Project structure

```
gradevault/
├── main.py              # App entry point + shell + routing
├── requirements.txt
├── db/
│   ├── connection.py    # SQLite helpers
│   └── migrate.py       # Schema + seed (runs on startup)
├── routes/              # Business logic — direct DB calls
│   ├── auth.py
│   ├── students.py
│   ├── users.py
│   ├── classes.py
│   ├── marks.py
│   ├── terms.py
│   └── settings.py      # School settings + permissions
├── pages/               # CustomTkinter UI pages
│   ├── setup_wizard.py
│   ├── login.py
│   ├── dashboard.py
│   ├── students.py
│   ├── users.py
│   └── classes.py
└── utils/
    ├── theme.py          # Colors, fonts, reusable widgets
    ├── session.py        # In-memory session
    ├── importer.py       # CSV/Excel student import
    └── pdf_classlist.py  # PDF class list generation
```

## Packaging as a desktop app

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name GradeVault main.py
# Output: dist/GradeVault (macOS) or dist/GradeVault.exe (Windows)
```

## Curriculum support

- **8-4-4** — Form 1 to Form 4
- **CBE Junior Secondary** — Grade 7 to Grade 9
- **CBE Senior Secondary** — Grade 10 to Grade 12
- Mix and match — run multiple curricula simultaneously

## Roadmap

- [ ] Marks entry spreadsheet grid
- [ ] Automatic grading (KCSE scale)
- [ ] Report card PDF generation
- [ ] Analytics and performance charts
- [ ] Timetable (separate module)
- [ ] SMS results notification
- [ ] Multi-school support
