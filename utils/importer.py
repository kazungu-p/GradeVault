import csv
from pathlib import Path


def read_students_from_file(filepath: str) -> tuple[list[dict], str]:
    """
    Read student rows from a CSV or Excel file.
    Returns (rows, warning_message).

    Supported column names (case-insensitive, flexible):
        Name:             full_name, name, student name, fullname
        Admission number: admission_number, admission_no, adm_no, admno, admission
        Gender:           gender, sex
        Class:            class, grade, form  (informational only — ignored during import)
        Stream:           stream              (informational only — ignored during import)
        Empty columns:    silently skipped
    """
    path = Path(filepath)
    ext  = path.suffix.lower()

    try:
        if ext == ".csv":
            raw_rows = _read_csv(filepath)
        elif ext in (".xlsx", ".xls"):
            raw_rows = _read_excel(filepath)
        else:
            return [], f"Unsupported file type '{ext}'. Use .csv or .xlsx"
    except Exception as e:
        return [], f"Could not read file: {e}"

    if not raw_rows:
        return [], "File is empty or has no data rows."

    NAME_ALIASES = {"full_name", "name", "student name", "student_name",
                    "fullname", "names", "full name"}
    ADM_ALIASES  = {"admission_number", "admission_no", "adm_no", "admno",
                    "admission", "adm", "adm. no", "adm. number",
                    "admission number", "reg no", "reg_no", "regno",
                    "adm no", "adm number"}
    GEN_ALIASES  = {"gender", "sex"}

    normalised = []
    warnings   = []

    for i, row in enumerate(raw_rows, start=2):
        # Normalise keys: strip whitespace, lowercase, skip empty keys
        lower = {}
        for k, v in row.items():
            key = str(k).strip().lower() if k else ""
            if key:  # skip empty column headers
                lower[key] = str(v).strip() if v is not None else ""

        name = next((lower[k] for k in lower if k in NAME_ALIASES), "")
        adm  = next((lower[k] for k in lower if k in ADM_ALIASES),  "")
        gen  = next((lower[k] for k in lower if k in GEN_ALIASES),  "")

        # Skip completely empty rows
        if not any(lower.values()):
            continue

        if not name:
            warnings.append(f"Row {i}: missing name — skipped.")
            continue
        if not adm:
            warnings.append(f"Row {i}: missing admission number — skipped.")
            continue

        gen_clean = gen.upper()[:1] if gen.upper()[:1] in ("M", "F") else None

        normalised.append({
            "full_name":        name,
            "admission_number": adm,
            "gender":           gen_clean,
        })

    warn_str = "\n".join(warnings) if warnings else ""
    return normalised, warn_str


def _read_csv(filepath: str) -> list[dict]:
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def _read_excel(filepath: str) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    result  = []
    for row in rows[1:]:
        if all(v is None for v in row):
            continue
        result.append({
            headers[i]: (str(row[i]).strip() if row[i] is not None else "")
            for i in range(len(headers))
        })
    wb.close()
    return result


def sample_csv_template() -> str:
    return (
        "full_name,admission_number,gender\n"
        "Jane Mwangi,2026001,F\n"
        "Brian Otieno,2026002,M\n"
        "Amina Hassan,2026003,F\n"
    )
