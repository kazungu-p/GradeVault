import customtkinter as ctk
import os
from tkinter import filedialog
from utils.theme import *
from routes.terms import get_all_terms, get_current_term
from routes.assessments import get_assessments
from routes.classes import get_classes
from routes.settings import get_setting, set_setting
from utils.grading import detect_curriculum


# ── Default comment templates ─────────────────────────────────
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

        heading(self, "Reports & Grading").pack(anchor="w", pady=(0, 16))

        # Tab bar
        tabs = ctk.CTkFrame(self, fg_color="transparent")
        tabs.pack(fill="x", pady=(0, 14))
        self._tab_var = ctk.StringVar(value="generate")
        for key, lbl in [("generate", "Generate reports"),
                          ("comments", "Comment templates")]:
            ctk.CTkButton(
                tabs, text=lbl, width=160, height=30,
                fg_color=ACCENT if self._tab_var.get() == key else "transparent",
                text_color="white" if self._tab_var.get() == key else TEXT_MUTED,
                hover_color=ACCENT_BG, corner_radius=6, font=("", 12),
                command=lambda k=key: self._switch_tab(k),
            ).pack(side="left", padx=(0, 6))

        self._tab_frames = {}
        self._generate_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._comments_frame = ctk.CTkFrame(self, fg_color="transparent")

        self._build_generate(self._generate_frame)
        self._build_comments(self._comments_frame)
        self._switch_tab("generate")

    def _switch_tab(self, key):
        self._tab_var.set(key)
        self._generate_frame.pack_forget()
        self._comments_frame.pack_forget()
        if key == "generate":
            self._generate_frame.pack(fill="both", expand=True)
        else:
            self._comments_frame.pack(fill="both", expand=True)
        # Refresh tab button colors
        for w in self.winfo_children():
            if isinstance(w, ctk.CTkFrame) and w != self._generate_frame \
                    and w != self._comments_frame:
                for btn in w.winfo_children():
                    if isinstance(btn, ctk.CTkButton):
                        is_active = (btn.cget("text").lower().startswith(
                            key.replace("_", " ")))

    # ── Generate tab ──────────────────────────────────────────
    def _build_generate(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        # Step 1 — Select
        s1 = self._section(scroll, "Step 1 — Select term, assessment and class")
        f1 = ctk.CTkFrame(s1, fg_color="transparent")
        f1.pack(fill="x", padx=16, pady=(0, 16))

        # Term
        muted(f1, "Term").pack(anchor="w")
        terms = get_all_terms()
        term_labels = [f"Term {t['term']}, {t['year']}" for t in terms]
        current = get_current_term()
        default_term = (f"Term {current['term']}, {current['year']}"
                        if current and term_labels else
                        (term_labels[0] if term_labels else "—"))
        self._term_var = ctk.StringVar(value=default_term)
        self._terms_data = terms
        ctk.CTkOptionMenu(f1, variable=self._term_var,
                          values=term_labels if term_labels else ["—"],
                          width=300, fg_color=SURFACE,
                          button_color=BORDER, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          command=self._on_term_change,
                          ).pack(anchor="w", pady=(4, 12))

        # Assessment
        muted(f1, "Assessment").pack(anchor="w")
        self._asmt_var = ctk.StringVar(value="—")
        self._asmt_menu = ctk.CTkOptionMenu(
            f1, variable=self._asmt_var,
            values=["—"], width=300,
            fg_color=SURFACE, button_color=BORDER,
            text_color=TEXT, dropdown_fg_color=SURFACE)
        self._asmt_menu.pack(anchor="w", pady=(4, 12))
        self._asmt_data = []
        self._on_term_change()

        # Class
        muted(f1, "Class").pack(anchor="w")
        classes = get_classes()
        self._classes_data = classes
        class_labels = [
            f"{c['name']}{' ' + c['stream'] if c.get('stream') else ''}"
            for c in classes
        ]
        self._class_var = ctk.StringVar(
            value=class_labels[0] if class_labels else "—")
        self._class_menu = ctk.CTkOptionMenu(
            f1, variable=self._class_var,
            values=class_labels if class_labels else ["—"],
            width=300, fg_color=SURFACE,
            button_color=BORDER, text_color=TEXT,
            dropdown_fg_color=SURFACE,
            command=self._on_class_change,
        )
        self._class_menu.pack(anchor="w", pady=(4, 0))

        # Curriculum detection
        self._curr_label = muted(f1, "")
        self._curr_label.pack(anchor="w", pady=(4, 0))
        self._on_class_change()

        # Step 2 — Generate
        s2 = self._section(scroll, "Step 2 — Generate")
        f2 = ctk.CTkFrame(s2, fg_color="transparent")
        f2.pack(fill="x", padx=16, pady=(0, 16))

        muted(f2, "Report cards will be generated for all students in the "
                  "selected class.\nBest-7 rule applied automatically for "
                  "8-4-4 classes. Comment templates from the 'Comment "
                  "templates' tab will be used.").pack(anchor="w", pady=(0, 12))

        self._gen_status = ctk.CTkLabel(
            f2, text="", font=("", 12), text_color=TEXT_MUTED)
        self._gen_status.pack(anchor="w", pady=(0, 8))

        primary_btn(f2, "Generate report cards →",
                    command=self._generate, width=220).pack(anchor="w")

    def _on_term_change(self, _=None):
        term_label = self._term_var.get()
        term = next((t for t in self._terms_data
                     if f"Term {t['term']}, {t['year']}" == term_label), None)
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
                    if f"{c['name']}{' ' + c['stream'] if c.get('stream') else ''}"
                    == cls_label), None)
        if cls:
            curr = detect_curriculum(cls["name"])
            self._curr_label.configure(
                text=f"Detected curriculum: {curr}",
                text_color=ACCENT)

    def _generate(self):
        from utils.report_pdf import generate_report_cards

        asmt_name = self._asmt_var.get()
        asmt = next((a for a in self._asmt_data
                     if a["name"] == asmt_name), None)
        cls_label = self._class_var.get()
        cls = next((c for c in self._classes_data
                    if f"{c['name']}{' ' + c['stream'] if c.get('stream') else ''}"
                    == cls_label), None)

        if not asmt or not cls:
            self._gen_status.configure(
                text="Please select an assessment and class.", text_color=DANGER)
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"reports_{cls_label.replace(' ', '_')}.pdf",
            title="Save report cards as",
        )
        if not path:
            return

        self._gen_status.configure(
            text="Generating... please wait.", text_color=TEXT_MUTED)
        self.update()

        try:
            count, _ = generate_report_cards(
                path, asmt["id"], cls["id"], self._comments)
            self._gen_status.configure(
                text=f"✓ {count} report card(s) generated successfully.",
                text_color=SUCCESS)
            os.system(f'open "{path}"' if os.name != "nt"
                      else f'start "" "{path}"')
        except Exception as e:
            self._gen_status.configure(
                text=f"Error: {e}", text_color=DANGER)

    # ── Comments tab ──────────────────────────────────────────
    def _build_comments(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        self._comment_widgets = {}

        for role, role_label in [
            ("principal", "Principal's comments"),
            ("teacher",   "Class teacher's comments"),
        ]:
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

        # Save button
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=16)
        self._save_msg = ctk.CTkLabel(
            btn_row, text="", font=("", 12), text_color=SUCCESS)
        self._save_msg.pack(side="right", padx=(0, 16))
        primary_btn(btn_row, "Save comment templates",
                    command=self._save_comments, width=200).pack(side="right")

    def _save_comments(self):
        for key, box in self._comment_widgets.items():
            text = box.get("1.0", "end").strip()
            self._comments[key] = text
            set_setting(f"comment_{key}", text)
        self._save_msg.configure(text="✓ Templates saved.")
        self.after(2000, lambda: self._save_msg.configure(text=""))

    def _section(self, parent, title):
        c = card(parent)
        c.pack(fill="x", pady=(0, 14))
        hdr = ctk.CTkFrame(c, fg_color=ACCENT_BG, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=title, font=("", 13, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=16, pady=10)
        return c
