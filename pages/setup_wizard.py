import customtkinter as ctk
from utils.theme import *
from routes.settings import set_setting, mark_setup_complete
from routes.classes import create_class, create_subject
from db.connection import execute as db_execute, query_one
import bcrypt
from datetime import date

# ── All possible classes ──────────────────────────────────────
ALL_CLASSES = [
    ("ECDE",        "PP1"),
    ("ECDE",        "PP2"),
    ("Lower Primary (CBC)", "Grade 1"),
    ("Lower Primary (CBC)", "Grade 2"),
    ("Lower Primary (CBC)", "Grade 3"),
    ("Upper Primary (CBC)", "Grade 4"),
    ("Upper Primary (CBC)", "Grade 5"),
    ("Upper Primary (CBC)", "Grade 6"),
    ("Junior Secondary (CBC)", "Grade 7"),
    ("Junior Secondary (CBC)", "Grade 8"),
    ("Junior Secondary (CBC)", "Grade 9"),
    ("Senior Secondary (CBC)", "Grade 10"),
    ("Senior Secondary (CBC)", "Grade 11"),
    ("Senior Secondary (CBC)", "Grade 12"),
    ("Secondary (8-4-4)", "Form 1"),
    ("Secondary (8-4-4)", "Form 2"),
    ("Secondary (8-4-4)", "Form 3"),
    ("Secondary (8-4-4)", "Form 4"),
]

# ── Section display order ─────────────────────────────────────
SECTION_ORDER = [
    "ECDE",
    "Lower Primary (CBC)",
    "Upper Primary (CBC)",
    "Junior Secondary (CBC)",
    "Senior Secondary (CBC)",
    "Secondary (8-4-4)",
]

# ── Subject presets per curriculum ───────────────────────────
SUBJECT_PRESETS = {
    "ECDE": [
        "Language Activities",
        "Mathematical Activities",
        "Environmental Activities",
        "Psychomotor & Creative Activities",
        "Religious Education Activities",
    ],
    "Lower Primary (CBC)": [
        "Literacy",
        "Kiswahili Language Activities",
        "Mathematics",
        "Environmental Activities",
        "Christian Religious Education",
        "Islamic Religious Education",
        "Hindu Religious Education",
        "Creative Arts",
        "Physical & Health Education",
    ],
    "Upper Primary (CBC)": [
        "English",
        "Kiswahili",
        "Mathematics",
        "Integrated Science",
        "Social Studies",
        "Christian Religious Education",
        "Islamic Religious Education",
        "Creative Arts & Sports",
        "Agriculture",
        "Home Science",
        "ICT",
    ],
    "Junior Secondary (CBC)": [
        "Mathematics", "English", "Kiswahili",
        "Integrated Science", "Social Studies",
        "Religious Education", "Business Studies",
        "Agriculture", "Home Science", "Visual Arts",
        "Performing Arts", "Physical Education",
        "Health Education", "ICT", "Arabic",
        "French", "German", "Fasihi",
        "Literature in English",
    ],
    "Senior Secondary (CBC)": [
        "Mathematics", "English", "Kiswahili",
        "Biology", "Chemistry", "Physics",
        "History & Government", "Geography",
        "Christian Religious Education", "Business Studies",
        "Economics", "Computer Science", "ICT",
        "Literature in English", "Fasihi",
        "French", "German", "Arabic",
        "Visual Arts", "Performing Arts",
        "Physical Education", "Agriculture", "Home Science",
    ],
    "Secondary (8-4-4)": [
        "Mathematics", "English", "Kiswahili", "Biology",
        "Chemistry", "Physics", "History & Government",
        "Geography", "Christian Religious Education",
        "Islamic Religious Education", "Hindu Religious Education",
        "Home Science", "Agriculture", "Business Studies",
        "Computer Studies", "Art & Design", "Music",
        "French", "German", "Arabic",
        "Woodwork", "Metalwork", "Building & Construction",
        "Power Mechanics", "Electricity",
    ],
}

STEPS = [
    "Welcome",
    "School info",
    "Classes",
    "Streams",
    "Subjects",
    "Admin account",
    "Done",
]


class SetupWizard(ctk.CTkToplevel):
    def __init__(self, parent, on_complete):
        super().__init__(parent)
        self.title("GradeVault — First-time setup")
        self.geometry("820x620")
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self._on_complete = on_complete
        self._step = 0

        # state
        self._school_name   = ""
        self._school_motto  = ""
        self._selected_classes = []   # list of (curriculum, class_name)
        self._use_streams   = False
        self._streams       = []      # stream name strings
        self._subjects      = []      # final subject name list
        self._admin_pw      = ""

        self._build_shell()
        self._show_step(0)

    # ── Shell ─────────────────────────────────────────────────
    def _build_shell(self):
        self._left = ctk.CTkFrame(self, fg_color=ACCENT, width=200,
                                   corner_radius=0)
        self._left.pack(side="left", fill="y")
        self._left.pack_propagate(False)

        ctk.CTkLabel(self._left, text="GradeVault",
                     font=("", 18, "bold"),
                     text_color="white").pack(pady=(32, 4), padx=20)
        ctk.CTkLabel(self._left, text="School setup",
                     font=("", 12),
                     text_color="#C7D2FE").pack(padx=20)
        ctk.CTkFrame(self._left, fg_color="#6366F1",
                     height=1).pack(fill="x", padx=20, pady=20)

        self._step_labels = []
        for s in STEPS:
            lbl = ctk.CTkLabel(self._left, text=f"  {s}",
                               font=("", 12), anchor="w",
                               text_color="white")
            lbl.pack(fill="x", padx=16, pady=3)
            self._step_labels.append(lbl)

        self._right = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._right.pack(side="left", fill="both", expand=True)

        self._content = ctk.CTkScrollableFrame(
            self._right, fg_color=BG, corner_radius=0)
        self._content.pack(fill="both", expand=True, padx=36, pady=28)

        nav = ctk.CTkFrame(self._right, fg_color=SURFACE,
                           border_color=BORDER, border_width=1,
                           corner_radius=0, height=60)
        nav.pack(fill="x", side="bottom")
        nav.pack_propagate(False)

        self._back_btn = ghost_btn(nav, "← Back",
                                   command=self._prev, width=100)
        self._back_btn.pack(side="left", padx=20, pady=12)

        self._next_btn = primary_btn(nav, "Next →",
                                     command=self._next, width=130)
        self._next_btn.pack(side="right", padx=20, pady=12)

    def _update_progress(self):
        for i, lbl in enumerate(self._step_labels):
            if i < self._step:
                lbl.configure(text=f"  ✓ {STEPS[i]}",
                              text_color="#A5B4FC",
                              font=("", 12))
            elif i == self._step:
                lbl.configure(text=f"  › {STEPS[i]}",
                              text_color="white",
                              font=("", 12, "bold"))
            else:
                lbl.configure(text=f"    {STEPS[i]}",
                              text_color="#818CF8",
                              font=("", 12))

        self._back_btn.configure(
            state="normal" if self._step > 0 else "disabled")
        last = len(STEPS) - 1
        self._next_btn.configure(
            text="Finish ✓" if self._step == last - 1 else "Next →",
            state="disabled" if self._step == last else "normal",
        )

    def _show_step(self, step):
        self._step = step
        self._update_progress()
        for w in self._content.winfo_children():
            w.destroy()
        [self._step_welcome, self._step_school_info,
         self._step_classes, self._step_streams,
         self._step_subjects, self._step_admin,
         self._step_done][step]()

    def _next(self):
        if not self._validate():
            return
        self._collect()
        if self._step < len(STEPS) - 1:
            self._show_step(self._step + 1)

    def _prev(self):
        if self._step > 0:
            self._show_step(self._step - 1)

    # ── Steps ─────────────────────────────────────────────────
    def _step_welcome(self):
        ctk.CTkLabel(self._content, text="Welcome to GradeVault",
                     font=("", 22, "bold"),
                     text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(
            self._content,
            text=(
                "Let's set up your school in a few quick steps.\n"
                "This wizard runs once — you can change everything later.\n\n"
                "You will:\n"
                "  •  Enter your school name\n"
                "  •  Pick exactly which classes you currently run\n"
                "  •  Configure streams (optional)\n"
                "  •  Choose your subjects\n"
                "  •  Set your admin password"
            ),
            font=("", 13), text_color=TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", pady=(16, 0))

    def _step_school_info(self):
        heading(self._content,
                "School information").pack(anchor="w", pady=(0, 20))

        muted(self._content, "School name *").pack(anchor="w")
        self._sname = ctk.CTkEntry(
            self._content, width=520,
            fg_color=SURFACE, border_color=BORDER)
        self._sname.pack(anchor="w", pady=(2, 12))
        if self._school_name:
            self._sname.insert(0, self._school_name)

        muted(self._content, "Motto (optional)").pack(anchor="w")
        self._smotto = ctk.CTkEntry(
            self._content, width=520,
            fg_color=SURFACE, border_color=BORDER)
        self._smotto.pack(anchor="w", pady=(2, 12))
        if self._school_motto:
            self._smotto.insert(0, self._school_motto)

        self._err = ctk.CTkLabel(self._content, text="",
                                  text_color=DANGER, font=("", 12))
        self._err.pack(anchor="w")

    def _step_classes(self):
        heading(self._content,
                "Which classes does your school currently run?"
                ).pack(anchor="w", pady=(0, 4))
        muted(
            self._content,
            "Tick only the classes you have RIGHT NOW.\n"
            "You can add or remove classes later as your school grows."
        ).pack(anchor="w", pady=(0, 16))

        self._class_vars = {}
        sections = [
            ("8-4-4  (Senior Secondary)",
             [c for c in ALL_CLASSES if c[0] == "8-4-4"]),
            ("CBE Junior Secondary (Grade 7–9)",
             [c for c in ALL_CLASSES if c[0] == "CBE Jr"]),
            ("CBE Senior Secondary (Grade 10–12)",
             [c for c in ALL_CLASSES if c[0] == "CBE Sr"]),
        ]

        for section_title, classes in sections:
            sec = ctk.CTkFrame(self._content,
                               fg_color=SURFACE,
                               border_color=BORDER,
                               border_width=1,
                               corner_radius=8)
            sec.pack(fill="x", pady=(0, 12))

            ctk.CTkLabel(sec, text=section_title,
                         font=("", 12, "bold"),
                         text_color=ACCENT).pack(
                anchor="w", padx=14, pady=(10, 6))

            row = ctk.CTkFrame(sec, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=(0, 10))

            for i, (curr, cls_name) in enumerate(classes):
                key = f"{curr}|{cls_name}"
                var = ctk.BooleanVar(
                    value=key in [
                        f"{c[0]}|{c[1]}"
                        for c in self._selected_classes
                    ]
                )
                self._class_vars[key] = var
                ctk.CTkCheckBox(
                    row, text=cls_name,
                    variable=var,
                    font=("", 12), text_color=TEXT,
                    fg_color=ACCENT, hover_color=ACCENT_DARK,
                ).grid(row=0, column=i, padx=(0, 20), sticky="w")

        self._class_err = ctk.CTkLabel(
            self._content, text="",
            text_color=DANGER, font=("", 12))
        self._class_err.pack(anchor="w", pady=(4, 0))

    def _step_streams(self):
        heading(self._content, "Streams").pack(anchor="w", pady=(0, 4))
        muted(
            self._content,
            "Does your school have multiple streams per class?\n"
            "e.g. Form 1A, Form 1B  or  Grade 10 North, Grade 10 South"
        ).pack(anchor="w", pady=(0, 14))

        self._stream_var = ctk.BooleanVar(value=self._use_streams)
        ctk.CTkCheckBox(
            self._content,
            text="Yes — my school has multiple streams per class",
            variable=self._stream_var,
            font=("", 13), text_color=TEXT,
            fg_color=ACCENT, hover_color=ACCENT_DARK,
            command=self._toggle_stream_entry,
        ).pack(anchor="w", pady=(0, 12))

        self._stream_detail = ctk.CTkFrame(
            self._content, fg_color="transparent")
        self._stream_detail.pack(anchor="w", fill="x")
        self._render_stream_entry()

    def _toggle_stream_entry(self):
        self._render_stream_entry()

    def _render_stream_entry(self):
        for w in self._stream_detail.winfo_children():
            w.destroy()
        if not self._stream_var.get():
            return
        muted(self._stream_detail,
              "Stream names (comma-separated):").pack(anchor="w")
        ctk.CTkLabel(
            self._stream_detail,
            text="e.g.   A, B, C     or     North, South     or     Lion, Rhino",
            font=("", 11), text_color="#9CA3AF",
        ).pack(anchor="w", pady=(0, 4))
        self._streams_entry = ctk.CTkEntry(
            self._stream_detail, width=520,
            fg_color=SURFACE, border_color=BORDER,
            placeholder_text="Type stream names separated by commas")
        self._streams_entry.pack(anchor="w", pady=(0, 4))
        if self._streams:
            self._streams_entry.insert(0, ", ".join(self._streams))

        muted(self._stream_detail,
              "Each class above will get one copy per stream.").pack(
            anchor="w")

    def _step_subjects(self):
        heading(self._content, "Subjects").pack(anchor="w", pady=(0, 4))
        muted(
            self._content,
            "Pre-filled based on your selected classes.\n"
            "Edit freely — one subject per line. You can also manage subjects later."
        ).pack(anchor="w", pady=(0, 10))

        # Build merged preset from selected curricula
        curricula_selected = set(c[0] for c in self._selected_classes)
        merged = []
        seen = set()
        for curr in ["8-4-4", "CBE Jr", "CBE Sr"]:
            if curr in curricula_selected:
                for s in SUBJECT_PRESETS[curr]:
                    if s not in seen:
                        merged.append(s)
                        seen.add(s)

        initial = "\n".join(self._subjects if self._subjects else merged)
        self._subjects_box = ctk.CTkTextbox(
            self._content, width=520, height=320,
            fg_color=SURFACE, border_color=BORDER, font=("", 12))
        self._subjects_box.pack(anchor="w", pady=(2, 0))
        self._subjects_box.insert("1.0", initial)

    def _step_admin(self):
        heading(self._content,
                "Set your admin password").pack(anchor="w", pady=(0, 4))
        muted(
            self._content,
            "The username stays 'admin'. Choose a strong password.\n"
            "This is the master account for your school."
        ).pack(anchor="w", pady=(0, 16))

        muted(self._content, "New password *").pack(anchor="w")
        self._pw1 = ctk.CTkEntry(
            self._content, width=380,
            fg_color=SURFACE, border_color=BORDER, show="•")
        self._pw1.pack(anchor="w", pady=(2, 10))

        muted(self._content, "Confirm password *").pack(anchor="w")
        self._pw2 = ctk.CTkEntry(
            self._content, width=380,
            fg_color=SURFACE, border_color=BORDER, show="•")
        self._pw2.pack(anchor="w", pady=(2, 10))

        self._err = ctk.CTkLabel(self._content, text="",
                                  text_color=DANGER, font=("", 12))
        self._err.pack(anchor="w")

    def _step_done(self):
        self._save_all()
        ctk.CTkLabel(self._content, text="✓",
                     font=("", 52, "bold"),
                     text_color=SUCCESS).pack(pady=(10, 4))
        ctk.CTkLabel(self._content, text="Setup complete!",
                     font=("", 22, "bold"),
                     text_color=TEXT).pack()

        lines = [
            f"  •  School: {self._school_name}",
            f"  •  {len(self._selected_classes)} class(es) configured",
        ]
        if self._use_streams and self._streams:
            lines.append(
                f"  •  {len(self._streams)} stream(s): "
                f"{', '.join(self._streams)}"
            )
        lines.append(f"  •  {len(self._subjects)} subject(s) loaded")
        lines.append("")
        lines.append("Click 'Launch GradeVault' to get started.")

        ctk.CTkLabel(
            self._content,
            text="\n".join(lines),
            font=("", 13), text_color=TEXT_MUTED,
            justify="left",
        ).pack(pady=(12, 24))

        primary_btn(self._content, "Launch GradeVault →",
                    command=self._finish, width=220).pack()

    # ── Validate ─────────────────────────────────────────────
    def _validate(self) -> bool:
        if self._step == 1:
            if not self._sname.get().strip():
                self._err.configure(text="School name is required.")
                return False
        if self._step == 2:
            selected = [k for k, v in self._class_vars.items() if v.get()]
            if not selected:
                self._class_err.configure(
                    text="Please select at least one class.")
                return False
        if self._step == 5:
            p1 = self._pw1.get()
            p2 = self._pw2.get()
            if not p1:
                self._err.configure(text="Password is required.")
                return False
            if len(p1) < 6:
                self._err.configure(
                    text="Password must be at least 6 characters.")
                return False
            if p1 != p2:
                self._err.configure(text="Passwords do not match.")
                return False
        return True

    # ── Collect ───────────────────────────────────────────────
    def _collect(self):
        if self._step == 1:
            self._school_name  = self._sname.get().strip()
            self._school_motto = self._smotto.get().strip()
        elif self._step == 2:
            self._selected_classes = [
                tuple(k.split("|"))
                for k, v in self._class_vars.items()
                if v.get()
            ]
        elif self._step == 3:
            self._use_streams = self._stream_var.get()
            if self._use_streams and hasattr(self, "_streams_entry"):
                raw = self._streams_entry.get()
                self._streams = [
                    s.strip() for s in raw.split(",") if s.strip()
                ]
            else:
                self._streams = []
        elif self._step == 4:
            raw = self._subjects_box.get("1.0", "end").strip()
            self._subjects = [
                l.strip() for l in raw.splitlines() if l.strip()
            ]
        elif self._step == 5:
            self._admin_pw = self._pw1.get()

    # ── Save ─────────────────────────────────────────────────
    def _save_all(self):
        set_setting("school_name",  self._school_name)
        set_setting("school_motto", self._school_motto)

        # Classes
        db_execute("DELETE FROM classes")
        curricula_order = ["8-4-4", "CBE Jr", "CBE Sr"]
        sorted_classes = sorted(
            self._selected_classes,
            key=lambda c: (
                curricula_order.index(c[0])
                if c[0] in curricula_order else 99,
                c[1],
            ),
        )
        for i, (curr, cls_name) in enumerate(sorted_classes):
            if self._use_streams and self._streams:
                for stream in self._streams:
                    create_class(cls_name, stream, sort_order=i)
            else:
                create_class(cls_name, None, sort_order=i)

        # Subjects
        db_execute("DELETE FROM subjects")
        for subj in self._subjects:
            create_subject(subj)

        # Admin password
        if self._admin_pw:
            pw_hash = bcrypt.hashpw(
                self._admin_pw.encode(), bcrypt.gensalt()
            ).decode()
            db_execute(
                "UPDATE users SET password_hash=? WHERE username='admin'",
                (pw_hash,),
            )

        # Default term
        if not query_one("SELECT id FROM terms LIMIT 1"):
            db_execute(
                "INSERT INTO terms (year, term, is_current) VALUES (?,?,1)",
                (date.today().year, 1),
            )

        mark_setup_complete()

    def _finish(self):
        self.destroy()
        self._on_complete()
