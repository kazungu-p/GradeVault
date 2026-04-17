import customtkinter as ctk
from utils.theme import *
from routes.classes import get_classes, bulk_promote
from db.connection import query, execute


# Auto-detect next class mapping
def _build_promotion_map(classes: list) -> list[dict]:
    """
    For each class, suggest the logical next class.
    e.g. Form 1 → Form 2, Grade 7 → Grade 8, PP1 → PP2
    Returns list of {from, to, students, suggested}
    """
    PROGRESSIONS = {
        "pp1": "pp2", "pp2": "grade 1",
        "grade 1": "grade 2", "grade 2": "grade 3",
        "grade 3": "grade 4", "grade 4": "grade 5",
        "grade 5": "grade 6", "grade 6": "grade 7",
        "grade 7": "grade 8", "grade 8": "grade 9",
        "grade 9": "grade 10", "grade 10": "grade 11",
        "grade 11": "grade 12",
        "form 1": "form 2", "form 2": "form 3",
        "form 3": "form 4",
    }

    # Build lookup: base_name → list of class dicts
    by_name = {}
    for c in classes:
        base = c["name"].lower().strip()
        by_name.setdefault(base, []).append(c)

    rows = []
    for c in classes:
        base = c["name"].lower().strip()
        next_base = PROGRESSIONS.get(base)

        student_count = (query(
            "SELECT COUNT(*) AS n FROM students "
            "WHERE class_id=? AND status='active'",
            (c["id"],)
        ) or [{}])[0].get("n", 0)

        cls_label = (f"{c['name']} {c['stream']}"
                     if c.get("stream") else c["name"])

        # Find matching next class (same stream if possible)
        next_cls = None
        if next_base and next_base in by_name:
            candidates = by_name[next_base]
            # Prefer same stream
            if c.get("stream"):
                next_cls = next(
                    (x for x in candidates
                     if x.get("stream") == c["stream"]),
                    candidates[0]
                )
            else:
                next_cls = candidates[0]

        next_label = None
        if next_cls:
            next_label = (f"{next_cls['name']} {next_cls['stream']}"
                          if next_cls.get("stream") else next_cls["name"])

        rows.append({
            "from_cls":    c,
            "from_label":  cls_label,
            "to_cls":      next_cls,
            "to_label":    next_label,
            "students":    student_count,
            "include":     True,
            "is_terminal": next_base is None or next_base not in by_name,
        })

    # Sort by curriculum order
    ORDER = ["pp1","pp2","grade 1","grade 2","grade 3","grade 4",
             "grade 5","grade 6","grade 7","grade 8","grade 9",
             "grade 10","grade 11","grade 12",
             "form 1","form 2","form 3","form 4"]
    rows.sort(key=lambda r: ORDER.index(
        r["from_cls"]["name"].lower().strip())
        if r["from_cls"]["name"].lower().strip() in ORDER else 99)

    return rows


class PromotionWizard(ctk.CTkToplevel):
    def __init__(self, parent, on_done=None):
        super().__init__(parent)
        self.title("End-of-year promotion")
        self.geometry("720x580")
        self.resizable(False, False)
        self.grab_set()
        self._on_done = on_done
        self._step    = 1
        self._rows    = []
        self._build()

    def _build(self):
        self._outer = ctk.CTkFrame(self, fg_color=BG)
        self._outer.pack(fill="both", expand=True)
        self._show_step1()

    def _clear(self):
        for w in self._outer.winfo_children():
            w.destroy()

    # ── Step 1: Review & configure ───────────────────────────
    def _show_step1(self):
        self._clear()
        f = ctk.CTkFrame(self._outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=24)

        heading(f, "End-of-year promotion", size=16
                ).pack(anchor="w", pady=(0, 4))
        muted(f, "Review each class → next class mapping. "
                 "Untick classes you don't want to promote yet."
              ).pack(anchor="w", pady=(0, 14))

        classes = get_classes()
        self._rows = _build_promotion_map(classes)
        all_classes = {c["id"]: c for c in classes}

        # Table header
        thead = ctk.CTkFrame(f, fg_color="#F3F4F6", corner_radius=6)
        thead.pack(fill="x", pady=(0, 4))
        for txt, w in [("Include", 70), ("From class", 160),
                        ("Students", 80), ("→  To class", 200),
                        ("Status", 140)]:
            ctk.CTkLabel(thead, text=txt, font=("", 11, "bold"),
                         text_color=TEXT_MUTED, width=w,
                         anchor="w").pack(
                side="left", padx=(10, 0), pady=6)

        scroll = ctk.CTkScrollableFrame(
            f, fg_color=SURFACE,
            border_color=BORDER, border_width=1,
            corner_radius=8, height=280)
        scroll.pack(fill="x", pady=(0, 14))

        self._include_vars  = []
        self._to_class_vars = []

        all_labels = ["— (graduate / leave)"] + [
            f"{c['name']} {c['stream']}".strip()
            if c.get("stream") else c["name"]
            for c in classes
        ]

        for i, row in enumerate(self._rows):
            bg = SURFACE if i % 2 == 0 else "#FAFAFA"
            r  = ctk.CTkFrame(scroll, fg_color=bg,
                               corner_radius=0, height=38)
            r.pack(fill="x")
            r.pack_propagate(False)

            inc_var = ctk.BooleanVar(
                value=row["include"] and not row["is_terminal"])
            self._include_vars.append(inc_var)
            ctk.CTkCheckBox(r, text="", variable=inc_var,
                            width=70, fg_color=ACCENT,
                            hover_color=ACCENT_DARK,
                            ).pack(side="left", padx=(10, 0))

            ctk.CTkLabel(r, text=row["from_label"],
                         font=("", 12), text_color=TEXT,
                         width=160, anchor="w"
                         ).pack(side="left", padx=(10, 0))
            ctk.CTkLabel(r, text=str(row["students"]),
                         font=("", 12), text_color=TEXT_MUTED,
                         width=80, anchor="w"
                         ).pack(side="left", padx=(10, 0))

            # To class dropdown
            default = row["to_label"] or "— (graduate / leave)"
            to_var  = ctk.StringVar(value=default)
            self._to_class_vars.append(to_var)
            ctk.CTkOptionMenu(r, variable=to_var,
                              values=all_labels, width=190,
                              fg_color=SURFACE if not row["is_terminal"]
                              else "#F3F4F6",
                              button_color=BORDER, text_color=TEXT,
                              dropdown_fg_color=SURFACE,
                              ).pack(side="left", padx=(10, 0))

            status = ("Terminal (graduates)" if row["is_terminal"]
                      else f"→ {row['to_label'] or '—'}")
            ctk.CTkLabel(r, text=status, font=("", 11),
                         text_color=TEXT_MUTED if not row["is_terminal"]
                         else "#9CA3AF",
                         width=140, anchor="w"
                         ).pack(side="left", padx=(10, 0))

        # Footer
        foot = ctk.CTkFrame(self._outer, fg_color=SURFACE,
                             border_color=BORDER, border_width=1,
                             corner_radius=0, height=56)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        ghost_btn(foot, "Cancel", command=self.destroy,
                  width=100).pack(side="left", padx=20, pady=10)
        primary_btn(foot, "Promote →", command=self._show_step2,
                    width=130).pack(side="right", padx=20, pady=10)

    # ── Step 2: Confirm ───────────────────────────────────────
    def _show_step2(self):
        # Build plan
        self._plan = []
        all_classes = get_classes()
        cls_by_label = {}
        for c in all_classes:
            lbl = f"{c['name']} {c['stream']}".strip() \
                if c.get("stream") else c["name"]
            cls_by_label[lbl] = c

        for i, row in enumerate(self._rows):
            if not self._include_vars[i].get():
                continue
            to_label = self._to_class_vars[i].get()
            if to_label == "— (graduate / leave)":
                continue
            to_cls = cls_by_label.get(to_label)
            if not to_cls:
                continue
            if row["students"] == 0:
                continue
            self._plan.append({
                "from_cls":   row["from_cls"],
                "from_label": row["from_label"],
                "to_cls":     to_cls,
                "to_label":   to_label,
                "students":   row["students"],
            })

        if not self._plan:
            from tkinter import messagebox
            messagebox.showwarning(
                "Nothing to promote",
                "No classes selected or no students to move.")
            return

        self._clear()
        f = ctk.CTkFrame(self._outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=24)

        heading(f, "Confirm promotion", size=16
                ).pack(anchor="w", pady=(0, 4))

        total = sum(p["students"] for p in self._plan)
        muted(f, f"{len(self._plan)} class(es) · "
                 f"{total} student(s) will be moved."
              ).pack(anchor="w", pady=(0, 14))

        scroll = ctk.CTkScrollableFrame(
            f, fg_color=SURFACE, border_color=BORDER,
            border_width=1, corner_radius=8, height=300)
        scroll.pack(fill="x", pady=(0, 14))

        for p in self._plan:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=6)
            ctk.CTkLabel(row,
                         text=f"{p['from_label']}  →  {p['to_label']}",
                         font=("", 13), text_color=TEXT,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(row,
                         text=f"{p['students']} student(s)",
                         font=("", 11), text_color=TEXT_MUTED,
                         anchor="e").pack(side="right")
            divider(scroll).pack(fill="x", padx=12)

        warn = ctk.CTkFrame(f, fg_color="#FEF3C7",
                             border_color="#FCD34D", border_width=1,
                             corner_radius=8)
        warn.pack(fill="x")
        ctk.CTkLabel(warn,
                     text="⚠  This action cannot be undone. "
                          "Take a backup first if you haven't already.",
                     font=("", 12), text_color="#92400E",
                     justify="left"
                     ).pack(padx=14, pady=8, anchor="w")

        foot = ctk.CTkFrame(self._outer, fg_color=SURFACE,
                             border_color=BORDER, border_width=1,
                             corner_radius=0, height=56)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        ghost_btn(foot, "← Back", command=self._show_step1,
                  width=100).pack(side="left", padx=20, pady=10)
        ctk.CTkButton(foot, text="Confirm & promote",
                      width=160, height=36,
                      fg_color=SUCCESS, hover_color="#15803D",
                      corner_radius=8, font=("", 13),
                      command=self._execute
                      ).pack(side="right", padx=20, pady=10)

    # ── Execute ───────────────────────────────────────────────
    def _execute(self):
        self._clear()
        f = ctk.CTkFrame(self._outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=24)

        heading(f, "Promoting students…", size=16).pack(
            anchor="w", pady=(0, 20))

        self._prog_bar = ctk.CTkProgressBar(f, width=500)
        self._prog_bar.set(0)
        self._prog_bar.pack(anchor="w", pady=(0, 12))

        self._prog_lbl = muted(f, "Starting…")
        self._prog_lbl.pack(anchor="w")

        self.update()

        results = []
        total   = len(self._plan)
        for i, p in enumerate(self._plan):
            self._prog_lbl.configure(
                text=f"Promoting {p['from_label']} → {p['to_label']}…")
            self._prog_bar.set((i + 0.5) / total)
            self.update()

            ok, msg = bulk_promote(
                p["from_cls"]["id"], p["to_cls"]["id"])
            results.append((p, ok, msg))
            self._prog_bar.set((i + 1) / total)
            self.update()

        # Results
        for w in f.winfo_children():
            w.destroy()

        succeeded = sum(1 for _, ok, _ in results if ok)
        heading(f, f"✓ Done — {succeeded}/{total} class(es) promoted",
                size=16).pack(anchor="w", pady=(0, 14))

        scroll = ctk.CTkScrollableFrame(
            f, fg_color=SURFACE, border_color=BORDER,
            border_width=1, corner_radius=8, height=320)
        scroll.pack(fill="x", pady=(0, 14))

        for p, ok, msg in results:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=6)
            icon  = "✓" if ok else "✗"
            color = SUCCESS if ok else DANGER
            ctk.CTkLabel(row,
                         text=f"{icon}  {p['from_label']} → {p['to_label']}  |  {msg}",
                         font=("", 12), text_color=color,
                         anchor="w").pack(anchor="w")

        foot = ctk.CTkFrame(self._outer, fg_color=SURFACE,
                             border_color=BORDER, border_width=1,
                             corner_radius=0, height=56)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        primary_btn(foot, "Close", command=self._close,
                    width=100).pack(side="right", padx=20, pady=10)

    def _close(self):
        if self._on_done:
            self._on_done()
        self.destroy()
