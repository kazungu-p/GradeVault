import customtkinter as ctk
import os
from tkinter import filedialog
from utils.theme import *
from routes.terms import get_all_terms, get_current_term
from routes.assessments import get_assessments
from routes.classes import get_classes
from routes.settings import get_setting, set_setting
from utils.grading import detect_curriculum
from db.connection import query

DEFAULT_COMMENTS = {
    "principal_excellent": (
        "It is with great pleasure that I commend this student for their outstanding "
        "academic performance this term. They have demonstrated exceptional dedication, "
        "intellectual curiosity and a strong work ethic. I encourage them to maintain "
        "this excellent standard and continue to inspire their peers."
    ),
    "principal_good": (
        "This student has performed commendably this term and shown a good "
        "understanding of the curriculum. With continued effort and focus, "
        "I am confident they can achieve even greater results. I encourage "
        "them to keep working hard and seek help where needed."
    ),
    "principal_average": (
        "This student has shown satisfactory progress this term. However, there "
        "is clear room for improvement in several areas. I encourage the student "
        "to put in more consistent effort, attend all lessons and make use of "
        "available academic support resources."
    ),
    "principal_below_average": (
        "This student's performance this term is a cause for concern. I urge "
        "them to take their studies more seriously and seek extra tuition where "
        "necessary. Parents and guardians are encouraged to provide additional "
        "support at home. We believe in the student's potential to improve."
    ),
    "teacher_excellent": (
        "An outstanding student who consistently performs at the highest level. "
        "Shows excellent understanding, participates actively and is a role model "
        "to classmates. Keep up this remarkable performance."
    ),
    "teacher_good": (
        "A good student who demonstrates solid understanding of the subject matter. "
        "Participates well in class and shows consistent effort. "
        "Continue working hard to reach even greater heights."
    ),
    "teacher_average": (
        "Shows average performance with room for improvement. The student should "
        "revise more regularly, complete all assignments on time and participate "
        "more actively in class discussions."
    ),
    "teacher_below_average": (
        "Performance this term has been below expectations. The student needs to "
        "put in significantly more effort, attend remedial sessions and seek "
        "clarification on areas of difficulty without delay."
    ),
}

BANDS = [
    ("excellent",     "Excellent  (mean ≥ 70%)"),
    ("good",          "Good  (mean 55–69%)"),
    ("average",       "Average  (mean 40–54%)"),
    ("below_average", "Below average  (mean < 40%)"),
]

KCSE_DEFAULT = [
    ("A",  80, 100, 12),
    ("A-", 75, 79,  11),
    ("B+", 70, 74,  10),
    ("B",  65, 69,   9),
    ("B-", 60, 64,   8),
    ("C+", 55, 59,   7),
    ("C",  50, 54,   6),
    ("C-", 45, 49,   5),
    ("D+", 40, 44,   4),
    ("D",  35, 39,   3),
    ("D-", 30, 34,   2),
    ("E",   0, 29,   1),
]

CBE_DEFAULT = [
    ("EE2", 90, 100, 4),
    ("EE1", 75,  89, 4),
    ("ME2", 65,  74, 3),
    ("ME1", 50,  64, 3),
    ("AE2", 35,  49, 2),
    ("AE1", 25,  34, 2),
    ("BE2", 10,  24, 1),
    ("BE1",  0,   9, 1),
]


class ReportsPage(ctk.CTkFrame):
    # Class-level persistent store shared across all ReportsPage instances
    _report_index: dict = {}   # key → {path, count, class_label, asmt_name}
    _REPORTS_DIR = None

    @classmethod
    def _get_reports_dir(cls):
        from pathlib import Path
        if cls._REPORTS_DIR is None:
            d = Path.home() / ".gradevault" / "reports"
            d.mkdir(parents=True, exist_ok=True)
            cls._REPORTS_DIR = d
        return cls._REPORTS_DIR

    @classmethod
    def _load_index(cls):
        import json
        from pathlib import Path
        idx_path = cls._get_reports_dir() / "index.json"
        if idx_path.exists():
            try:
                raw = json.loads(idx_path.read_text())
                # Restore only entries whose PDF still exists
                cls._report_index = {
                    k: v for k, v in raw.items()
                    if Path(v.get("path", "")).exists()
                }
            except Exception:
                cls._report_index = {}

    @classmethod
    def _save_index(cls):
        import json
        try:
            idx_path = cls._get_reports_dir() / "index.json"
            idx_path.write_text(json.dumps(cls._report_index, indent=2))
        except Exception:
            pass

    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._comments = {}
        # Load persistent index on first use
        if not ReportsPage._report_index:
            ReportsPage._load_index()
        # Instance alias for convenience
        self._last_reports = ReportsPage._report_index
        self._load_saved_comments()
        self._build()

    def _load_saved_comments(self):
        for key, default in DEFAULT_COMMENTS.items():
            saved = get_setting(f"comment_{key}", "")
            self._comments[key] = saved if saved else default

    def _build(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)
        heading(self, "Reports").pack(anchor="w", pady=(0, 14))

        # Tab bar
        self._active_tab = "generate"
        tabs = ctk.CTkFrame(self, fg_color="transparent")
        tabs.pack(fill="x", pady=(0, 14))
        self._tab_btns = {}
        for key, lbl in [("generate", "Generate reports"),
                          ("comments", "Comment templates"),
                          ("grading",  "Grading scales")]:
            btn = ctk.CTkButton(
                tabs, text=lbl, width=160, height=30,
                fg_color=ACCENT if key == "generate" else "transparent",
                text_color="white" if key == "generate" else TEXT_MUTED,
                hover_color=ACCENT_BG, corner_radius=6, font=("", 12),
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", padx=(0, 6))
            self._tab_btns[key] = btn

        self._content_area = ctk.CTkFrame(self, fg_color="transparent")
        self._content_area.pack(fill="both", expand=True)

        self._frames = {}
        for key in ("generate", "comments", "grading"):
            f = ctk.CTkFrame(self._content_area, fg_color="transparent")
            self._frames[key] = f
            f.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._build_generate(self._frames["generate"])
        self._build_comments(self._frames["comments"])
        self._build_grading(self._frames["grading"])
        self._switch_tab("generate")
        # Bind scroll after frames are built
        self.after(100, lambda: self._bind_tab_scroll("generate"))

    def _switch_tab(self, key):
        self._active_tab = key
        # Raise selected frame to top — no rebuild, no flash
        for k, f in self._frames.items():
            if k == key:
                f.lift()
            else:
                f.lower()
        for k, btn in self._tab_btns.items():
            btn.configure(
                fg_color=ACCENT if k == key else "transparent",
                text_color="white" if k == key else TEXT_MUTED)
        # Bind keyboard scroll to the active tab's scrollable frame
        self._bind_tab_scroll(key)

    def _bind_tab_scroll(self, key):
        """Find the CTkScrollableFrame in the active tab and bind arrow keys."""
        import customtkinter as _ctk
        frame = self._frames.get(key)
        if not frame:
            return
        # Find first CTkScrollableFrame child
        sf = None
        for child in frame.winfo_children():
            if isinstance(child, _ctk.CTkScrollableFrame):
                sf = child
                break
        if not sf:
            return
        canvas = getattr(sf, "_parent_canvas", None)
        if not canvas:
            return
        def _scroll(event):
            if event.keysym in ("Down",):
                canvas.yview_scroll(3, "units")
            elif event.keysym in ("Up",):
                canvas.yview_scroll(-3, "units")
            elif event.keysym == "Next":
                canvas.yview_scroll(1, "pages")
            elif event.keysym == "Prior":
                canvas.yview_scroll(-1, "pages")
            elif event.keysym == "End":
                canvas.yview_moveto(1.0)
            elif event.keysym == "Home":
                canvas.yview_moveto(0.0)
        for seq in ("<Down>","<Up>","<Next>","<Prior>","<End>","<Home>"):
            self.winfo_toplevel().bind(seq, _scroll, add="+")

    # ── Generate tab ──────────────────────────────────────────
    def _build_generate(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        s1 = self._section(scroll, "Select term, assessment and class")
        f1 = ctk.CTkFrame(s1, fg_color="transparent")
        f1.pack(fill="x", padx=16, pady=(0, 16))

        muted(f1, "Term").pack(anchor="w")
        self._terms_data = get_all_terms()
        term_labels = [f"Term {t['term']}, {t['year']}" for t in self._terms_data]
        current     = get_current_term()
        default_t   = (f"Term {current['term']}, {current['year']}"
                       if current and term_labels else
                       (term_labels[0] if term_labels else "—"))
        self._term_var = ctk.StringVar(value=default_t)
        ctk.CTkOptionMenu(f1, variable=self._term_var,
                          values=term_labels if term_labels else ["—"],
                          width=320, fg_color=SURFACE,
                          button_color=BORDER, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          command=self._on_term_change,
                          ).pack(anchor="w", pady=(4, 12))

        muted(f1, "Assessment").pack(anchor="w")
        self._asmt_var  = ctk.StringVar(value="—")
        self._asmt_data = []
        self._asmt_menu = ctk.CTkOptionMenu(
            f1, variable=self._asmt_var, values=["—"],
            width=320, fg_color=SURFACE, button_color=BORDER,
            text_color=TEXT, dropdown_fg_color=SURFACE)
        self._asmt_menu.pack(anchor="w", pady=(4, 12))
        self._on_term_change()

        muted(f1, "Class").pack(anchor="w")
        self._classes_data = get_classes()
        class_labels = ["— All classes (merged PDF)"] + [
            f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
            for c in self._classes_data
        ]
        self._class_var = ctk.StringVar(
            value=class_labels[0] if class_labels else "—")
        ctk.CTkOptionMenu(f1, variable=self._class_var,
                          values=class_labels if class_labels else ["—"],
                          width=320, fg_color=SURFACE,
                          button_color=BORDER, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          command=self._on_class_change,
                          ).pack(anchor="w", pady=(4, 0))

        self._curr_label = muted(f1, "")
        self._curr_label.pack(anchor="w", pady=(4, 0))
        self._on_class_change()

        # ── Combined assessments ─────────────────────────────
        s_comb = self._section(scroll, "Combined assessment report (optional)")
        f_comb = ctk.CTkFrame(s_comb, fg_color="transparent")
        f_comb.pack(fill="x", padx=16, pady=(0, 16))

        muted(f_comb,
              "Select multiple assessments (e.g. Opener + Midterm + Endterm) to generate\n"
              "a combined report card where each subject shows the mean across all selected exams."
              ).pack(anchor="w", pady=(0, 10))

        add_row = ctk.CTkFrame(f_comb, fg_color="transparent")
        add_row.pack(fill="x", pady=(0, 6))
        muted(add_row, "Add:").pack(side="left", padx=(0, 6))
        self._comb_add_var = ctk.StringVar(value="— select assessment —")
        all_asmt_labels = [a["name"] for a in get_assessments()]
        self._comb_add_menu = ctk.CTkOptionMenu(
            add_row, variable=self._comb_add_var,
            values=["— select assessment —"] + all_asmt_labels,
            width=260, fg_color=SURFACE, button_color=BORDER,
            text_color=TEXT, dropdown_fg_color=SURFACE,
            command=self._on_comb_add)
        self._comb_add_menu.pack(side="left", padx=(0, 8))
        ghost_btn(add_row, "Clear all",
                  command=self._on_comb_clear, width=80).pack(side="left")

        self._comb_selected: list = []  # list of (id, name)
        self._comb_lbl = muted(f_comb,
                                "No assessments added — will use single assessment above.")
        self._comb_lbl.pack(anchor="w", pady=(0, 4))

        s2 = self._section(scroll, "Generate")
        f2 = ctk.CTkFrame(s2, fg_color="transparent")
        f2.pack(fill="x", padx=16, pady=(0, 16))

        self._gen_desc = muted(f2,
              "Clicking Generate will process all students in the selected class,\n"
              "apply the best-7 rule, compute grades and open a preview window.")
        self._gen_desc.pack(anchor="w", pady=(0, 12))

        self._gen_status = ctk.CTkLabel(
            f2, text="", font=("", 12), text_color=TEXT_MUTED)
        self._gen_status.pack(anchor="w", pady=(0, 8))

        btn_row_gen = ctk.CTkFrame(f2, fg_color="transparent")
        btn_row_gen.pack(anchor="w", fill="x")
        self._gen_btn = primary_btn(btn_row_gen, "Generate & preview →",
                    command=self._generate, width=200)
        self._gen_btn.pack(side="left", padx=(0, 12))
        self._view_btn = ghost_btn(btn_row_gen, "View last report",
                                    command=self._view_last, width=150)
        self._view_btn.pack(side="left")
        self._view_btn.configure(state="disabled")

        # Last-report info label
        self._last_info = muted(f2, "")
        self._last_info.pack(anchor="w", pady=(6, 0))

        # Restore last key from persistent index (most recent entry)
        if self._last_reports:
            from pathlib import Path
            valid = {k: v for k, v in self._last_reports.items()
                     if Path(v.get("path", "")).exists()}
            if valid:
                # Pick the entry matching current selection if possible,
                # otherwise show the most recent valid one
                self._last_key = next(iter(valid))
                info = valid[self._last_key]
                self._view_btn.configure(state="normal")
                self._last_info.configure(
                    text=f"Last: {info['class_label']}  ·  {info['asmt_name']}  ·  {info['count']} card(s)",
                    text_color=ACCENT)

    def _on_comb_add(self, name):
        if name == "— select assessment —":
            return
        all_asmts = get_assessments()
        asmt = next((a for a in all_asmts if a["name"] == name), None)
        if not asmt:
            return
        if asmt["id"] not in [x[0] for x in self._comb_selected]:
            self._comb_selected.append((asmt["id"], asmt["name"]))
        self._comb_add_var.set("— select assessment —")
        self._comb_lbl.configure(
            text="Combined: " + " + ".join(n for _, n in self._comb_selected),
            text_color=ACCENT)

    def _on_comb_clear(self):
        self._comb_selected = []
        self._comb_lbl.configure(
            text="No assessments added — will use single assessment above.",
            text_color=TEXT_MUTED)

    def _on_term_change(self, _=None):
        t_label = self._term_var.get()
        term = next((t for t in self._terms_data
                     if f"Term {t['term']}, {t['year']}" == t_label), None)
        if not term:
            return
        asmts = get_assessments(term_id=term["id"])
        self._asmt_data = asmts
        labels = [a["name"] for a in asmts]
        self._asmt_menu.configure(values=labels if labels else ["—"])
        self._asmt_var.set(labels[0] if labels else "—")
        # Populate combined assessment menu with ALL assessments
        all_labels = [a["name"] for a in get_assessments()]
        try:
            self._comb_add_menu.configure(
                values=["— select assessment —"] + all_labels)
        except Exception:
            pass
        self._refresh_view_btn()

    def _on_class_change(self, _=None):
        cls_label = self._class_var.get()
        if cls_label == "— All classes (merged PDF)":
            self._curr_label.configure(
                text=f"Will generate cards for all {len(self._classes_data)} class(es) in one PDF.",
                text_color=TEXT_MUTED)
            try:
                self._gen_desc.configure(
                    text="Clicking Generate will process ALL classes, apply the best-7 rule\n"
                         "and produce one merged PDF — one student per page.")
            except Exception:
                pass
            self._refresh_view_btn()
            return
        try:
            self._gen_desc.configure(
                text="Clicking Generate will process all students in the selected class,\n"
                     "apply the best-7 rule, compute grades and open a preview window.")
        except Exception:
            pass
        cls = next((c for c in self._classes_data
                    if f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
                    == cls_label), None)
        if cls:
            curr = detect_curriculum(cls["name"])
            friendly = {
                "ECDE":          "ECDE / Pre-Primary (CBC)",
                "Lower Primary": "Lower Primary (CBC)",
                "Upper Primary": "Upper Primary (CBC)",
                "CBC":           "CBC — Senior/Junior Secondary (Grade 7–12)",
                "8-4-4":         "8-4-4 (KCSE)",
            }.get(curr, curr)
            self._curr_label.configure(
                text=f"Curriculum detected: {friendly}",
                text_color=ACCENT)
        self._refresh_view_btn()

    def _refresh_view_btn(self):
        """Enable / disable 'View last report' based on current selection."""
        try:
            from pathlib import Path
            asmt = next((a for a in self._asmt_data
                         if a["name"] == self._asmt_var.get()), None)
            cls_label = self._class_var.get()

            if cls_label == "— All classes (merged PDF)":
                key = f"ALL_{asmt['id']}" if asmt else None
            else:
                cls = next((c for c in self._classes_data
                            if f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
                            == cls_label), None)
                key = f"{cls['id']}_{asmt['id']}" if (asmt and cls) else None

            if key and key in self._last_reports:
                info = self._last_reports[key]
                if Path(info.get("path", "")).exists():
                    self._view_btn.configure(state="normal")
                    self._last_info.configure(
                        text=f"Last: {info['class_label']}  ·  {info['asmt_name']}  ·  {info['count']} card(s)",
                        text_color=ACCENT)
                    self._last_key = key
                    return
                else:
                    del self._last_reports[key]
                    ReportsPage._save_index()
            self._view_btn.configure(state="disabled")
            self._last_info.configure(text="")
        except Exception:
            pass

    def _generate(self):
        asmt = next((a for a in self._asmt_data
                     if a["name"] == self._asmt_var.get()), None)
        if not asmt:
            self._gen_status.configure(
                text="Please select an assessment.", text_color=DANGER)
            return

        cls_label = self._class_var.get()
        all_classes_mode = (cls_label == "— All classes (merged PDF)")

        comb = getattr(self, "_comb_selected", [])

        if not all_classes_mode:
            # Single class
            cls = next((c for c in self._classes_data
                         if f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
                         == cls_label), None)
            if not cls:
                self._gen_status.configure(
                    text="Please select a class.", text_color=DANGER)
                return
            if comb:
                self._generate_combined_report(cls, cls_label)
            else:
                self._generate_single(asmt, cls, cls_label)
        else:
            if comb:
                self._generate_combined_all(asmt)
            else:
                self._generate_all(asmt)

    def _generate_single(self, asmt, cls, cls_label):
        import threading
        self._gen_status.configure(
            text="Generating… please wait.", text_color=TEXT_MUTED)
        self._gen_btn.configure(state="disabled")
        self.update()

        def _worker():
            try:
                from utils.report_pdf import generate_report_cards
                safe      = cls_label.replace(" ", "_")
                asmt_safe = asmt["name"].replace(" ", "_")
                fname     = f"report_{safe}_{asmt_safe}.pdf"
                tmp_path  = str(ReportsPage._get_reports_dir() / fname)

                count, _ = generate_report_cards(
                    tmp_path, asmt["id"], cls["id"], self._comments)

                def _done():
                    self._gen_btn.configure(
                        state="normal", text="Generate & preview →")
                    if count == 0:
                        self._gen_status.configure(
                            text="No marks found for this class and assessment.",
                            text_color=DANGER)
                        return
                    self._gen_status.configure(
                        text=f"✓ {count} report card(s) ready.",
                        text_color=SUCCESS)
                    key = f"{cls['id']}_{asmt['id']}"
                    self._last_reports[key] = {
                        "path": tmp_path, "count": count,
                        "class_label": cls_label,
                        "asmt_name": asmt["name"],
                    }
                    ReportsPage._save_index()
                    try:
                        self._view_btn.configure(state="normal")
                        self._last_info.configure(
                            text=f"Last: {cls_label}  ·  {asmt['name']}  ·  {count} card(s)",
                            text_color=ACCENT)
                        self._last_key = key
                    except Exception:
                        pass
                    ReportPreviewDialog(self, tmp_path, cls_label,
                                        asmt["name"], count)
                self.after(0, _done)

            except Exception as e:
                self.after(0, lambda err=e: (
                    self._gen_status.configure(
                        text=f"Error: {err}", text_color=DANGER),
                    self._gen_btn.configure(
                        state="normal", text="Generate & preview →"),
                ))

        threading.Thread(target=_worker, daemon=True).start()

    def _generate_all(self, asmt):
        from utils.report_pdf import generate_all_classes_report_cards
        if not self._classes_data:
            self._gen_status.configure(
                text="No classes found.", text_color=DANGER)
            return

        self._gen_status.configure(
            text=f"Generating for all {len(self._classes_data)} class(es)... please wait.",
            text_color=TEXT_MUTED)
        self.update()

        try:
            asmt_safe = asmt["name"].replace(" ", "_")
            fname     = f"report_ALL_{asmt_safe}.pdf"
            tmp_path  = str(ReportsPage._get_reports_dir() / fname)

            class_ids = [c["id"] for c in self._classes_data]
            count, _ = generate_all_classes_report_cards(
                tmp_path, asmt["id"], class_ids, self._comments)

            if count == 0:
                self._gen_status.configure(
                    text="No marks found for any class with this assessment.",
                    text_color=DANGER)
                return

            self._gen_status.configure(
                text=f"✓ {count} report card(s) across all classes.", text_color=SUCCESS)

            key = f"ALL_{asmt['id']}"
            self._last_reports[key] = {
                "path":        tmp_path,
                "count":       count,
                "class_label": "All classes",
                "asmt_name":   asmt["name"],
            }
            ReportsPage._save_index()
            try:
                self._view_btn.configure(state="normal")
                self._last_info.configure(
                    text=f"Last: All classes  ·  {asmt['name']}  ·  {count} card(s)",
                    text_color=ACCENT)
                self._last_key = key
            except Exception:
                pass

            ReportPreviewDialog(self, tmp_path, "All classes",
                                asmt["name"], count)

        except Exception as e:
            self._gen_status.configure(
                text=f"Error: {e}", text_color=DANGER)

    def _generate_combined_report(self, cls, cls_label):
        from utils.report_pdf import generate_combined_report_cards
        comb = self._comb_selected
        ids   = [i for i, _ in comb]
        names = [n for _, n in comb]
        self._gen_status.configure(
            text=f"Generating combined ({' + '.join(names)})... please wait.",
            text_color=TEXT_MUTED)
        self.update()
        try:
            safe      = cls_label.replace(" ", "_")
            ids_str   = "_".join(str(i) for i in ids)
            fname     = f"combined_{safe}_{ids_str}.pdf"
            tmp_path  = str(ReportsPage._get_reports_dir() / fname)

            count, _ = generate_combined_report_cards(
                tmp_path, ids, names, cls["id"], self._comments)

            if count == 0:
                self._gen_status.configure(
                    text="No marks found for the selected assessments and class.",
                    text_color=DANGER)
                return

            lbl = f"{cls_label} — Combined"
            asmt_label = " + ".join(names)
            self._gen_status.configure(
                text=f"✓ {count} combined report card(s) ready.",
                text_color=SUCCESS)

            key = f"COMB_{cls['id']}_{ids_str}"
            self._last_reports[key] = {
                "path":        tmp_path,
                "count":       count,
                "class_label": lbl,
                "asmt_name":   asmt_label,
            }
            ReportsPage._save_index()
            try:
                self._view_btn.configure(state="normal")
                self._last_info.configure(
                    text=f"Last: {lbl}  ·  {asmt_label}  ·  {count} card(s)",
                    text_color=ACCENT)
                self._last_key = key
            except Exception:
                pass

            ReportPreviewDialog(self, tmp_path, lbl, asmt_label, count)

        except Exception as e:
            self._gen_status.configure(
                text=f"Error: {e}", text_color=DANGER)

    def _generate_combined_all(self, asmt):
        """Generate combined report for ALL classes using shared generator."""
        from utils.report_pdf import generate_combined_report_cards
        from reportlab.platypus import SimpleDocTemplate, PageBreak
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm

        comb  = self._comb_selected
        ids   = [i for i, _ in comb]
        names = [n for _, n in comb]

        self._gen_status.configure(
            text=f"Generating combined for all classes ({' + '.join(names)})...",
            text_color=TEXT_MUTED)
        self._gen_btn.configure(state="disabled")
        self.update()

        import threading

        def _worker():
            try:
                fname    = f"combined_ALL_{'_'.join(str(i) for i in ids)}.pdf"
                tmp_path = str(ReportsPage._get_reports_dir() / fname)

                # Generate per-class PDFs and merge
                import tempfile, shutil
                from utils.report_pdf import (_styles_compact,
                    _school_header_compact,
                    _student_header_table, _marks_table, _comment_block,
                    _per_exam_chart, ACCENT, TEXT_MUTED, BORDER_C,
                    get_current_term)
                from reportlab.platypus import (
                    SimpleDocTemplate, PageBreak, KeepTogether,
                    Paragraph, Spacer, HRFlowable, Table, TableStyle)
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.units import cm
                from reportlab.lib.styles import ParagraphStyle
                from reportlab.lib.enums import TA_CENTER
                from utils.grading import compute_class_results_combined

                s = _styles_compact()
                term = get_current_term()
                combined_label = " + ".join(names)
                term_str = f"Term {term['term']}, {term['year']}" if term else ""

                doc = SimpleDocTemplate(
                    tmp_path, pagesize=A4,
                    leftMargin=1.4*cm, rightMargin=1.4*cm,
                    topMargin=1.0*cm, bottomMargin=1.2*cm)

                story = []
                total_count = 0
                first = True

                from db.connection import query as _dbq
                all_cls_info = {r["id"]: r for r in _dbq(
                    "SELECT id, name, stream FROM classes")}

                for cls in self._classes_data:
                    results = compute_class_results_combined(ids, cls["id"])
                    if not results:
                        continue

                    cls_rec = all_cls_info.get(cls["id"], {})
                    cls_lbl = (f"{cls_rec.get('name','')} "
                               f"{cls_rec.get('stream','') or ''}").strip()

                    for result in results:
                        if not first:
                            story.append(PageBreak())
                        first = False

                        band = result["band"]
                        tc   = self._comments.get(f"teacher_{band}", "")
                        pc_c = self._comments.get(f"principal_{band}", "")

                        el = []
                        _school_header_compact(el, s)
                        el.append(HRFlowable(
                            width="100%", thickness=0.8, color=ACCENT,
                            spaceBefore=3, spaceAfter=3))
                        el.append(Paragraph(
                            f"<b>STUDENT REPORT CARD</b> — {term_str}  |  "
                            f"<font color='#4F46E5'>Combined: {combined_label}</font>",
                            ParagraphStyle("ht", fontSize=9,
                                           fontName="Helvetica-Bold",
                                           textColor=TEXT_MUTED,
                                           alignment=TA_CENTER)))
                        el.append(Spacer(1, 0.12*cm))
                        el.append(_student_header_table(
                            result, cls_lbl, term, s,
                            class_total=len(results)))
                        el.append(Spacer(1, 0.12*cm))
                        el.append(_marks_table(result, s))

                        if result.get("is_844"):
                            el.append(Paragraph(
                                "* Best 7 rule — means across all assessments.",
                                s["small"]))
                        elif result.get("is_cbc"):
                            el.append(Paragraph(
                                "EE=Exceeds  ME=Meets  AE=Approaches  BE=Below",
                                s["small"]))

                        el.append(Spacer(1, 0.15*cm))
                        ct = _comment_block("Class Teacher", tc, s)
                        if ct: el.append(ct)
                        pc = _comment_block("Principal", pc_c, s)
                        if pc: el.append(pc)
                        el.append(Spacer(1, 0.15*cm))

                        chart = _per_exam_chart(
                            result["student_id"], ids, names, cls["id"], s)
                        if chart:
                            el.append(Paragraph(
                                "Performance across assessments",
                                ParagraphStyle("cl", fontSize=7,
                                               fontName="Helvetica-Bold",
                                               textColor=ACCENT)))
                            el.append(Spacer(1, 0.04*cm))
                            el.append(chart)
                            el.append(Spacer(1, 0.12*cm))

                        sig = Table([[
                            "Class Teacher: _______________________",
                            "Principal: _______________________",
                            "Date: _______________",
                        ]], colWidths=[6.5*cm, 6*cm, 5.5*cm])
                        sig.setStyle(TableStyle([
                            ("FONTNAME",  (0,0),(-1,-1), "Helvetica"),
                            ("FONTSIZE",  (0,0),(-1,-1), 7.5),
                            ("TEXTCOLOR", (0,0),(-1,-1), TEXT_MUTED),
                        ]))
                        el.append(sig)
                        story.append(KeepTogether(el))
                        total_count += 1

                if total_count == 0:
                    def _no_marks():
                        self._gen_status.configure(
                            text="No marks found for any class.",
                            text_color=DANGER)
                        self._gen_btn.configure(
                            state="normal", text="Generate & preview →")
                    self.after(0, _no_marks)
                    return

                doc.build(story)  # no watermark

                asmt_label = " + ".join(names)
                key = f"COMB_ALL_{'_'.join(str(i) for i in ids)}"

                def _done():
                    self._gen_btn.configure(
                        state="normal", text="Generate & preview →")
                    self._gen_status.configure(
                        text=f"✓ {total_count} combined cards across all classes.",
                        text_color=SUCCESS)
                    self._last_reports[key] = {
                        "path":        tmp_path,
                        "count":       total_count,
                        "class_label": "All classes — Combined",
                        "asmt_name":   asmt_label,
                    }
                    ReportsPage._save_index()
                    try:
                        self._view_btn.configure(state="normal")
                        self._last_info.configure(
                            text=f"Last: All classes  ·  {asmt_label}  ·  {total_count} card(s)",
                            text_color=ACCENT)
                        self._last_key = key
                    except Exception:
                        pass
                    ReportPreviewDialog(self, tmp_path,
                                        "All classes — Combined",
                                        asmt_label, total_count)
                self.after(0, _done)

            except Exception as e:
                import traceback
                err = traceback.format_exc()
                self.after(0, lambda msg=str(e): (
                    self._gen_status.configure(
                        text=f"Error: {msg}", text_color=DANGER),
                    self._gen_btn.configure(
                        state="normal", text="Generate & preview →"),
                ))

        threading.Thread(target=_worker, daemon=True).start()

    def _view_last(self):
        """Re-open the preview for the most recently generated report."""
        from pathlib import Path
        key = getattr(self, "_last_key", None)
        # Try last key, then fall back to any valid stored report
        if not key or key not in self._last_reports:
            valid = {k: v for k, v in self._last_reports.items()
                     if Path(v.get("path", "")).exists()}
            if valid:
                key = next(iter(valid))
            else:
                self._gen_status.configure(
                    text="No report generated yet.", text_color=DANGER)
                return
        info = self._last_reports.get(key)
        if not info or not Path(info["path"]).exists():
            self._gen_status.configure(
                text="Report file no longer exists. Please regenerate.",
                text_color=DANGER)
            return
        ReportPreviewDialog(self, info["path"], info["class_label"],
                            info["asmt_name"], info["count"])

    # ── Comments tab ──────────────────────────────────────────
    def _build_comments(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)
        self._comment_widgets = {}

        for role, role_label in [("principal", "Principal's comments"),
                                  ("teacher",   "Class teacher's comments")]:
            sec = self._section(scroll, role_label)
            sf  = ctk.CTkFrame(sec, fg_color="transparent")
            sf.pack(fill="x", padx=16, pady=(0, 14))

            for band_key, band_label in BANDS:
                full_key = f"{role}_{band_key}"
                muted(sf, band_label).pack(anchor="w", pady=(8, 2))
                box = ctk.CTkTextbox(
                    sf, width=680, height=70,
                    fg_color=SURFACE, border_color=BORDER,
                    font=("", 11))
                box.pack(anchor="w")
                box.insert("1.0", self._comments.get(full_key, ""))
                self._comment_widgets[full_key] = box

        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=16)
        self._save_msg = ctk.CTkLabel(
            btn_row, text="", font=("", 12), text_color=SUCCESS)
        self._save_msg.pack(side="right", padx=(0, 16))
        primary_btn(btn_row, "Save templates",
                    command=self._save_comments, width=160).pack(side="right")

    def _save_comments(self):
        for key, box in self._comment_widgets.items():
            text = box.get("1.0", "end").strip()
            self._comments[key] = text
            set_setting(f"comment_{key}", text)
        self._save_msg.configure(text="✓ Saved.")
        self.after(2000, lambda: self._save_msg.configure(text=""))

    # ── Grading scales tab ────────────────────────────────────
    def _build_grading(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        for curriculum, default_scale in [("8-4-4 (KCSE)", KCSE_DEFAULT),
                                           ("CBE",          CBE_DEFAULT)]:
            sec = self._section(scroll, f"{curriculum} Grading Scale")
            sf  = ctk.CTkFrame(sec, fg_color="transparent")
            sf.pack(fill="x", padx=16, pady=(12, 14))

            # Header
            hdr = ctk.CTkFrame(sf, fg_color="#F3F4F6", corner_radius=6)
            hdr.pack(fill="x", pady=(0, 4))
            for txt, w in [("Grade", 80), ("Min %", 90),
                            ("Max %", 90), ("Points", 80)]:
                ctk.CTkLabel(hdr, text=txt, font=("", 11, "bold"),
                             text_color=TEXT_MUTED, width=w,
                             anchor="w").pack(side="left", padx=(10, 0), pady=6)

            key_prefix = "kcse" if "KCSE" in curriculum else "cbe"
            rows_frame = ctk.CTkFrame(sf, fg_color="transparent")
            rows_frame.pack(fill="x")

            for i, (grade, min_s, max_s, pts) in enumerate(default_scale):
                saved_min = get_setting(f"{key_prefix}_{grade}_min", str(min_s))
                saved_max = get_setting(f"{key_prefix}_{grade}_max", str(max_s))
                saved_pts = get_setting(f"{key_prefix}_{grade}_pts", str(pts))

                row = ctk.CTkFrame(rows_frame,
                                   fg_color=SURFACE if i%2==0 else "#FAFAFA",
                                   corner_radius=0)
                row.pack(fill="x")

                ctk.CTkLabel(row, text=grade, font=("", 12, "bold"),
                             text_color=ACCENT, width=80,
                             anchor="w").pack(side="left", padx=(10, 0), pady=4)

                for val, setting_key in [
                    (saved_min, f"{key_prefix}_{grade}_min"),
                    (saved_max, f"{key_prefix}_{grade}_max"),
                    (saved_pts, f"{key_prefix}_{grade}_pts"),
                ]:
                    e = ctk.CTkEntry(row, width=80, height=28,
                                     fg_color=SURFACE, border_color=BORDER,
                                     font=("", 11))
                    e.insert(0, val)
                    e.pack(side="left", padx=(10, 0))
                    # Save on focus out
                    def _make_saver(sk, ew):
                        def _save(ev=None):
                            set_setting(sk, ew.get().strip())
                            from utils.grading import invalidate_scale_cache
                            invalidate_scale_cache()
                        return _save
                    _sv = _make_saver(setting_key, e)
                    e.bind("<FocusOut>", _sv)
                    e.bind("<Return>",   _sv)

            if key_prefix == "cbe":
                muted(sf, "EE2/EE1 = Exceeds  ·  ME2/ME1 = Meets  ·  AE2/AE1 = Approaches  ·  BE2/BE1 = Below  ·  "
                          "Changes are saved automatically when you click away from each field."
                      ).pack(anchor="w", pady=(8, 0))
            else:
                muted(sf, "Changes are saved automatically when you click away from each field."
                      ).pack(anchor="w", pady=(8, 0))

        # Reset to defaults button
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=16)
        ghost_btn(btn_row, "Reset to defaults",
                  command=self._reset_grading, width=150).pack(side="right")

    def _reset_grading(self):
        from utils.grading import invalidate_scale_cache
        invalidate_scale_cache()
        for grade, min_s, max_s, pts in KCSE_DEFAULT:
            set_setting(f"kcse_{grade}_min", str(min_s))
            set_setting(f"kcse_{grade}_max", str(max_s))
            set_setting(f"kcse_{grade}_pts", str(pts))
        for grade, min_s, max_s, pts in CBE_DEFAULT:
            set_setting(f"cbe_{grade}_min", str(min_s))
            set_setting(f"cbe_{grade}_max", str(max_s))
            set_setting(f"cbe_{grade}_pts", str(pts))
        # Rebuild grading tab
        self._frames["grading"].destroy()
        f = ctk.CTkFrame(self._content_area, fg_color="transparent")
        f.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._frames["grading"] = f
        self._build_grading(f)
        self._switch_tab("grading")

    def _section(self, parent, title):
        c = card(parent)
        c.pack(fill="x", pady=(0, 14))
        hdr = ctk.CTkFrame(c, fg_color=ACCENT_BG, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=title, font=("", 13, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=16, pady=10)
        return c


# ── Report preview dialog ─────────────────────────────────────
class ReportPreviewDialog(ctk.CTkToplevel):
    def __init__(self, parent, pdf_path, class_label, asmt_name, count):
        super().__init__(parent)
        self.title(f"Report cards — {class_label}")
        self.geometry("500x320")
        self.resizable(False, False)
        self.grab_set()
        self._pdf_path  = pdf_path
        self._class_label = class_label
        self._asmt_name = asmt_name
        self._count     = count
        self._build()

    def _build(self):
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(fill="both", expand=True)

        f = ctk.CTkFrame(outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=(24, 0))

        # Success header
        ctk.CTkLabel(f, text="✓", font=("", 36, "bold"),
                     text_color=SUCCESS).pack(pady=(0, 4))
        heading(f, f"{self._count} report card(s) generated",
                size=16).pack()
        muted(f, f"{self._class_label}  ·  {self._asmt_name}"
              ).pack(pady=(2, 16))

        divider(f).pack(fill="x", pady=(0, 12))

        muted(f, "What would you like to do?").pack(anchor="w", pady=(0, 10))

        # Action buttons
        actions = ctk.CTkFrame(f, fg_color="transparent")
        actions.pack(fill="x")

        primary_btn(actions, "Preview PDF",
                    command=self._preview, width=130).pack(
            side="left", padx=(0, 8))
        ghost_btn(actions, "Save PDF",
                  command=self._save_pdf, width=110).pack(
            side="left", padx=(0, 8))

        self._status = ctk.CTkLabel(
            f, text="", font=("", 11), text_color=TEXT_MUTED)
        self._status.pack(anchor="w", pady=(12, 0))

        # Pinned footer
        btn_row = ctk.CTkFrame(outer, fg_color=SURFACE,
                               border_color=BORDER, border_width=1,
                               corner_radius=0, height=56)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)
        ghost_btn(btn_row, "Close", command=self.destroy,
                  width=90).pack(side="left", padx=20, pady=10)
        ghost_btn(btn_row, "Print",
                  command=self._print, width=90).pack(
            side="right", padx=(8, 20), pady=10)

    def _preview(self):
        if os.name == "nt":
            os.startfile(self._pdf_path)
        else:
            os.system(f'open "{self._pdf_path}"')

    def _save_pdf(self):
        safe      = self._class_label.replace(" ", "_").replace("—", "").strip("_")
        asmt_safe = self._asmt_name.replace(" ", "_").replace("/", "-")
        try:
            from routes.terms import get_current_term
            term = get_current_term()
            term_str = f"Term{term['term']}_{term['year']}" if term else ""
        except Exception:
            term_str = ""
        parts = [p for p in [safe, asmt_safe, term_str] if p]
        fname = "_".join(parts) + ".pdf"
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=fname,
            title="Save PDF as",
        )
        if path:
            import shutil
            shutil.copy2(self._pdf_path, path)
            self._status.configure(
                text=f"✓ Saved: {os.path.basename(path)}", text_color=SUCCESS)

    def _print(self):
        PrintDialog(self, self._pdf_path, self._status)


# ── Printer selection dialog ──────────────────────────────────
class PrintDialog(ctk.CTkToplevel):
    def __init__(self, parent, pdf_path, status_label):
        super().__init__(parent)
        self.title("Print")
        self.geometry("420x300")
        self.resizable(False, False)
        self.grab_set()
        self._pdf_path    = pdf_path
        self._status_lbl  = status_label
        self._printers    = []
        self._build()
        self._load_printers()

    def _build(self):
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(fill="both", expand=True)

        f = ctk.CTkFrame(outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=(24, 0))

        heading(f, "Select printer", size=15).pack(anchor="w", pady=(0, 12))

        self._printer_list = ctk.CTkScrollableFrame(
            f, fg_color=SURFACE, border_color=BORDER,
            border_width=1, corner_radius=8, height=140)
        self._printer_list.pack(fill="x", pady=(0, 12))

        self._loading = muted(self._printer_list, "Detecting printers...")
        self._loading.pack(pady=12)

        self._msg = ctk.CTkLabel(f, text="", font=("", 11),
                                  text_color=TEXT_MUTED)
        self._msg.pack(anchor="w", pady=(0, 8))

        self._selected_printer = None

        # Pinned footer
        btn_row = ctk.CTkFrame(outer, fg_color=SURFACE,
                               border_color=BORDER, border_width=1,
                               corner_radius=0, height=56)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)
        ghost_btn(btn_row, "Cancel", command=self.destroy,
                  width=100).pack(side="left", padx=20, pady=10)
        self._print_btn = primary_btn(
            btn_row, "Print", command=self._do_print, width=100)
        self._print_btn.pack(side="right", padx=20, pady=10)
        self._print_btn.configure(state="disabled")

    def _load_printers(self):
        import subprocess, platform
        printers = []

        try:
            if platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ["lpstat", "-a"],
                    capture_output=True, text=True, timeout=5)
                for line in result.stdout.splitlines():
                    name = line.split()[0]
                    if name:
                        printers.append(name)
            elif platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "printer", "get", "name"],
                    capture_output=True, text=True, timeout=5)
                for line in result.stdout.splitlines()[1:]:
                    name = line.strip()
                    if name:
                        printers.append(name)
            else:  # Linux
                result = subprocess.run(
                    ["lpstat", "-a"],
                    capture_output=True, text=True, timeout=5)
                for line in result.stdout.splitlines():
                    name = line.split()[0]
                    if name:
                        printers.append(name)
        except Exception:
            printers = []

        self._printers = printers
        self._loading.pack_forget()

        if not printers:
            ctk.CTkLabel(
                self._printer_list,
                text="No printers found.\nConnect a printer and try again.",
                font=("", 12), text_color=TEXT_MUTED,
                justify="center").pack(pady=16)
            self._msg.configure(
                text="Tip: You can also Preview PDF and print from there.",
                text_color=TEXT_MUTED)
            return

        self._printer_vars = []
        selected_var = ctk.StringVar(value="")

        for p in printers:
            var = ctk.BooleanVar(value=False)
            self._printer_vars.append((p, var))
            row = ctk.CTkFrame(self._printer_list, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkRadioButton(
                row, text=p,
                variable=selected_var, value=p,
                font=("", 12), text_color=TEXT,
                fg_color=ACCENT, hover_color=ACCENT_DARK,
                command=lambda pn=p: self._select_printer(pn),
            ).pack(anchor="w", padx=8)

        # Auto-select first
        self._select_printer(printers[0])

    def _select_printer(self, name):
        self._selected_printer = name
        self._print_btn.configure(state="normal")

    def _do_print(self):
        if not self._selected_printer:
            return
        import subprocess, platform
        self._msg.configure(text="Sending to printer...",
                            text_color=TEXT_MUTED)
        self.update()
        try:
            if platform.system() == "Windows":
                import subprocess
                subprocess.run(
                    ["print", f"/D:{self._selected_printer}",
                     self._pdf_path],
                    shell=True, check=True)
            else:
                subprocess.run(
                    ["lpr", "-P", self._selected_printer, self._pdf_path],
                    check=True, timeout=15)
            self._msg.configure(
                text=f"✓ Sent to {self._selected_printer}",
                text_color=SUCCESS)
            try:
                self._status_lbl.configure(
                    text=f"✓ Printed on {self._selected_printer}",
                    text_color=SUCCESS)
            except Exception:
                pass
            self.after(1500, self.destroy)
        except Exception as e:
            self._msg.configure(
                text=f"Print failed: {e}\nTry Preview PDF and print manually.",
                text_color=DANGER)
