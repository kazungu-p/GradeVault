import csv
import io
from pathlib import Path


def read_students_from_file(filepath: str) -> tuple[list[dict], str]:
    """
    Read student rows from a CSV or Excel file.
    Returns (rows, error_message).
    Rows are dicts with keys: full_name, admission_number, gender (optional).

    Expected columns (any order, case-insensitive):
        full_name / name / student name
        admission_number / admission no / adm no / adm_no
        gender (optional)
    """
    path = Path(filepath)
    ext  = path.suffix.lower()

    try:
        if ext == ".csv":
            rows = _read_csv(filepath)
        elif ext in (".xlsx", ".xls"):
            rows = _read_excel(filepath)
        else:
            return [], f"Unsupported file type: {ext}. Use .csv or .xlsx"
    except Exception as e:
        return [], f"Could not read file: {e}"

    if not rows:
        return [], "File is empty or has no data rows."

    # Normalise column names
    NAME_ALIASES = {"full_name", "name", "student name", "student_name",
                    "fullname"}
    ADM_ALIASES  = {"admission_number", "admission_no", "adm_no",
                    "adm no", "admno", "admission"}
    GEN_ALIASES  = {"gender", "sex"}

    normalised = []
    errors = []
    for i, row in enumerate(rows, start=2):  # row 1 = header
        lower = {k.strip().lower(): str(v).strip() for k, v in row.items()}

        name = next((lower[k] for k in lower if k in NAME_ALIASES), "")
        adm  = next((lower[k] for k in lower if k in ADM_ALIASES),  "")
        gen  = next((lower[k] for k in lower if k in GEN_ALIASES),  "")

        if not name:
            errors.append(f"Row {i}: missing name — skipped.")
            continue
        if not adm:
            errors.append(f"Row {i}: missing admission number — skipped.")
            continue

        gen_clean = gen.upper()[:1] if gen.upper()[:1] in ("M", "F") else None

        normalised.append({
            "full_name":        name,
            "admission_number": adm,
            "gender":           gen_clean,
        })

    if errors:
        return normalised, "\n".join(errors)
    return normalised, ""


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
    """Return a sample CSV string the user can download as a template."""
    return (
        "full_name,admission_number,gender\n"
        "Jane Mwangi,2026001,F\n"
        "Brian Otieno,2026002,M\n"
        "Amina Hassan,2026003,F\n"
    )
