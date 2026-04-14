from db.connection import query, query_one, execute


# ── Student contacts ──────────────────────────────────────────
def get_contacts(student_id: int) -> list:
    return query(
        "SELECT * FROM student_contacts WHERE student_id=? ORDER BY is_primary DESC, name",
        (student_id,),
    )


def add_contact(student_id: int, name: str, relationship: str,
                phone: str, is_primary: bool = False) -> tuple[bool, str]:
    name  = name.strip()
    phone = phone.strip()
    if not name:
        return False, "Contact name is required."
    if not phone:
        return False, "Phone number is required."
    # Clean phone — ensure starts with +254 or 07/01
    phone = _clean_phone(phone)
    if is_primary:
        execute("UPDATE student_contacts SET is_primary=0 WHERE student_id=?",
                (student_id,))
    execute(
        "INSERT INTO student_contacts (student_id, name, relationship, phone, is_primary)"
        " VALUES (?,?,?,?,?)",
        (student_id, name, relationship, phone, 1 if is_primary else 0),
    )
    return True, "Contact added."


def update_contact(contact_id: int, name: str, relationship: str,
                   phone: str, is_primary: bool) -> tuple[bool, str]:
    name  = name.strip()
    phone = _clean_phone(phone.strip())
    if not name or not phone:
        return False, "Name and phone are required."
    if is_primary:
        row = query_one("SELECT student_id FROM student_contacts WHERE id=?",
                        (contact_id,))
        if row:
            execute("UPDATE student_contacts SET is_primary=0 WHERE student_id=?",
                    (row["student_id"],))
    execute(
        "UPDATE student_contacts SET name=?, relationship=?, phone=?, is_primary=?"
        " WHERE id=?",
        (name, relationship, phone, 1 if is_primary else 0, contact_id),
    )
    return True, "Contact updated."


def delete_contact(contact_id: int) -> None:
    execute("DELETE FROM student_contacts WHERE id=?", (contact_id,))


def _clean_phone(phone: str) -> str:
    """Normalise Kenyan phone to +254XXXXXXXXX."""
    digits = "".join(c for c in phone if c.isdigit() or c == "+")
    if digits.startswith("+"):
        return digits
    if digits.startswith("254"):
        return "+" + digits
    if digits.startswith("0") and len(digits) == 10:
        return "+254" + digits[1:]
    return phone  # return as-is if unrecognised


def get_primary_contacts_for_class(class_id: int) -> list:
    """All primary contacts for active students in a class."""
    return query(
        """
        SELECT s.full_name AS student_name, s.admission_number,
               c.name, c.phone, c.relationship
        FROM student_contacts c
        JOIN students s ON c.student_id = s.id
        WHERE s.class_id=? AND s.status='active' AND c.is_primary=1
        ORDER BY s.full_name
        """,
        (class_id,),
    )


def get_all_primary_contacts() -> list:
    return query(
        """
        SELECT s.full_name AS student_name, s.admission_number,
               cl.name AS class_name, cl.stream,
               c.name, c.phone, c.relationship
        FROM student_contacts c
        JOIN students s ON c.student_id = s.id
        JOIN classes cl ON s.class_id = cl.id
        WHERE s.status='active' AND c.is_primary=1
        ORDER BY cl.name, cl.stream, s.full_name
        """,
    )


# ── SMS ───────────────────────────────────────────────────────
def send_sms(recipients: list[dict], message: str,
             api_key: str, username: str) -> dict:
    """
    Send SMS via Africa's Talking.
    recipients: list of {name, phone}
    Returns {sent, failed, total, cost}
    """
    try:
        import warnings
        warnings.filterwarnings('ignore', category=UserWarning,
                               module='africastalking')
        import africastalking
    except ImportError:
        return {"error": "africastalking package not installed.\n"
                         "Run: pip install africastalking"}

    africastalking.initialize(username, api_key)
    sms = africastalking.SMS

    sent = failed = 0
    total_cost = "KES 0"

    for r in recipients:
        phone = r.get("phone", "")
        if not phone:
            failed += 1
            continue
        try:
            resp = sms.send(message, [phone])
            recipients_resp = resp.get("SMSMessageData", {}).get(
                "Recipients", [])
            for rec in recipients_resp:
                status = rec.get("status", "Failed")
                cost   = rec.get("cost", "")
                if status == "Success":
                    sent += 1
                else:
                    failed += 1
                _log_sms(r.get("name", phone), phone,
                         message, status, cost)
        except Exception as e:
            failed += 1
            _log_sms(r.get("name", phone), phone,
                     message, f"Error: {e}", "")

    return {"sent": sent, "failed": failed,
            "total": len(recipients)}


def _log_sms(recipient, phone, message, status, cost):
    execute(
        "INSERT INTO sms_log (recipient, phone, message, status, cost)"
        " VALUES (?,?,?,?,?)",
        (recipient, phone, message, status, cost),
    )


def get_sms_log(limit: int = 100) -> list:
    return query(
        "SELECT * FROM sms_log ORDER BY sent_at DESC LIMIT ?",
        (limit,),
    )


def get_at_credentials() -> tuple[str, str]:
    """Load saved Africa's Talking credentials from settings."""
    from routes.settings import get_setting
    return (get_setting("at_api_key", ""),
            get_setting("at_username", "sandbox"))


def save_at_credentials(api_key: str, username: str) -> None:
    from routes.settings import set_setting
    set_setting("at_api_key",  api_key)
    set_setting("at_username", username)
