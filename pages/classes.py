import customtkinter as ctk
from utils.theme import *
from pages.promotion import PromotionWizard
from routes.classes import (
    get_classes, create_class, update_class, delete_class,
    bulk_promote, get_subjects, create_subject,
    update_subject, delete_subject, toggle_subject_active,
)


class ClassesPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._build()
        self._load_classes()
        self._load_subjects()

    def _build(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)

        # Tab switcher
        tabs = ctk.CTkFrame(self, fg_color="transparent")
        tabs.pack(fill="x", pady=(0, 16))
        heading(tabs, "Classes & Subjects").pack(side="left")

        self._tab_var = ctk.StringVar(value="Classes")
        for t in ["Classes", "Subjects"]:
            ctk.CTkButton(
                tabs, text=t, width=100, height=30,
                fg_color=ACCENT, text_color="white",
                corner_radius=6, font=("", 12),
                command=lambda x=t: self._switch_tab(x),
            ).pack(side="right", padx=(6, 0))

        self._classes_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._subjects_frame = ctk.CTkFrame(self, fg_color="transparent")

        self._build_classes_panel()
        self._build_subjects_panel()
        self._switch_tab("Classes")

    def _switch_tab(self, tab):
        self._tab_var.set(tab)
        if tab == "Classes":
            self._subjects_frame.pack_forget()
            self._classes_frame.pack(fill="both", expand=True)
        else:
            self._classes_frame.pack_forget()
            self._subjects_frame.pack(fill="both", expand=True)

    # ── Classes panel ─────────────────────────────────────────
    def _build_classes_panel(self):
        f = self._classes_frame

        ctrl = ctk.CTkFrame(f, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 10))
        muted(ctrl, "Manage your school's classes and streams.").pack(side="left")
        primary_btn(ctrl, "+ Add class",
                    command=self._add_class, width=110).pack(side="right")
        ghost_btn(ctrl, "Bulk promote",
                  command=self._bulk_promote_dialog,
                  width=110).pack(side="right", padx=(0, 8))
        primary_btn(ctrl, "End-of-year →",
                    command=self._end_of_year,
                    width=130).pack(side="right", padx=(0, 8))

        tcard = card(f)
        tcard.pack(fill="both", expand=True)

        thead = ctk.CTkFrame(tcard, fg_color="#F3F4F6", corner_radius=0)
        thead.pack(fill="x", padx=1, pady=(1, 0))
        for col, w in [("Class", 160), ("Stream", 100),
                        ("Students", 90), ("Actions", 180)]:
            ctk.CTkLabel(thead, text=col, font=("", 11, "bold"),
                         text_color=TEXT_MUTED, width=w,
                         anchor="w").pack(side="left", padx=(12, 0), pady=8)

        self._classes_body = ctk.CTkScrollableFrame(
            tcard, fg_color=SURFACE, corner_radius=0)
        self._classes_body.pack(fill="both", expand=True, padx=1, pady=(0, 1))

    def _load_classes(self):
        from db.connection import query_one as qone
        for w in self._classes_body.winfo_children():
            w.destroy()

        classes = get_classes()
        if not classes:
            muted(self._classes_body,
                  "No classes yet. Click '+ Add class' to get started."
                  ).pack(pady=24)
            return

        for i, c in enumerate(classes):
            bg = SURFACE if i % 2 == 0 else "#FAFAFA"
            row = ctk.CTkFrame(self._classes_body, fg_color=bg,
                               corner_radius=0, height=40)
            row.pack(fill="x")
            row.pack_propagate(False)

            name_txt = c["name"]
            if c.get("is_combined"):
                name_txt += "  ⬡"  # combined marker
            ctk.CTkLabel(row, text=name_txt, font=("", 12),
                         text_color=ACCENT if c.get("is_combined") else TEXT,
                         width=180, anchor="w").pack(side="left", padx=(12, 0))
            ctk.CTkLabel(row, text=c["stream"] or "—", font=("", 12),
                         text_color=TEXT_MUTED, width=100,
                         anchor="w").pack(side="left", padx=(12, 0))

            from db.connection import query_one
            count = query_one(
                "SELECT COUNT(*) AS n FROM students "
                "WHERE class_id=? AND status='active'",
                (c["id"],)) or {}
            ctk.CTkLabel(row, text=str(count.get("n", 0)),
                         font=("", 12), text_color=TEXT_MUTED,
                         width=90, anchor="w").pack(side="left", padx=(12, 0))

            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(side="left", padx=8)

            ctk.CTkButton(actions, text="Edit", width=50, height=26,
                          fg_color="transparent", border_color=BORDER,
                          border_width=1, text_color=TEXT, corner_radius=6,
                          hover_color=BG, font=("", 11),
                          command=lambda cl=c: self._edit_class(cl)
                          ).pack(side="left", padx=(0, 4))

            ctk.CTkButton(actions, text="Retire", width=56, height=26,
                          fg_color="transparent", border_color=WARNING,
                          border_width=1, text_color=WARNING, corner_radius=6,
                          hover_color="#FFFBEB", font=("", 11),
                          command=lambda cl=c: self._retire_class(cl)
                          ).pack(side="left", padx=(0, 4))

            ctk.CTkButton(actions, text="Delete", width=58, height=26,
                          fg_color="transparent", border_color=DANGER,
                          border_width=1, text_color=DANGER, corner_radius=6,
                          hover_color="#FEF2F2", font=("", 11),
                          command=lambda cl=c: self._delete_class(cl)
                          ).pack(side="left")

    def _add_class(self):
        ClassForm(self, title="Add class", on_save=self._on_add_class)

    def _edit_class(self, cls):
        ClassForm(self, title="Edit class", cls=cls,
                  on_save=self._on_edit_class)

    def _on_add_class(self, name, stream, is_combined=False, description=None):
        ok, msg = create_class(name, stream, is_combined=is_combined,
                               description=description)
        if ok:
            self._load_classes()
            return True, msg
        return False, msg

    def _on_edit_class(self, name, stream, cls_id=None,
                       is_combined=False, description=None):
        ok, msg = update_class(cls_id, name, stream, is_combined=is_combined,
                               description=description)
        if ok:
            self._load_classes()
            return True, msg
        return False, msg

    def _delete_class(self, cls):
        label = f"{cls['name']} {cls['stream']}".strip() if cls['stream'] else cls['name']
        ConfirmDialog(
            self,
            message=f"Delete '{label}'?\nAll enrolment data will be lost.",
            on_confirm=lambda: self._confirm_delete(cls["id"]),
        )

    def _confirm_delete(self, class_id):
        ok, msg = delete_class(class_id)
        if not ok:
            ErrorDialog(self, msg)
        self._load_classes()

    def _retire_class(self, cls):
        label = f"{cls['name']} {cls['stream']}".strip() if cls['stream'] else cls['name']
        RetireClassDialog(self, cls=cls, on_done=self._load_classes)

    def _end_of_year(self):
        PromotionWizard(self, on_done=self._load_classes)

    def _bulk_promote_dialog(self):
        BulkPromoteDialog(self, on_done=self._load_classes)

    # ── Subjects panel ────────────────────────────────────────
    def _build_subjects_panel(self):
        f = self._subjects_frame

        ctrl = ctk.CTkFrame(f, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 10))
        muted(ctrl, "Add, edit or deactivate subjects.").pack(side="left")
        primary_btn(ctrl, "+ Add subject",
                    command=self._add_subject, width=120).pack(side="right")

        tcard = card(f)
        tcard.pack(fill="both", expand=True)

        thead = ctk.CTkFrame(tcard, fg_color="#F3F4F6", corner_radius=0)
        thead.pack(fill="x", padx=1, pady=(1, 0))
        for col, w in [("Subject name", 240), ("Code", 80),
                        ("Status", 80), ("Actions", 180)]:
            ctk.CTkLabel(thead, text=col, font=("", 11, "bold"),
                         text_color=TEXT_MUTED, width=w,
                         anchor="w").pack(side="left", padx=(12, 0), pady=8)

        self._subjects_body = ctk.CTkScrollableFrame(
            tcard, fg_color=SURFACE, corner_radius=0)
        self._subjects_body.pack(fill="both", expand=True,
                                  padx=1, pady=(0, 1))

    def _load_subjects(self):
        for w in self._subjects_body.winfo_children():
            w.destroy()

        subjects = get_subjects()
        if not subjects:
            muted(self._subjects_body,
                  "No subjects yet.").pack(pady=24)
            return

        for i, s in enumerate(subjects):
            bg = SURFACE if i % 2 == 0 else "#FAFAFA"
            row = ctk.CTkFrame(self._subjects_body, fg_color=bg,
                               corner_radius=0, height=40)
            row.pack(fill="x")
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=s["name"], font=("", 12),
                         text_color=TEXT if s["is_active"] else TEXT_MUTED,
                         width=240, anchor="w").pack(side="left", padx=(12, 0))
            ctk.CTkLabel(row, text=s["code"] or "—",
                         font=("", 12), text_color=TEXT_MUTED,
                         width=80, anchor="w").pack(side="left", padx=(12, 0))

            status = "Active" if s["is_active"] else "Inactive"
            sc = SUCCESS if s["is_active"] else TEXT_MUTED
            ctk.CTkLabel(row, text=status, font=("", 12),
                         text_color=sc, width=80,
                         anchor="w").pack(side="left", padx=(12, 0))

            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(side="left", padx=8)

            ctk.CTkButton(actions, text="Edit", width=50, height=26,
                          fg_color="transparent", border_color=BORDER,
                          border_width=1, text_color=TEXT, corner_radius=6,
                          hover_color=BG, font=("", 11),
                          command=lambda sub=s: self._edit_subject(sub)
                          ).pack(side="left", padx=(0, 4))

            toggle_text = "Deactivate" if s["is_active"] else "Activate"
            toggle_fg   = DANGER if s["is_active"] else SUCCESS
            ctk.CTkButton(actions, text=toggle_text, width=80, height=26,
                          fg_color="transparent",
                          border_color=toggle_fg, border_width=1,
                          text_color=toggle_fg, corner_radius=6,
                          hover_color="#FEF2F2" if s["is_active"] else "#F0FDF4",
                          font=("", 11),
                          command=lambda sub=s: self._toggle_subject(sub)
                          ).pack(side="left", padx=(0, 4))

            ctk.CTkButton(actions, text="Delete", width=58, height=26,
                          fg_color="transparent", border_color=DANGER,
                          border_width=1, text_color=DANGER, corner_radius=6,
                          hover_color="#FEF2F2", font=("", 11),
                          command=lambda sub=s: self._delete_subject(sub)
                          ).pack(side="left")

    def _add_subject(self):
        SubjectForm(self, title="Add subject",
                    on_save=self._on_add_subject)

    def _edit_subject(self, sub):
        SubjectForm(self, title="Edit subject", subject=sub,
                    on_save=self._on_edit_subject)

    def _on_add_subject(self, name, code):
        ok, msg = create_subject(name, code)
        if ok:
            self._load_subjects()
        return ok, msg

    def _on_edit_subject(self, name, code, subject_id=None):
        ok, msg = update_subject(subject_id, name, code)
        if ok:
            self._load_subjects()
        return ok, msg

    def _toggle_subject(self, sub):
        toggle_subject_active(sub["id"])
        self._load_subjects()

    def _delete_subject(self, sub):
        ConfirmDialog(
            self,
            message=f"Delete '{sub['name']}'?\nThis cannot be undone.",
            on_confirm=lambda: self._confirm_delete_subject(sub["id"]),
        )

    def _confirm_delete_subject(self, subject_id):
        ok, msg = delete_subject(subject_id)
        if not ok:
            ErrorDialog(self, msg)
        self._load_subjects()


# ── Class form ────────────────────────────────────────────────
class ClassForm(ctk.CTkToplevel):
    def __init__(self, parent, title, on_save, cls=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("480x500")
        self.resizable(False, False)
        self.grab_set()
        self._on_save = on_save
        self._cls = cls
        self._build()

    def _build(self):
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(fill="both", expand=True)

        f = ctk.CTkFrame(outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=(24, 0))

        heading(f, self.title()).pack(anchor="w", pady=(0, 14))

        muted(f, "Class name  (e.g. Form 1, Grade 10, Form 4 Physics Combined)").pack(anchor="w")
        self._name = ctk.CTkEntry(f, width=370, fg_color=SURFACE, border_color=BORDER)
        self._name.pack(anchor="w", pady=(4, 14))

        muted(f, "Stream  (optional — leave blank for combined/single-stream classes)").pack(anchor="w")
        self._stream = ctk.CTkEntry(f, width=370, fg_color=SURFACE, border_color=BORDER,
                                     placeholder_text="Leave blank if no streams")
        self._stream.pack(anchor="w", pady=(4, 14))

        self._is_combined = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f,
            text="Combined class (optional subject — students from multiple streams)",
            variable=self._is_combined,
            font=("", 12), text_color=TEXT,
            fg_color=ACCENT, hover_color=ACCENT_DARK,
            command=self._toggle_desc,
        ).pack(anchor="w", pady=(0, 8))

        self._desc_frame = ctk.CTkFrame(f, fg_color="transparent")
        muted(self._desc_frame, "Description (e.g. Physics students from Form 4 A, B, C)").pack(anchor="w")
        self._desc = ctk.CTkEntry(self._desc_frame, width=370, fg_color=SURFACE,
                                   border_color=BORDER,
                                   placeholder_text="Optional note about this combined class")
        self._desc.pack(anchor="w", pady=(4, 0))

        if self._cls:
            self._name.insert(0, self._cls["name"])
            if self._cls.get("stream"):
                self._stream.insert(0, self._cls["stream"])
            if self._cls.get("is_combined"):
                self._is_combined.set(True)
                self._desc_frame.pack(anchor="w", fill="x", pady=(0, 8))
            if self._cls.get("description"):
                self._desc.insert(0, self._cls["description"])

        self._err = ctk.CTkLabel(f, text="", text_color=DANGER, font=("", 12))
        self._err.pack(anchor="w", pady=(8, 0))

        # Pinned footer
        btn_row = ctk.CTkFrame(outer, fg_color=SURFACE,
                               border_color=BORDER, border_width=1,
                               corner_radius=0, height=56)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)
        ghost_btn(btn_row, "Cancel", command=self.destroy,
                  width=100).pack(side="left", padx=20, pady=10)
        primary_btn(btn_row, "Save", command=self._submit,
                    width=100).pack(side="right", padx=20, pady=10)

    def _toggle_desc(self):
        if self._is_combined.get():
            self._desc_frame.pack(anchor="w", fill="x", pady=(0, 8),
                                   before=self._err)
        else:
            self._desc_frame.pack_forget()

    def _submit(self):
        name        = self._name.get().strip()
        stream      = self._stream.get().strip() or None
        is_combined = self._is_combined.get()
        desc        = self._desc.get().strip() or None
        if self._cls:
            ok, msg = self._on_save(name, stream, cls_id=self._cls["id"],
                                    is_combined=is_combined, description=desc)
        else:
            ok, msg = self._on_save(name, stream,
                                    is_combined=is_combined, description=desc)
        if ok:
            self.destroy()
        else:
            self._err.configure(text=msg)


# ── Subject form ──────────────────────────────────────────────
class SubjectForm(ctk.CTkToplevel):
    def __init__(self, parent, title, on_save, subject=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("440x340")
        self.resizable(False, False)
        self.grab_set()
        self._on_save = on_save
        self._subject = subject
        self._build()

    def _build(self):
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(fill="both", expand=True)

        f = ctk.CTkFrame(outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=(24, 0))

        heading(f, self.title()).pack(anchor="w", pady=(0, 16))

        muted(f, "Subject name *").pack(anchor="w")
        self._name = ctk.CTkEntry(f, width=350,
                                   fg_color=SURFACE, border_color=BORDER)
        self._name.pack(anchor="w", pady=(4, 14))

        muted(f, "Subject code (optional — e.g. MAT, ENG)").pack(anchor="w")
        self._code = ctk.CTkEntry(f, width=350,
                                   fg_color=SURFACE, border_color=BORDER)
        self._code.pack(anchor="w", pady=(4, 14))

        if self._subject:
            self._name.insert(0, self._subject["name"])
            if self._subject.get("code"):
                self._code.insert(0, self._subject["code"])

        self._err = ctk.CTkLabel(f, text="", text_color=DANGER, font=("", 12))
        self._err.pack(anchor="w")

        # Pinned footer
        btn_row = ctk.CTkFrame(outer, fg_color=SURFACE,
                               border_color=BORDER, border_width=1,
                               corner_radius=0, height=56)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)
        ghost_btn(btn_row, "Cancel", command=self.destroy,
                  width=100).pack(side="left", padx=20, pady=10)
        primary_btn(btn_row, "Save", command=self._submit,
                    width=100).pack(side="right", padx=20, pady=10)

    def _submit(self):
        name = self._name.get().strip()
        code = self._code.get().strip() or None
        if self._subject:
            ok, msg = self._on_save(name, code, subject_id=self._subject["id"])
        else:
            ok, msg = self._on_save(name, code)
        if ok:
            self.destroy()
        else:
            self._err.configure(text=msg)


# ── Bulk promote dialog ───────────────────────────────────────
class BulkPromoteDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_done):
        super().__init__(parent)
        self.title("Bulk promote students")
        self.geometry("500x320")
        self.resizable(False, False)
        self.grab_set()
        self._on_done = on_done
        self._classes = get_classes()
        self._build()

    def _build(self):
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(fill="both", expand=True)

        f = ctk.CTkFrame(outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=(24, 0))

        heading(f, "Bulk promote", size=16).pack(anchor="w", pady=(0, 4))
        muted(f, "Move all active students from one class to another.\n"
                 "Use this at the end of the year.").pack(
            anchor="w", pady=(0, 16))

        class_labels = [
            f"{c['name']}{' ' + c['stream'] if c['stream'] else ''}"
            for c in self._classes
        ]

        row1 = ctk.CTkFrame(f, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))
        muted(row1, "From:", size=12).pack(side="left", padx=(0, 8))
        self._from_var = ctk.StringVar(
            value=class_labels[0] if class_labels else "")
        ctk.CTkOptionMenu(row1, variable=self._from_var,
                          values=class_labels, width=200,
                          fg_color=SURFACE, button_color=BORDER,
                          text_color=TEXT,
                          dropdown_fg_color=SURFACE).pack(side="left")

        row2 = ctk.CTkFrame(f, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 16))
        muted(row2, "To:    ", size=12).pack(side="left", padx=(0, 8))
        self._to_var = ctk.StringVar(
            value=class_labels[1] if len(class_labels) > 1 else "")
        ctk.CTkOptionMenu(row2, variable=self._to_var,
                          values=class_labels, width=200,
                          fg_color=SURFACE, button_color=BORDER,
                          text_color=TEXT,
                          dropdown_fg_color=SURFACE).pack(side="left")

        self._msg = ctk.CTkLabel(f, text="", font=("", 12),
                                  text_color=DANGER)
        self._msg.pack(anchor="w", pady=(0, 8))

        # Pinned footer
        btn_row = ctk.CTkFrame(outer, fg_color=SURFACE,
                               border_color=BORDER, border_width=1,
                               corner_radius=0, height=56)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)
        ghost_btn(btn_row, "Cancel", command=self.destroy,
                  width=100).pack(side="left", padx=20, pady=10)
        primary_btn(btn_row, "Promote", command=self._submit,
                    width=100).pack(side="right", padx=20, pady=10)

    def _submit(self):
        from_label = self._from_var.get()
        to_label   = self._to_var.get()
        if from_label == to_label:
            self._msg.configure(text="'From' and 'To' must be different.")
            return
        from_cls = next((c for c in self._classes if
                         f"{c['name']}{' ' + c['stream'] if c['stream'] else ''}"
                         == from_label), None)
        to_cls   = next((c for c in self._classes if
                         f"{c['name']}{' ' + c['stream'] if c['stream'] else ''}"
                         == to_label), None)
        if not from_cls or not to_cls:
            self._msg.configure(text="Invalid selection.")
            return
        ok, msg = bulk_promote(from_cls["id"], to_cls["id"])
        if ok:
            self._msg.configure(text=msg, text_color=SUCCESS)
            self.after(1200, self.destroy)
            self.after(1200, self._on_done)
        else:
            self._msg.configure(text=msg, text_color=DANGER)


# ── Helpers ───────────────────────────────────────────────────
class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, message, on_confirm):
        super().__init__(parent)
        self.title("Confirm")
        self.geometry("460x200")
        self.resizable(False, False)
        self.grab_set()
        self._on_confirm = on_confirm
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(fill="both", expand=True)
        f = ctk.CTkFrame(outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=(24, 0))
        label(f, message, size=13).pack(anchor="w", pady=(0, 8))
        btn_row = ctk.CTkFrame(outer, fg_color=SURFACE,
                               border_color=BORDER, border_width=1,
                               corner_radius=0, height=56)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)
        ghost_btn(btn_row, "Cancel", command=self.destroy,
                  width=100).pack(side="left", padx=20, pady=10)
        ctk.CTkButton(btn_row, text="Confirm", width=100, height=36,
                      fg_color=DANGER, hover_color="#DC2626",
                      corner_radius=8,
                      command=lambda: [self._on_confirm(),
                                       self.destroy()]).pack(
            side="right", padx=20, pady=10)


class ErrorDialog(ctk.CTkToplevel):
    def __init__(self, parent, message):
        super().__init__(parent)
        self.title("Error")
        self.geometry("420x180")
        self.resizable(False, False)
        self.grab_set()
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(fill="both", expand=True)
        f = ctk.CTkFrame(outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=(24, 0))
        label(f, message, size=13, color=DANGER).pack(anchor="w", pady=(0, 8))
        btn_row = ctk.CTkFrame(outer, fg_color=SURFACE,
                               border_color=BORDER, border_width=1,
                               corner_radius=0, height=56)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)
        primary_btn(btn_row, "OK", command=self.destroy,
                    width=100).pack(side="right", padx=20, pady=10)


# ── Retire class dialog ───────────────────────────────────────
class RetireClassDialog(ctk.CTkToplevel):
    def __init__(self, parent, cls, on_done):
        super().__init__(parent)
        self.title("Retire class")
        self.geometry("600x360")
        self.resizable(False, False)
        self.grab_set()
        self._cls    = cls
        self._on_done = on_done
        self._build()

    def _build(self):
        from routes.classes import retire_class
        from db.connection import query_one

        self._outer = ctk.CTkFrame(self, fg_color=BG)
        self._outer.pack(fill="both", expand=True)

        f = ctk.CTkFrame(self._outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=(24, 0))

        cls_label = (f"{self._cls['name']} "
                     f"{self._cls['stream']}").strip() \
            if self._cls.get("stream") else self._cls["name"]

        heading(f, f"Retire  {cls_label}", size=16).pack(
            anchor="w", pady=(0, 4))

        count = query_one(
            "SELECT COUNT(*) AS n FROM students "
            "WHERE class_id=? AND status='active'",
            (self._cls["id"],)) or {}
        n = count.get("n", 0)

        muted(f, f"{n} active student(s) will be archived.").pack(
            anchor="w", pady=(0, 16))

        # Info card
        info = ctk.CTkFrame(f, fg_color="#FFFBEB",
                             border_color=WARNING, border_width=1,
                             corner_radius=8)
        info.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            info,
            text="Retiring archives all students in this class.\n"
                 "Their records and marks are preserved.\n"
                 "Choose whether to keep or remove the class itself.",
            font=("", 12), text_color="#92400E",
            justify="left",
        ).pack(padx=12, pady=10, anchor="w")

        self._msg = ctk.CTkLabel(f, text="", font=("", 12),
                                  text_color=SUCCESS)
        self._msg.pack(anchor="w", pady=(0, 8))

        # Pinned footer
        btn_row = ctk.CTkFrame(self._outer, fg_color=SURFACE,
                               border_color=BORDER, border_width=1,
                               corner_radius=0, height=56)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)

        ghost_btn(btn_row, "Cancel",
                  command=self.destroy, width=80).pack(
            side="left", padx=20, pady=10)

        ctk.CTkButton(
            btn_row,
            text="Archive students, keep class",
            width=200, height=36,
            fg_color=WARNING, hover_color="#D97706",
            corner_radius=8, font=("", 12),
            command=lambda: self._do("archive"),
        ).pack(side="right", padx=(8, 20), pady=10)

        ctk.CTkButton(
            btn_row,
            text="Archive & remove class",
            width=180, height=36,
            fg_color=DANGER, hover_color="#DC2626",
            corner_radius=8, font=("", 12),
            command=lambda: self._do("delete"),
        ).pack(side="right", pady=10)

    def _do(self, action):
        from routes.classes import retire_class
        ok, msg = retire_class(self._cls["id"], action)
        if ok:
            self._msg.configure(text=f"✓ {msg}", text_color=SUCCESS)
            self.after(1500, self.destroy)
            self.after(1500, self._on_done)
        else:
            self._msg.configure(text=msg, text_color=DANGER)
