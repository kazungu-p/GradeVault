import customtkinter as ctk
from utils.theme import *
from utils.session import Session
from routes.assessments import (
    get_assessments, create_assessment, update_assessment, delete_assessment,
    get_enrolled_students, get_all_class_students,
    set_enrollments, is_enrolled, get_marks, save_mark,
)
from routes.classes import get_classes
from routes.settings import get_user_permissions
from db.connection import query


GRADE_COLORS = {
    "A": "#15803D", "A-": "#15803D",
    "B+": "#1D4ED8", "B": "#1D4ED8", "B-": "#1D4ED8",
    "C+": "#92400E", "C": "#92400E", "C-": "#92400E",
    "D+": "#B91C1C", "D": "#B91C1C", "D-": "#B91C1C",
    "E": "#7F1D1D",
}


class MarksPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._assessment  = None
        self._class       = None
        self._subject     = None
        self._out_of      = 100
        self._marks_cache = {}   # student_id → saved mark dict
        self._entries     = {}   # student_id → CTkEntry widget
        self._build()

    # ── Shell ─────────────────────────────────────────────────
    def _build(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)

        heading(self, "Marks entry").pack(anchor="w", pady=(0, 16))

        # Step panels
        self._steps = ctk.CTkFrame(self, fg_color="transparent")
        self._steps.pack(fill="both", expand=True)
        self._steps.columnconfigure(0, weight=1)

        self._show_step1()

    def _clear_steps(self):
        for w in self._steps.winfo_children():
            w.destroy()
        self._entries = {}

    # ── Step 1: Pick assessment ───────────────────────────────
    def _show_step1(self):
        self._clear_steps()
        self._assessment = None
        self._class      = None
        self._subject    = None

        f = ctk.CTkFrame(self._steps, fg_color="transparent")
        f.pack(fill="both", expand=True)

        # Step indicator
        self._step_indicator(f, 1)

        body = ctk.CTkFrame(f, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # Left — existing assessments
        left = card(body)
        left.grid(row=0, column=0, padx=(0, 8), sticky="nsew", pady=(0, 0))

        lf = ctk.CTkFrame(left, fg_color="transparent")
        lf.pack(fill="both", expand=True, padx=16, pady=14)

        label(lf, "Select assessment", size=13,
              weight="bold").pack(anchor="w", pady=(0, 10))

        assessments = get_assessments()

        if not assessments:
            muted(lf, "No assessments yet.\nCreate one →").pack(
                anchor="w", pady=20)
        else:
            scroll = ctk.CTkScrollableFrame(
                lf, fg_color="transparent", height=300)
            scroll.pack(fill="both", expand=True)

            for a in assessments:
                row = ctk.CTkFrame(scroll, fg_color=SURFACE,
                                   border_color=BORDER, border_width=1,
                                   corner_radius=8)
                row.pack(fill="x", pady=4)

                info = ctk.CTkFrame(row, fg_color="transparent")
                info.pack(side="left", fill="x", expand=True,
                          padx=12, pady=10)

                ctk.CTkLabel(info, text=a["name"],
                             font=("", 13, "bold"),
                             text_color=TEXT, anchor="w").pack(anchor="w")
                ctk.CTkLabel(
                    info,
                    text=f"{a['type']}  ·  Out of {a['out_of']}"
                         f"  ·  Term {a['term_number']}, {a['year']}",
                    font=("", 11), text_color=TEXT_MUTED,
                    anchor="w").pack(anchor="w")

                btn_col = ctk.CTkFrame(row, fg_color="transparent")
                btn_col.pack(side="right", padx=8)

                primary_btn(btn_col, "Select →",
                            command=lambda ax=a: self._on_assessment(ax),
                            width=90).pack(pady=8)

        # Right — create new (only for users with manage_exams permission)
        user = Session.get()
        can_create = (user["role"] == "admin" or
                      "manage_exams" in user.get("perms", []))
        right = card(body)
        if can_create:
            right.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        else:
            right.grid_forget()

        rf = ctk.CTkFrame(right, fg_color="transparent")
        rf.pack(fill="both", expand=True, padx=16, pady=14)

        label(rf, "Create new assessment", size=13,
              weight="bold").pack(anchor="w", pady=(0, 12))

        muted(rf, "Name *").pack(anchor="w")
        self._aname = ctk.CTkEntry(rf, width=280,
                                    fg_color=SURFACE, border_color=BORDER,
                                    placeholder_text="e.g. Midterm 1 Exam")
        self._aname.pack(anchor="w", pady=(4, 12))

        muted(rf, "Type *").pack(anchor="w")
        self._atype = ctk.StringVar(value="Exam")
        ctk.CTkOptionMenu(rf, variable=self._atype,
                          values=["Exam", "CAT", "Assignment"],
                          width=280, fg_color=SURFACE,
                          button_color=BORDER, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          ).pack(anchor="w", pady=(4, 12))

        muted(rf, "Default marks out of").pack(anchor="w")
        self._aoutof = ctk.CTkEntry(rf, width=280,
                                     fg_color=SURFACE, border_color=BORDER)
        self._aoutof.insert(0, "100")
        self._aoutof.pack(anchor="w", pady=(4, 14))

        self._aerr = ctk.CTkLabel(rf, text="",
                                   text_color=DANGER, font=("", 12))
        self._aerr.pack(anchor="w")

        primary_btn(rf, "Create assessment",
                    command=self._create_assessment, width=200).pack(
            anchor="w", pady=(8, 0))

    def _create_assessment(self):
        self._aerr.configure(text="")
        name = self._aname.get().strip()
        try:
            out_of = int(self._aoutof.get().strip())
            assert out_of > 0
        except Exception:
            self._aerr.configure(text="Enter a valid number for marks out of.")
            return
        ok, msg = create_assessment(name, self._atype.get(), out_of)
        if ok:
            self._show_step1()
        else:
            self._aerr.configure(text=msg)

    def _on_assessment(self, assessment):
        self._assessment = assessment
        self._out_of     = assessment["out_of"]
        self._show_step2()

    # ── Step 2: Pick class + subject ──────────────────────────
    def _show_step2(self):
        self._clear_steps()

        f = ctk.CTkFrame(self._steps, fg_color="transparent")
        f.pack(fill="both", expand=True)

        self._step_indicator(f, 2)

        # Breadcrumb
        self._breadcrumb(f, self._assessment["name"])

        body = card(f)
        body.pack(fill="x", pady=(0, 12))
        bf = ctk.CTkFrame(body, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=14)

        label(bf, "Select class and subject", size=13,
              weight="bold").pack(anchor="w", pady=(0, 12))

        row1 = ctk.CTkFrame(bf, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 12))

        # Class — filtered by teacher assignments if teacher
        user    = Session.get()
        classes = self._get_allowed_classes(user)

        muted(row1, "Class").pack(anchor="w")
        class_labels = [
            f"{c['name']}{' ' + c['stream'] if c.get('stream') else ''}"
            for c in classes
        ]
        self._cls_var = ctk.StringVar(
            value=class_labels[0] if class_labels else "")
        ctk.CTkOptionMenu(row1, variable=self._cls_var,
                          values=class_labels if class_labels else ["—"],
                          width=240, fg_color=SURFACE,
                          button_color=BORDER, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          command=lambda _: self._update_subject_menu(
                              classes, user)
                          ).pack(anchor="w", pady=(4, 0))

        muted(row1, "Subject").pack(anchor="w", pady=(12, 0))
        self._subj_var = ctk.StringVar(value="")
        self._subj_menu = ctk.CTkOptionMenu(
            row1, variable=self._subj_var,
            values=["—"], width=240,
            fg_color=SURFACE, button_color=BORDER,
            text_color=TEXT, dropdown_fg_color=SURFACE)
        self._subj_menu.pack(anchor="w", pady=(4, 0))

        self._classes_list = classes
        self._update_subject_menu(classes, user)

        btn_row = ctk.CTkFrame(bf, fg_color="transparent")
        btn_row.pack(fill="x", pady=(16, 0))

        ghost_btn(btn_row, "← Back",
                  command=self._show_step1, width=100).pack(side="left")

        primary_btn(btn_row, "Enter marks →",
                    command=lambda: self._on_class_subject(classes, user),
                    width=140).pack(side="right")

    def _get_allowed_classes(self, user) -> list:
        all_classes = get_classes()
        if user["role"] == "admin":
            return all_classes
        # Teacher — only assigned classes
        assigned = query(
            "SELECT DISTINCT class_id FROM teacher_assignments WHERE user_id=?",
            (user["id"],)
        )
        allowed_ids = {r["class_id"] for r in assigned}
        return [c for c in all_classes if c["id"] in allowed_ids]

    def _update_subject_menu(self, classes, user):
        cls_label = self._cls_var.get()
        cls = next(
            (c for c in classes
             if f"{c['name']}{' ' + c['stream'] if c.get('stream') else ''}"
             == cls_label),
            None,
        )
        if not cls:
            self._subj_menu.configure(values=["—"])
            return

        if user["role"] == "admin":
            subjects = query(
                "SELECT s.id, s.name FROM subjects s "
                "WHERE s.is_active=1 ORDER BY s.name")
        else:
            subjects = query(
                "SELECT s.id, s.name FROM teacher_assignments ta "
                "JOIN subjects s ON ta.subject_id=s.id "
                "WHERE ta.user_id=? AND ta.class_id=? "
                "ORDER BY s.name",
                (user["id"], cls["id"]),
            )

        self._subjects_for_class = subjects
        labels = [s["name"] for s in subjects]
        self._subj_menu.configure(values=labels if labels else ["—"])
        if labels:
            self._subj_var.set(labels[0])

    def _on_class_subject(self, classes, user):
        cls_label  = self._cls_var.get()
        subj_label = self._subj_var.get()

        cls = next(
            (c for c in classes
             if f"{c['name']}{' ' + c['stream'] if c.get('stream') else ''}"
             == cls_label),
            None,
        )
        subj = next(
            (s for s in getattr(self, "_subjects_for_class", [])
             if s["name"] == subj_label),
            None,
        )
        if not cls or not subj:
            return

        self._class   = cls
        self._subject = subj
        self._show_step3()

    # ── Step 3: Marks grid ────────────────────────────────────
    def _show_step3(self):
        self._clear_steps()

        cls  = self._class
        subj = self._subject
        asmt = self._assessment

        f = ctk.CTkFrame(self._steps, fg_color="transparent")
        f.pack(fill="both", expand=True)

        self._step_indicator(f, 3)

        cls_label = f"{cls['name']}{' ' + cls['stream'] if cls.get('stream') else ''}"
        self._breadcrumb(f, f"{asmt['name']}  →  {cls_label}  →  {subj['name']}")

        # Check enrollment — if none saved yet, auto-enroll all
        if not is_enrolled(subj["id"], cls["id"]):
            all_students = get_all_class_students(cls["id"])
            set_enrollments(subj["id"], cls["id"],
                            [s["id"] for s in all_students])

        enrolled = get_enrolled_students(subj["id"], cls["id"])
        self._marks_cache = get_marks(asmt["id"], subj["id"], cls["id"])

        # Top bar
        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))

        # Out of field
        outof_frame = ctk.CTkFrame(top, fg_color=SURFACE,
                                    border_color=BORDER, border_width=1,
                                    corner_radius=8)
        outof_frame.pack(side="left")
        ctk.CTkLabel(outof_frame, text="Marks out of:",
                     font=("", 12), text_color=TEXT_MUTED
                     ).pack(side="left", padx=(10, 4), pady=6)
        self._outof_var = ctk.StringVar(value=str(self._out_of))
        outof_entry = ctk.CTkEntry(
            outof_frame, textvariable=self._outof_var,
            width=60, fg_color=SURFACE, border_width=0,
            font=("", 13, "bold"))
        outof_entry.pack(side="left", padx=(0, 10))
        outof_entry.bind("<FocusOut>", self._on_outof_change)
        outof_entry.bind("<Return>",   self._on_outof_change)

        # Student count
        muted(top, f"{len(enrolled)} student(s)").pack(
            side="left", padx=12)

        # Manage enrollment button
        ghost_btn(top, "Manage enrollment",
                  command=self._open_enrollment, width=150
                  ).pack(side="left", padx=(0, 8))

        # Save all + back
        primary_btn(top, "Save all",
                    command=self._save_all, width=100
                    ).pack(side="right")
        self._save_status = ctk.CTkLabel(
            top, text="", font=("", 11), text_color=SUCCESS)
        self._save_status.pack(side="right", padx=8)
        ghost_btn(top, "← Back",
                  command=self._show_step2, width=80
                  ).pack(side="right", padx=(0, 8))

        # Grid
        tcard = card(f)
        tcard.pack(fill="both", expand=True)

        # Header
        thead = ctk.CTkFrame(tcard, fg_color="#F3F4F6", corner_radius=0)
        thead.pack(fill="x", padx=1, pady=(1, 0))
        for txt, w in [("#", 36), ("Adm. No.", 120),
                        ("Full name", 260), ("Score", 100),
                        ("/ Max", 60), ("%", 70)]:
            ctk.CTkLabel(thead, text=txt, font=("", 11, "bold"),
                         text_color=TEXT_MUTED, width=w,
                         anchor="w").pack(side="left", padx=(8, 0), pady=8)

        # Rows
        body = ctk.CTkScrollableFrame(tcard, fg_color=SURFACE,
                                       corner_radius=0)
        body.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        self._grid_body = body

        self._enrolled  = enrolled
        self._render_grid()

    def _render_grid(self):
        for w in self._grid_body.winfo_children():
            w.destroy()
        self._entries = {}

        for i, s in enumerate(self._enrolled):
            bg = SURFACE if i % 2 == 0 else "#FAFAFA"
            row = ctk.CTkFrame(self._grid_body, fg_color=bg,
                               corner_radius=0, height=38)
            row.pack(fill="x")
            row.pack_propagate(False)

            saved = self._marks_cache.get(s["id"], {})

            def _lbl(txt, w, color=TEXT_MUTED):
                ctk.CTkLabel(row, text=str(txt), font=("", 12),
                             text_color=color, width=w,
                             anchor="w").pack(side="left", padx=(8, 0))

            _lbl(i + 1, 36)
            _lbl(s["admission_number"], 120, TEXT)
            ctk.CTkLabel(row, text=s["full_name"], font=("", 12),
                         text_color=TEXT, width=260,
                         anchor="w").pack(side="left", padx=(8, 0))

            # Score entry
            score_var = ctk.StringVar(
                value=str(saved["raw_score"])
                if saved.get("raw_score") is not None else "")
            entry = ctk.CTkEntry(
                row, textvariable=score_var,
                width=90, height=28, border_color=BORDER,
                fg_color=SURFACE, font=("", 12))
            entry.pack(side="left", padx=(8, 0))
            self._entries[s["id"]] = (entry, score_var)

            _lbl(self._out_of, 60)

            # Percentage and grade labels (updated on save)
            pct_var = ctk.StringVar(
                value=f"{saved['percentage']:.1f}%"
                if saved.get("percentage") is not None else "—")

            pct_lbl = ctk.CTkLabel(row, textvariable=pct_var,
                                    font=("", 12), text_color=TEXT_MUTED,
                                    width=70, anchor="w")
            pct_lbl.pack(side="left", padx=(8, 0))

            # Auto-save on focus out
            def _auto_save(event, sid=s["id"],
                           sv=score_var, pl=pct_lbl, pv=pct_var):
                self._save_one(sid, sv, pv, pl)

            entry.bind("<FocusOut>", _auto_save)
            entry.bind("<Return>",   _auto_save)
            entry.bind("<Tab>",      _auto_save)

        # Keyboard navigation — focus first empty entry
        for sid, (entry, _) in self._entries.items():
            if not entry.get():
                entry.focus()
                break

    def _on_outof_change(self, event=None):
        try:
            val = float(self._outof_var.get().strip())
            assert val > 0
            self._out_of = val
            self._render_grid()
        except Exception:
            self._outof_var.set(str(self._out_of))

    def _save_one(self, student_id, score_var, pct_var, pct_lbl):
        raw = score_var.get().strip()
        if not raw:
            return
        try:
            score = float(raw)
        except ValueError:
            score_var.set("")
            return

        ok, result = save_mark(
            self._assessment["id"], self._subject["id"],
            self._class["id"], student_id,
            score, self._out_of,
        )
        if ok:
            pct = round((score / self._out_of) * 100, 1)
            pct_var.set(f"{pct:.1f}%")
            pct_lbl.configure(text_color=SUCCESS)
            # Update cache
            self._marks_cache[student_id] = {
                "raw_score": score, "out_of": self._out_of,
                "percentage": pct, "grade": result,
            }
        else:
            score_var.set("")

    def _save_all(self):
        saved = 0
        for sid, (entry, sv) in self._entries.items():
            raw = sv.get().strip()
            if not raw:
                continue
            try:
                score = float(raw)
            except ValueError:
                continue
            ok, _ = save_mark(
                self._assessment["id"], self._subject["id"],
                self._class["id"], sid, score, self._out_of,
            )
            if ok:
                saved += 1
        self._save_status.configure(
            text=f"✓ {saved} mark(s) saved")
        self.after(3000, lambda: self._save_status.configure(text=""))
        # Refresh cache
        self._marks_cache = get_marks(
            self._assessment["id"], self._subject["id"], self._class["id"])
        self._render_grid()

    def _open_enrollment(self):
        EnrollmentDialog(
            self,
            subject=self._subject,
            cls=self._class,
            on_done=self._refresh_enrollment,
        )

    def _refresh_enrollment(self):
        self._enrolled    = get_enrolled_students(
            self._subject["id"], self._class["id"])
        self._marks_cache = get_marks(
            self._assessment["id"], self._subject["id"], self._class["id"])
        self._render_grid()

    # ── Helpers ───────────────────────────────────────────────
    def _step_indicator(self, parent, current):
        steps = ["Assessment", "Class & subject", "Enter marks"]
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(anchor="w", pady=(0, 16))
        for i, name in enumerate(steps, 1):
            is_done    = i < current
            is_current = i == current
            color = ACCENT if is_current else (SUCCESS if is_done else TEXT_MUTED)
            txt   = f"✓ {name}" if is_done else f"{i}. {name}"
            ctk.CTkLabel(row, text=txt, font=("", 12,
                         "bold" if is_current else "normal"),
                         text_color=color).pack(side="left")
            if i < len(steps):
                ctk.CTkLabel(row, text="  →  ",
                             font=("", 12), text_color=TEXT_MUTED
                             ).pack(side="left")

    def _breadcrumb(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("", 12),
                     text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 10))


# ── Enrollment dialog ─────────────────────────────────────────
class EnrollmentDialog(ctk.CTkToplevel):
    def __init__(self, parent, subject, cls, on_done):
        super().__init__(parent)
        cls_label = f"{cls['name']}{' ' + cls['stream'] if cls.get('stream') else ''}"
        self.title(f"Enrollment — {subject['name']} / {cls_label}")
        self.geometry("480x520")
        self.resizable(False, False)
        self.grab_set()
        self._subject = subject
        self._cls     = cls
        self._on_done = on_done
        self._vars    = {}
        self._build()

    def _build(self):
        f = ctk.CTkFrame(self, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=28)

        cls_label = f"{self._cls['name']}{' ' + self._cls['stream'] if self._cls.get('stream') else ''}"
        heading(f, f"Who takes {self._subject['name']}?",
                size=15).pack(anchor="w", pady=(0, 4))
        muted(f, f"Class: {cls_label}  —  tick the students enrolled in this subject."
              ).pack(anchor="w", pady=(0, 12))

        # Select all toggle
        ctrl = ctk.CTkFrame(f, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 8))
        ghost_btn(ctrl, "Select all",
                  command=self._select_all, width=100).pack(side="left")
        ghost_btn(ctrl, "Clear all",
                  command=self._clear_all, width=100).pack(
            side="left", padx=(8, 0))
        self._count_lbl = muted(ctrl, "")
        self._count_lbl.pack(side="right")

        # Student checklist
        scroll = ctk.CTkScrollableFrame(
            f, fg_color=SURFACE,
            border_color=BORDER, border_width=1,
            corner_radius=8, height=280)
        scroll.pack(fill="x", pady=(0, 14))

        all_students  = get_all_class_students(self._cls["id"])
        enrolled_ids  = {s["id"] for s in
                         get_enrolled_students(self._subject["id"],
                                               self._cls["id"])}

        for s in all_students:
            var = ctk.BooleanVar(value=(s["id"] in enrolled_ids))
            self._vars[s["id"]] = var
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkCheckBox(
                row,
                text=f"{s['full_name']}  ({s['admission_number']})",
                variable=var,
                font=("", 12), text_color=TEXT,
                fg_color=ACCENT, hover_color=ACCENT_DARK,
                command=self._update_count,
            ).pack(anchor="w", padx=8)

        self._update_count()

        self._msg = ctk.CTkLabel(f, text="", font=("", 12),
                                  text_color=SUCCESS)
        self._msg.pack(anchor="w")

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x", pady=(8, 0))
        ghost_btn(btn_row, "Cancel", command=self.destroy,
                  width=100).pack(side="left")
        primary_btn(btn_row, "Save enrollment",
                    command=self._save, width=140).pack(side="right")

    def _update_count(self):
        n = sum(1 for v in self._vars.values() if v.get())
        self._count_lbl.configure(text=f"{n} selected")

    def _select_all(self):
        for v in self._vars.values():
            v.set(True)
        self._update_count()

    def _clear_all(self):
        for v in self._vars.values():
            v.set(False)
        self._update_count()

    def _save(self):
        selected = [sid for sid, v in self._vars.items() if v.get()]
        set_enrollments(self._subject["id"], self._cls["id"], selected)
        self._msg.configure(text=f"✓ {len(selected)} student(s) enrolled.")
        self.after(1200, lambda: [self.destroy(), self._on_done()])
