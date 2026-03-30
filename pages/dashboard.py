import customtkinter as ctk
from utils.theme import *
from utils.session import Session
from db.connection import query_one, query
from routes.terms import get_current_term, get_all_terms, set_current_term, create_term


class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._build()

    def _build(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)

        user = Session.get()
        first_name = user["fullName"].split()[0] if user else "User"
        if first_name.lower() == "system":
            first_name = user.get("username", "Admin").title()

        term = get_current_term()
        term_label = f"Term {term['term']}, {term['year']}" if term else "No term set"

        # ── Header ────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left", fill="x", expand=True)
        heading(title_col, f"Welcome back, {first_name}").pack(anchor="w")
        muted(title_col, "Here's an overview of the school this term.").pack(anchor="w", pady=(2, 0))

        # Term badge + set term button
        term_frame = ctk.CTkFrame(header, fg_color="transparent")
        term_frame.pack(side="right")

        self._term_badge = ctk.CTkFrame(term_frame, fg_color=ACCENT_BG, corner_radius=8)
        self._term_badge.pack(side="left", padx=(0, 8))
        self._term_label_widget = ctk.CTkLabel(
            self._term_badge, text=term_label,
            text_color=ACCENT, font=("", 12, "bold"))
        self._term_label_widget.pack(padx=12, pady=6)

        ghost_btn(term_frame, "Set term", command=self._open_term_dialog,
                  width=90).pack(side="left")

        # ── Stat cards ────────────────────────────────────────
        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 14))
        stats_row.columnconfigure((0, 1, 2, 3), weight=1, uniform="stat")

        total_students = (query_one(
            "SELECT COUNT(*) AS n FROM students WHERE status='active'") or {}).get("n", 0)
        total_classes = (query_one(
            "SELECT COUNT(*) AS n FROM classes") or {}).get("n", 0)
        pending = (query_one(
            "SELECT COUNT(*) AS n FROM assessments a "
            "WHERE NOT EXISTS (SELECT 1 FROM marks_new m WHERE m.assessment_id=a.id)"
        ) or {}).get("n", 0)

        school_mean_row = query_one(
            "SELECT ROUND(AVG(percentage), 1) AS mean FROM marks_new"
        ) or {}
        school_mean = school_mean_row.get("mean") or "—"
        mean_sub = "school average" if school_mean != "—" else "no marks yet"

        stats = [
            ("Total students", str(total_students), "active enrolment"),
            ("School mean",    str(school_mean),     mean_sub),
            ("Classes",        str(total_classes),   "across all forms"),
            ("Marks pending",  str(pending),         "assessments without marks"),
        ]
        for col, (lbl, val, sub) in enumerate(stats):
            c = ctk.CTkFrame(stats_row, fg_color="#F3F4F6", corner_radius=8)
            c.grid(row=0, column=col, padx=(0, 10) if col < 3 else 0, sticky="ew")
            inner = ctk.CTkFrame(c, fg_color="transparent")
            inner.pack(padx=14, pady=12, fill="both")
            muted(inner, lbl, size=11).pack(anchor="w")
            label(inner, val, size=22, weight="bold").pack(anchor="w", pady=(2, 0))
            color = DANGER if (lbl == "Marks pending" and int(val or 0) > 0) else TEXT_MUTED
            ctk.CTkLabel(inner, text=sub, font=("", 11),
                         text_color=color).pack(anchor="w")

        # ── Bottom row ────────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="both", expand=True)
        bottom.columnconfigure(0, weight=3)
        bottom.columnconfigure(1, weight=2)

        # Subject performance
        subj_card = card(bottom)
        subj_card.grid(row=0, column=0, padx=(0, 12), sticky="nsew")
        sp = ctk.CTkFrame(subj_card, fg_color="transparent")
        sp.pack(padx=16, pady=14, fill="both", expand=True)
        label(sp, "Subject performance — school average",
              size=13, weight="bold").pack(anchor="w", pady=(0, 10))

        # Load real subject averages from marks
        subject_avgs = query(
            """
            SELECT s.name, AVG(m.percentage) AS avg_score
            FROM marks_new m
            JOIN subjects s ON m.subject_id = s.id
            GROUP BY s.id, s.name
            ORDER BY avg_score ASC
            """
        )

        if not subject_avgs:
            ctk.CTkFrame(sp, fg_color="#F3F4F6", corner_radius=8).pack(
                fill="x", pady=(8, 0))
            no_data = ctk.CTkFrame(sp, fg_color="#F3F4F6", corner_radius=8)
            no_data.pack(fill="x", pady=(4, 0))
            ctk.CTkLabel(no_data,
                         text="No exam data yet.",
                         font=("", 13, "bold"), text_color=TEXT).pack(
                anchor="w", padx=14, pady=(10, 2))
            ctk.CTkLabel(no_data,
                         text="Subject averages will appear here after\n"
                              "marks have been entered and analysed.",
                         font=("", 12), text_color=TEXT_MUTED,
                         justify="left").pack(anchor="w", padx=14, pady=(0, 10))
        else:
            school_mean = sum(r["avg_score"] for r in subject_avgs) / len(subject_avgs)
            for r in subject_avgs:
                score = round(r["avg_score"], 1)
                low = score < school_mean * 0.9
                row_f = ctk.CTkFrame(sp, fg_color="transparent")
                row_f.pack(fill="x", pady=3)
                ctk.CTkLabel(row_f, text=r["name"], font=("", 12),
                             text_color=TEXT_MUTED, width=120,
                             anchor="w").pack(side="left")
                bar_bg = ctk.CTkFrame(row_f, fg_color="#E5E7EB",
                                      corner_radius=3, height=6, width=140)
                bar_bg.pack(side="left", padx=8)
                bar_bg.pack_propagate(False)
                ctk.CTkFrame(bar_bg,
                             fg_color=DANGER if low else ACCENT,
                             corner_radius=3, height=6,
                             width=int(min(score * 1.4, 140))).place(x=0, y=0)
                ctk.CTkLabel(row_f, text=f"{score}", font=("", 12, "bold"),
                             text_color=DANGER if low else TEXT,
                             width=36).pack(side="left")

        # Activity
        act_card = card(bottom)
        act_card.grid(row=0, column=1, sticky="nsew")
        ap = ctk.CTkFrame(act_card, fg_color="transparent")
        ap.pack(padx=16, pady=14, fill="both", expand=True)
        label(ap, "Recent activity", size=13, weight="bold").pack(anchor="w", pady=(0, 8))

        logs = query(
            "SELECT al.action, al.details, al.created_at "
            "FROM audit_logs al ORDER BY al.created_at DESC LIMIT 6"
        )
        log_colors = {
            "LOGIN": SUCCESS, "LOGOUT": TEXT_MUTED,
            "MARKS_ENTRY": SUCCESS, "MARKS_BULK": SUCCESS,
            "STUDENT_CREATE": ACCENT, "STUDENT_EDIT": ACCENT,
            "STUDENT_TRANSFER": WARNING, "STUDENT_ARCHIVE": DANGER,
        }
        if logs:
            for log in logs:
                r = ctk.CTkFrame(ap, fg_color="transparent")
                r.pack(fill="x", pady=4)
                ctk.CTkFrame(r, fg_color=log_colors.get(log["action"], TEXT_MUTED),
                             width=8, height=8, corner_radius=4).pack(side="left", padx=(0, 8))
                col = ctk.CTkFrame(r, fg_color="transparent")
                col.pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(col, text=log["details"] or log["action"],
                             font=("", 11), text_color=TEXT,
                             anchor="w", wraplength=200).pack(anchor="w")
                ctk.CTkLabel(col, text=str(log["created_at"])[:16],
                             font=("", 10), text_color=TEXT_MUTED,
                             anchor="w").pack(anchor="w")
                divider(ap).pack(fill="x", pady=(2, 0))
        else:
            muted(ap, "No activity yet.").pack(anchor="w")

    def _open_term_dialog(self):
        TermDialog(self, on_change=self._refresh_term)

    def _refresh_term(self):
        term = get_current_term()
        term_label = f"Term {term['term']}, {term['year']}" if term else "No term set"
        self._term_label_widget.configure(text=term_label)


# ── Term management dialog ────────────────────────────────────
class TermDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_change):
        super().__init__(parent)
        self.title("Manage terms")
        self.geometry("540x500")
        self.resizable(False, False)
        self.grab_set()
        self._on_change = on_change
        self._build()

    def _build(self):
        f = ctk.CTkFrame(self, fg_color=BG)
        f.pack(fill="both", expand=True, padx=36, pady=32)

        heading(f, "Set current term", size=16).pack(anchor="w", pady=(0, 4))
        muted(f, "Select the active term or create a new one.").pack(anchor="w", pady=(0, 14))

        # Existing terms list
        self._terms_frame = ctk.CTkScrollableFrame(f, fg_color=SURFACE,
                                                    corner_radius=8,
                                                    border_color=BORDER,
                                                    border_width=1,
                                                    height=160)
        self._terms_frame.pack(fill="x", pady=(0, 14))
        self._render_terms()

        # Create new term
        divider(f).pack(fill="x", pady=(0, 12))
        muted(f, "Create new term").pack(anchor="w", pady=(0, 6))

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x")

        self._year_entry = ctk.CTkEntry(row, placeholder_text="Year e.g. 2026",
                                         width=150, fg_color=SURFACE,
                                         border_color=BORDER)
        self._year_entry.pack(side="left", padx=(0, 8))

        self._term_var = ctk.StringVar(value="1")
        ctk.CTkOptionMenu(row, variable=self._term_var,
                          values=["1", "2", "3"], width=80,
                          fg_color=SURFACE, button_color=BORDER,
                          text_color=TEXT, dropdown_fg_color=SURFACE,
                          ).pack(side="left", padx=(0, 8))

        primary_btn(row, "Create", command=self._create_term,
                    width=90).pack(side="left")

        self._msg = ctk.CTkLabel(f, text="", font=("", 12), text_color=DANGER)
        self._msg.pack(anchor="w", pady=(8, 0))

    def _render_terms(self):
        for w in self._terms_frame.winfo_children():
            w.destroy()

        terms = get_all_terms()
        if not terms:
            muted(self._terms_frame, "No terms yet.").pack(pady=8)
            return

        for t in terms:
            is_current = bool(t["is_current"])
            row = ctk.CTkFrame(self._terms_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            badge_color = ACCENT_BG if is_current else "#F3F4F6"
            badge_text_color = ACCENT if is_current else TEXT_MUTED
            badge = ctk.CTkFrame(row, fg_color=badge_color, corner_radius=6)
            badge.pack(side="left")
            ctk.CTkLabel(badge,
                         text=f"Term {t['term']}, {t['year']}",
                         font=("", 12, "bold" if is_current else "normal"),
                         text_color=badge_text_color).pack(padx=10, pady=4)

            if is_current:
                ctk.CTkLabel(row, text="  ✓ Current",
                             font=("", 11), text_color=SUCCESS).pack(side="left")
            else:
                ctk.CTkButton(row, text="Set as current", width=110, height=28,
                              fg_color="transparent", border_color=BORDER,
                              border_width=1, text_color=TEXT, corner_radius=6,
                              hover_color=BG, font=("", 11),
                              command=lambda tid=t["id"]: self._set_current(tid)
                              ).pack(side="right")

    def _set_current(self, term_id):
        set_current_term(term_id)
        self._render_terms()
        self._on_change()

    def _create_term(self):
        self._msg.configure(text="")
        year_str = self._year_entry.get().strip()
        if not year_str.isdigit():
            self._msg.configure(text="Enter a valid year e.g. 2026.")
            return
        ok, msg = create_term(int(year_str), int(self._term_var.get()))
        if ok:
            self._msg.configure(text_color=SUCCESS, text=msg)
            self._year_entry.delete(0, "end")
            self._render_terms()
        else:
            self._msg.configure(text_color=DANGER, text=msg)
