# GradeVault

**Offline-first school management system for Kenyan schools.**
Built with Python + CustomTkinter + SQLite. No internet required.

---

## What it does

GradeVault handles the full academic cycle for any school level:

| Level | Curriculum | Grading |
|---|---|---|
| PP1, PP2 | ECDE / CBC | EE / ME / AE / BE |
| Grade 1–3 | Lower Primary CBC | EE / ME / AE / BE (descriptive) |
| Grade 4–6 | Upper Primary CBC | EE / ME / AE / BE (descriptive) |
| Grade 7–9 | Junior Secondary CBC | EE / ME / AE / BE |
| Grade 10–12 | Senior Secondary CBC | EE / ME / AE / BE |
| Form 1–4 | Secondary 8-4-4 | A–E (KCSE, Best-7 rule) |

---

## Modules

### Dashboard
- Live stat cards: total students, school mean, classes, marks pending
- Clickable "marks pending" shows exactly which subjects are missing marks
- Subject performance chart
- Term management with assessments listed per term

### Students
- Paginated list (50/page) — fast even with 800+ students
- Filters: class, stream, gender, status (active/archived)
- Import from CSV or Excel with flexible column detection
- Export class lists as PDF, Excel or Word with gender filter
- Archive, transfer between classes

### Classes & Subjects
- Classes with optional streams
- Combined classes for optional subjects (e.g. Physics students from all Form 4 streams in one group)
- Bulk promote students at end of year
- Retire a class (archives all students)
- Subject management with active/inactive toggle

### Users & Permissions
- Roles: Admin, Teacher
- 7 granular permissions: enter_marks, manage_students, manage_exams, generate_reports, view_all_classes, manage_users, manage_subjects
- One teacher per subject+class enforced

### Marks Entry
- 3-step flow: Assessment → Class + Subject → Grid
- Auto-save on Tab/Enter plus Save All button
- Configurable marks out of per subject per assessment
- Subject enrollment per class (choose which students take each subject)
- Combined class enrollment pulls from all matching streams
- Remembers last class/subject selection per session

### Reports
- Generate PDF report cards for all students in a class
- Editable comment templates per performance band (Excellent/Good/Average/Below Average)
- Editable grading scale boundaries for KCSE and CBC
- Preview popup: Preview PDF, Save PDF, Print with printer selection

**Report card includes:**
- School logo or text header
- Student info, term, position in class
- All subjects taken — subjects counted in the mean marked with *
- Best-7 rule applied automatically for 8-4-4
- Descriptive grades (Exceeds Expectations etc.) for primary CBC
- Auto subject comments per grade
- Class teacher and principal comments (auto by band)

### Analytics
- School overview: mean, pass rate, grade distribution, per-class breakdown
- Subject performance ranked by mean
- Exam ranking with tie-aware positions
- Most improved students (compare two assessments)
- Most improved subjects with bar chart
- Filterable by term, assessment and class/stream

### Backup & Restore
- Save backup anywhere as a .gvbak file
- Quick auto-named backup to ~/.gradevault/backups/
- Restore with automatic safety backup created first
- Validates backup before restoring
- Recent backups list with restore/delete per entry

### Settings
- School name, motto, contact
- Logo upload — replaces text header on all printed documents

---

## Getting started

### Requirements
```
Python 3.11+
customtkinter
bcrypt
reportlab
openpyxl
Pillow
python-docx
```

### Install dependencies
```bash
pip install customtkinter bcrypt reportlab openpyxl Pillow python-docx
```

### Run
```bash
python main.py
```

The setup wizard runs on first launch and asks for school name, classes, streams, subjects and admin password.

---

## File structure

```
gradevault/
├── main.py                    # Entry point, shell, routing, sidebar
├── requirements.txt
├── assets/icon.png, icon.ico
├── db/
│   ├── connection.py
│   └── migrate.py
├── routes/
│   ├── assessments.py
│   ├── auth.py
│   ├── classes.py
│   ├── marks.py
│   ├── settings.py
│   ├── students.py
│   ├── terms.py
│   └── users.py
├── pages/
│   ├── analytics.py
│   ├── backup.py
│   ├── classes.py
│   ├── dashboard.py
│   ├── login.py
│   ├── marks.py
│   ├── reports.py
│   ├── settings.py
│   ├── setup_wizard.py
│   ├── splash.py
│   ├── students.py
│   └── users.py
└── utils/
    ├── backup.py
    ├── grading.py
    ├── importer.py
    ├── pdf_classlist.py
    ├── report_pdf.py
    ├── session.py
    └── theme.py
```

---

## Data location

```
~/.gradevault/
├── gradevault.db         # SQLite database
├── assets/               # School logo
└── backups/              # Auto-generated backups
```

---

## Key design decisions

- **Offline-first**: no server, no internet needed
- **Best-7 (8-4-4)**: Maths + best language + best 5 remaining = 7 subjects for mean
- **CBC**: all subjects used, descriptive grades for primary levels
- **Combined classes**: optional subjects group students from multiple streams
- **Pagination**: 50 students per page keeps UI fast with large rosters
