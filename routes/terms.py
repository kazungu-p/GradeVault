from db.connection import query, query_one, execute


def get_current_term() -> dict | None:
    return query_one("SELECT * FROM terms WHERE is_current = 1")


def get_all_terms() -> list:
    return query("SELECT * FROM terms ORDER BY year DESC, term ASC")


def set_current_term(term_id: int) -> None:
    execute("UPDATE terms SET is_current = 0")
    execute("UPDATE terms SET is_current = 1 WHERE id = ?", (term_id,))


def create_term(year: int, term_number: int) -> tuple[bool, str]:
    if not (1 <= term_number <= 3):
        return False, "Term must be 1, 2 or 3."
    existing = query_one("SELECT id FROM terms WHERE year = ? AND term = ?",
                         (year, term_number))
    if existing:
        return False, f"Term {term_number}, {year} already exists."
    execute("INSERT INTO terms (year, term, is_current) VALUES (?, ?, 0)",
            (year, term_number))
    return True, "Term created."
