import customtkinter as ctk
import os
import tempfile
from tkinter import filedialog
from utils.theme import *
from routes.terms import get_all_terms, get_current_term
from routes.assessments import get_assessments
from routes.classes import get_classes
from routes.settings import get_setting, set_setting
from utils.grading import detect_curriculum
from db.connection import query, execute, execute_many

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
    ("EE", 75, 100, 4),
    ("ME", 50, 74,  3),
    ("AE", 25, 49,  2),
    ("BE",  0, 24,  1),
]


class ReportsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._comments = {}
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

        self._frames = {}
        for key in ("generate", "comments", "grading"):
            f = ctk.CTkFrame(self, fg_color="transparent")
            self._frames[key] = f

        # Build all tabs upfront — prevents flash on switch
        self._build_generate(self._frames["generate"])
        self._build_comments(self._frames["comments"])
        self._build_grading(self._frames["grading"])

        # Place all frames in same grid position, switch visibility
        for f in self._frames.values():
            f.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._switch_tab("generate")

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
        class_labels = [
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

        s2 = self._section(scroll, "Generate")
        f2 = ctk.CTkFrame(s2, fg_color="transparent")
        f2.pack(fill="x", padx=16, pady=(0, 16))

        muted(f2,
              "Clicking Generate will process all students in the selected class,\n"
              "apply the best-7 rule, compute grades and open a preview window."
              ).pack(anchor="w", pady=(0, 12))

        self._gen_status = ctk.CTkLabel(
            f2, text="", font=("", 12), text_color=TEXT_MUTED)
        self._gen_status.pack(anchor="w", pady=(0, 8))

        primary_btn(f2, "Generate & preview →",
                    command=self._generate, width=200).pack(anchor="w")

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

    def _on_class_change(self, _=None):
        cls_label = self._class_var.get()
        cls = next((c for c in self._classes_data
                    if f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
                    == cls_label), None)
        if cls:
            curr = detect_curriculum(cls["name"])
            self._curr_label.configure(
                text=f"Curriculum: {curr}",
                text_color=ACCENT)

    def _generate(self):
        from utils.report_pdf import generate_report_cards

        asmt = next((a for a in self._asmt_data
                     if a["name"] == self._asmt_var.get()), None)
        cls_label = self._class_var.get()
        cls  = next((c for c in self._classes_data
                     if f"{c['name']}{' '+c['stream'] if c.get('stream') else ''}"
                     == cls_label), None)

        if not asmt or not cls:
            self._gen_status.configure(
                text="Please select an assessment and class.",
                text_color=DANGER)
            return

        self._gen_status.configure(
            text="Generating... please wait.", text_color=TEXT_MUTED)
        self.update()

        try:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf", delete=False,
                prefix=f"reports_{cls_label.replace(' ','_')}_")
            tmp_path = tmp.name
            tmp.close()

            count, _ = generate_report_cards(
                tmp_path, asmt["id"], cls["id"], self._comments)

            if count == 0:
                self._gen_status.configure(
                    text="No marks found for this class and assessment.",
                    text_color=DANGER)
                return

            self._gen_status.configure(
                text=f"✓ {count} report card(s) ready.", text_color=SUCCESS)

            ReportPreviewDialog(self, tmp_path, cls_label,
                                asmt["name"], count)

        except Exception as e:
            self._gen_status.configure(
                text=f"Error: {e}", text_color=DANGER)

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
            sf.pack(fill="x", padx=16, pady=(0, 14))

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
                    e.bind("<FocusOut>",
                           lambda ev, sk=setting_key, ew=e: (
                               set_setting(sk, ew.get().strip())))
                    e.bind("<Return>",
                           lambda ev, sk=setting_key, ew=e: (
                               set_setting(sk, ew.get().strip())))

            muted(sf, "Changes are saved automatically when you click away from each field."
                  ).pack(anchor="w", pady=(8, 0))

        # Reset to defaults button
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=16)
        ghost_btn(btn_row, "Reset to defaults",
                  command=self._reset_grading, width=150).pack(side="right")

    def _reset_grading(self):
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
        self._frames["grading"] = ctk.CTkFrame(self, fg_color="transparent")
        self._build_grading(self._frames["grading"])
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
        f = ctk.CTkFrame(self, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=28)

        # Success header
        ctk.CTkLabel(f, text="✓", font=("", 36, "bold"),
                     text_color=SUCCESS).pack(pady=(0, 4))
        heading(f, f"{self._count} report card(s) generated",
                size=16).pack()
        muted(f, f"{self._class_label}  ·  {self._asmt_name}"
              ).pack(pady=(2, 20))

        divider(f).pack(fill="x", pady=(0, 16))

        muted(f, "What would you like to do?").pack(anchor="w", pady=(0, 10))

        # Action buttons
        actions = ctk.CTkFrame(f, fg_color="transparent")
        actions.pack(fill="x")

        # Preview (open PDF)
        primary_btn(actions, "Preview PDF",
                    command=self._preview, width=130).pack(
            side="left", padx=(0, 8))

        # Save as PDF
        ghost_btn(actions, "Save PDF",
                  command=self._save_pdf, width=110).pack(
            side="left", padx=(0, 8))

        # Print
        ghost_btn(actions, "Print",
                  command=self._print, width=90).pack(side="left")

        self._status = ctk.CTkLabel(
            f, text="", font=("", 11), text_color=TEXT_MUTED)
        self._status.pack(anchor="w", pady=(12, 0))

    def _preview(self):
        if os.name == "nt":
            os.startfile(self._pdf_path)
        else:
            os.system(f'open "{self._pdf_path}"')

    def _save_pdf(self):
        safe = self._class_label.replace(" ", "_")
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"reports_{safe}.pdf",
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
        f = ctk.CTkFrame(self, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=28)

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

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x")
        ghost_btn(btn_row, "Cancel", command=self.destroy,
                  width=100).pack(side="left")
        self._print_btn = primary_btn(
            btn_row, "Print", command=self._do_print, width=100)
        self._print_btn.pack(side="right")
        self._print_btn.configure(state="disabled")
        self._selected_printer = None

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
