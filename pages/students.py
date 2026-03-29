import customtkinter as ctk
import os
from tkinter import filedialog
from utils.importer import read_students_from_file, sample_csv_template
from utils.theme import *
from utils.pdf_classlist import generate_class_list
from routes.students import (
    get_students, get_classes, create_student,
    update_student, transfer_student, archive_student,
)


class StudentsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._students = []
        self._classes = []
        self._build()
        self._load()

    # ── Layout ───────────────────────────────────────────────
    def _build(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)

        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        heading(header, "Students").pack(side="left")
        primary_btn(header, "+ Add student",
                    command=self._open_add_form,
                    width=130).pack(side="right")
        ghost_btn(header, "Print class list",
                  command=self._print_class_list,
                  width=140).pack(side="right", padx=(0, 8))
        ghost_btn(header, "Import CSV/Excel",
                  command=self._open_import,
                  width=130).pack(side="right", padx=(0, 8))

        # Search + filter row
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 10))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._load())
        search = ctk.CTkEntry(controls, placeholder_text="Search by name or admission no.",
                              textvariable=self._search_var, width=260,
                              border_color=BORDER, fg_color=SURFACE)
        search.pack(side="left", padx=(0, 10))

        self._class_var = ctk.StringVar(value="All classes")
        self._class_filter = ctk.CTkOptionMenu(
            controls, variable=self._class_var,
            values=["All classes"],
            command=lambda _: self._load(),
            width=160, fg_color=SURFACE,
            button_color=BORDER, button_hover_color=BORDER,
            text_color=TEXT, dropdown_fg_color=SURFACE,
        )
        self._class_filter.pack(side="left", padx=(0, 10))

        self._status_var = ctk.StringVar(value="Active")
        ctk.CTkOptionMenu(
            controls, variable=self._status_var,
            values=["Active", "Archived"],
            command=lambda _: self._load(),
            width=110, fg_color=SURFACE,
            button_color=BORDER, button_hover_color=BORDER,
            text_color=TEXT, dropdown_fg_color=SURFACE,
        ).pack(side="left")

        self._count_label = muted(controls, "")
        self._count_label.pack(side="right")

        # Table card
        table_card = card(self)
        table_card.pack(fill="both", expand=True)

        # Table header
        thead = ctk.CTkFrame(table_card, fg_color="#F3F4F6", corner_radius=0)
        thead.pack(fill="x", padx=1, pady=(1, 0))

        cols = [
            ("Admission no.", 120),
            ("Full name",     220),
            ("Class",          80),
            ("Stream",         60),
            ("Gender",         60),
            ("Actions",       160),
        ]
        for col_name, col_w in cols:
            ctk.CTkLabel(thead, text=col_name, font=("", 11, "bold"),
                         text_color=TEXT_MUTED, width=col_w,
                         anchor="w").pack(side="left", padx=(12, 0), pady=8)

        # Scrollable body
        self._body = ctk.CTkScrollableFrame(table_card, fg_color=SURFACE,
                                             corner_radius=0)
        self._body.pack(fill="both", expand=True, padx=1, pady=(0, 1))

    # ── Data ─────────────────────────────────────────────────
    def _load(self):
        search = self._search_var.get().strip()
        status = "active" if self._status_var.get() == "Active" else "archived"

        # Resolve class filter
        class_id = None
        if self._class_var.get() != "All classes":
            match = next((c for c in self._classes
                          if f"{c['name']} {c['stream']}" == self._class_var.get()), None)
            if match:
                class_id = match["id"]

        self._classes = get_classes()
        class_labels = ["All classes"] + [f"{c['name']} {c['stream']}"
                                           for c in self._classes]
        self._class_filter.configure(values=class_labels)

        self._students = get_students(search=search, class_id=class_id, status=status)
        self._count_label.configure(text=f"{len(self._students)} student(s)")
        self._render_rows()

    def _render_rows(self):
        for w in self._body.winfo_children():
            w.destroy()

        if not self._students:
            muted(self._body, "No students found.").pack(pady=24)
            return

        for i, s in enumerate(self._students):
            bg = SURFACE if i % 2 == 0 else "#FAFAFA"
            row = ctk.CTkFrame(self._body, fg_color=bg, corner_radius=0, height=40)
            row.pack(fill="x")
            row.pack_propagate(False)

            def _cell(text, width, color=TEXT):
                ctk.CTkLabel(row, text=str(text), font=("", 12),
                             text_color=color, width=width,
                             anchor="w").pack(side="left", padx=(12, 0))

            _cell(s["admission_number"], 120)
            _cell(s["full_name"],        220)
            _cell(s.get("class_name", "—"), 80)
            _cell(s.get("stream", "—"),     60)
            _cell(s.get("gender") or "—",   60)

            # Action buttons
            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(side="left", padx=8)

            ctk.CTkButton(actions, text="Edit", width=50, height=26,
                          fg_color="transparent", border_color=BORDER,
                          border_width=1, text_color=TEXT, corner_radius=6,
                          hover_color=BG, font=("", 11),
                          command=lambda st=s: self._open_edit_form(st)
                          ).pack(side="left", padx=(0, 4))

            ctk.CTkButton(actions, text="Transfer", width=64, height=26,
                          fg_color="transparent", border_color=BORDER,
                          border_width=1, text_color=TEXT, corner_radius=6,
                          hover_color=BG, font=("", 11),
                          command=lambda st=s: self._open_transfer(st)
                          ).pack(side="left", padx=(0, 4))

            if s.get("status") == "active":
                ctk.CTkButton(actions, text="Archive", width=60, height=26,
                              fg_color="transparent", border_color=DANGER,
                              border_width=1, text_color=DANGER, corner_radius=6,
                              hover_color="#FEF2F2", font=("", 11),
                              command=lambda st=s: self._do_archive(st)
                              ).pack(side="left")

    # ── Import ───────────────────────────────────────────────
    def _open_import(self):
        ImportDialog(self, classes=self._classes, on_done=self._load)

    # ── Print ────────────────────────────────────────────────
    def _print_class_list(self):
        PrintClassListDialog(self, classes=self._classes)

    # ── Forms ─────────────────────────────────────────────────
    def _open_add_form(self):
        StudentForm(self, title="Add student", classes=self._classes,
                    on_save=self._on_save_new)

    def _open_edit_form(self, student):
        StudentForm(self, title="Edit student", classes=self._classes,
                    student=student, on_save=self._on_save_edit)

    def _open_transfer(self, student):
        TransferDialog(self, student=student, classes=self._classes,
                       on_save=self._on_transfer)

    def _on_save_new(self, data):
        ok, msg = create_student(
            data["full_name"], data["admission_number"],
            data["class_id"], data.get("gender"),
        )
        return ok, msg

    def _on_save_edit(self, data):
        ok, msg = update_student(
            data["student_id"], data["full_name"],
            data["admission_number"], data["class_id"],
            data.get("gender"),
        )
        return ok, msg

    def _on_transfer(self, student_id, class_id):
        transfer_student(student_id, class_id)
        self._load()

    def _do_archive(self, student):
        ConfirmDialog(
            self,
            message=f"Archive {student['full_name']}? They will be hidden from active lists.",
            on_confirm=lambda: self._confirm_archive(student["id"]),
        )

    def _confirm_archive(self, student_id):
        archive_student(student_id)
        self._load()


# ── Student form (add / edit) ─────────────────────────────────
class StudentForm(ctk.CTkToplevel):
    def __init__(self, parent, title, classes, on_save, student=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("460x500")
        self.resizable(False, False)
        self.grab_set()
        self._classes = classes
        self._on_save = on_save
        self._student = student
        self._build()
        if student:
            self._populate(student)

    def _build(self):
        f = ctk.CTkFrame(self, fg_color=BG)
        f.pack(fill="both", expand=True, padx=36, pady=32)

        heading(f, self.title()).pack(anchor="w", pady=(0, 16))

        # Full name
        muted(f, "Full name").pack(anchor="w")
        self._name = ctk.CTkEntry(f, width=360, fg_color=SURFACE, border_color=BORDER)
        self._name.pack(pady=(4, 14))

        # Admission number
        muted(f, "Admission number").pack(anchor="w")
        self._adm = ctk.CTkEntry(f, width=360, fg_color=SURFACE, border_color=BORDER)
        self._adm.pack(pady=(4, 14))

        # Class
        muted(f, "Class & stream").pack(anchor="w")
        self._class_labels = [f"{c['name']} {c['stream']}" for c in self._classes]
        self._class_var = ctk.StringVar(value=self._class_labels[0] if self._class_labels else "")
        ctk.CTkOptionMenu(f, variable=self._class_var,
                          values=self._class_labels, width=360,
                          fg_color=SURFACE, button_color=BORDER,
                          button_hover_color=ACCENT, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          ).pack(pady=(4, 14))

        # Gender
        muted(f, "Gender (optional)").pack(anchor="w")
        self._gender_var = ctk.StringVar(value="—")
        ctk.CTkOptionMenu(f, variable=self._gender_var,
                          values=["—", "M", "F"], width=360,
                          fg_color=SURFACE, button_color=BORDER,
                          button_hover_color=ACCENT, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          ).pack(pady=(4, 14))

        self._error = ctk.CTkLabel(f, text="", text_color=DANGER, font=("", 12))
        self._error.pack()

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x", pady=(8, 0))
        ghost_btn(btn_row, "Cancel", command=self.destroy, width=100).pack(side="left")
        primary_btn(btn_row, "Save", command=self._submit, width=100).pack(side="right")

    def _populate(self, s):
        self._name.insert(0, s["full_name"])
        self._adm.insert(0, s["admission_number"])
        if s.get("gender"):
            self._gender_var.set(s["gender"])
        class_label = f"{s.get('class_name', '')} {s.get('stream', '')}".strip()
        if class_label in self._class_labels:
            self._class_var.set(class_label)

    def _submit(self):
        self._error.configure(text="")
        name = self._name.get().strip()
        adm  = self._adm.get().strip()
        gender = self._gender_var.get()
        gender = None if gender == "—" else gender

        class_label = self._class_var.get()
        match = next((c for c in self._classes
                      if f"{c['name']} {c['stream']}" == class_label), None)
        if not match:
            self._error.configure(text="Please select a valid class.")
            return

        data = {
            "full_name": name, "admission_number": adm,
            "class_id": match["id"], "gender": gender,
        }
        if self._student:
            data["student_id"] = self._student["id"]

        ok, msg = self._on_save(data)
        if ok:
            self.destroy()
            # Reload parent
            self.master._load()
        else:
            self._error.configure(text=msg)


# ── Transfer dialog ───────────────────────────────────────────
class TransferDialog(ctk.CTkToplevel):
    def __init__(self, parent, student, classes, on_save):
        super().__init__(parent)
        self.title("Transfer student")
        self.geometry("480x280")
        self.resizable(False, False)
        self.grab_set()
        self._student = student
        self._classes = classes
        self._on_save = on_save
        self._build()

    def _build(self):
        f = ctk.CTkFrame(self, fg_color=BG)
        f.pack(fill="both", expand=True, padx=36, pady=32)

        heading(f, "Transfer student", size=16).pack(anchor="w", pady=(0, 4))
        muted(f, f"Moving: {self._student['full_name']}").pack(anchor="w", pady=(0, 16))

        muted(f, "New class & stream").pack(anchor="w")
        self._class_labels = [f"{c['name']} {c['stream']}" for c in self._classes]
        self._class_var = ctk.StringVar(value=self._class_labels[0] if self._class_labels else "")
        ctk.CTkOptionMenu(f, variable=self._class_var,
                          values=self._class_labels, width=310,
                          fg_color=SURFACE, button_color=BORDER,
                          button_hover_color=ACCENT, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          ).pack(pady=(2, 16))

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x")
        ghost_btn(btn_row, "Cancel", command=self.destroy, width=100).pack(side="left")
        primary_btn(btn_row, "Transfer", command=self._submit, width=100).pack(side="right")

    def _submit(self):
        class_label = self._class_var.get()
        match = next((c for c in self._classes
                      if f"{c['name']} {c['stream']}" == class_label), None)
        if match:
            self._on_save(self._student["id"], match["id"])
            self.destroy()


# ── Confirm dialog ────────────────────────────────────────────
class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, message, on_confirm):
        super().__init__(parent)
        self.title("Confirm")
        self.geometry("480x210")
        self.resizable(False, False)
        self.grab_set()
        self._on_confirm = on_confirm
        self._build(message)

    def _build(self, message):
        f = ctk.CTkFrame(self, fg_color=BG)
        f.pack(fill="both", expand=True, padx=36, pady=32)

        label(f, message, size=13).pack(anchor="w", pady=(0, 20))

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x")
        ghost_btn(btn_row, "Cancel", command=self.destroy, width=100).pack(side="left")
        ctk.CTkButton(btn_row, text="Confirm", width=100, height=38,
                      fg_color=DANGER, hover_color="#DC2626",
                      corner_radius=8,
                      command=self._confirm).pack(side="right")

    def _confirm(self):
        self._on_confirm()
        self.destroy()


# ── Print class list dialog ───────────────────────────────────
class PrintClassListDialog(ctk.CTkToplevel):
    def __init__(self, parent, classes):
        super().__init__(parent)
        self.title("Print class list")
        self.geometry("480x280")
        self.resizable(False, False)
        self.grab_set()
        self._classes = classes
        self._build()

    def _build(self):
        f = ctk.CTkFrame(self, fg_color=BG)
        f.pack(fill="both", expand=True, padx=36, pady=32)

        heading(f, "Print class list", size=16).pack(anchor="w", pady=(0, 16))

        muted(f, "Select class").pack(anchor="w")
        class_labels = ["All classes"] + [f"{c['name']} {c['stream']}"
                                           for c in self._classes]
        self._class_var = ctk.StringVar(value="All classes")
        ctk.CTkOptionMenu(f, variable=self._class_var,
                          values=class_labels, width=330,
                          fg_color=SURFACE, button_color=BORDER,
                          button_hover_color=ACCENT, text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          ).pack(pady=(2, 16))

        self._status = muted(f, "")
        self._status.pack(anchor="w", pady=(0, 8))

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x")
        ghost_btn(btn_row, "Cancel", command=self.destroy, width=100).pack(side="left")
        primary_btn(btn_row, "Generate PDF", command=self._generate, width=130).pack(side="right")

    def _generate(self):
        import os
        from tkinter import filedialog
        from utils.pdf_classlist import generate_class_list

        sel = self._class_var.get()
        class_id = None
        if sel != "All classes":
            match = next((c for c in self._classes
                          if f"{c['name']} {c['stream']}" == sel), None)
            if match:
                class_id = match["id"]

        default_name = f"classlist_{sel.replace(' ', '_')}.pdf"
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=default_name,
            title="Save class list as",
        )
        if not path:
            return

        self._status.configure(text="Generating PDF...")
        self.update()

        try:
            generate_class_list(path, class_id=class_id)
            self._status.configure(text=f"Saved to {os.path.basename(path)}")
            # Open the PDF automatically
            os.system(f'open "{path}"' if os.name != "nt"
                      else f'start "" "{path}"')
            self.after(1500, self.destroy)
        except Exception as e:
            self._status.configure(text=f"Error: {e}")


# ── Import dialog ─────────────────────────────────────────────
class ImportDialog(ctk.CTkToplevel):
    def __init__(self, parent, classes, on_done):
        super().__init__(parent)
        self.title("Import students from CSV / Excel")
        self.geometry("560x520")
        self.resizable(False, False)
        self.grab_set()
        self._classes = classes
        self._on_done = on_done
        self._rows    = []
        self._build()

    def _build(self):
        f = ctk.CTkFrame(self, fg_color=BG)
        f.pack(fill="both", expand=True, padx=36, pady=32)

        heading(f, "Import students", size=16).pack(anchor="w", pady=(0, 4))
        muted(f, "Upload a CSV or Excel file with student data.").pack(
            anchor="w", pady=(0, 2))

        # Template hint
        hint = ctk.CTkFrame(f, fg_color=ACCENT_BG, corner_radius=6)
        hint.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            hint,
            text="Required columns:  full_name  |  admission_number  |  gender (optional)",
            font=("", 11), text_color=ACCENT,
        ).pack(padx=10, pady=6, anchor="w")

        # Download template button
        ghost_btn(f, "Download template CSV",
                  command=self._download_template,
                  width=180).pack(anchor="w", pady=(0, 12))

        # Class selector
        muted(f, "Assign imported students to class:").pack(anchor="w")
        class_labels = [
            f"{c['name']}{' ' + c['stream'] if c['stream'] else ''}"
            for c in self._classes
        ]
        self._class_var = ctk.StringVar(
            value=class_labels[0] if class_labels else "")
        ctk.CTkOptionMenu(f, variable=self._class_var,
                          values=class_labels if class_labels else ["—"],
                          width=300,
                          fg_color=SURFACE, button_color=BORDER,
                          text_color=TEXT,
                          dropdown_fg_color=SURFACE,
                          ).pack(anchor="w", pady=(4, 14))

        # File picker
        file_row = ctk.CTkFrame(f, fg_color="transparent")
        file_row.pack(fill="x", pady=(0, 8))
        self._file_label = muted(file_row, "No file selected")
        self._file_label.pack(side="left", expand=True, anchor="w")
        ghost_btn(file_row, "Choose file",
                  command=self._pick_file, width=110).pack(side="right")

        # Preview area
        self._preview = ctk.CTkTextbox(
            f, width=460, height=100,
            fg_color=SURFACE, border_color=BORDER,
            font=("", 11), state="disabled")
        self._preview.pack(pady=(0, 8))

        self._status = ctk.CTkLabel(f, text="", font=("", 12),
                                     text_color=TEXT_MUTED)
        self._status.pack(anchor="w", pady=(0, 8))

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x")
        ghost_btn(btn_row, "Cancel",
                  command=self.destroy, width=100).pack(side="left")
        self._import_btn = primary_btn(
            btn_row, "Import students",
            command=self._do_import, width=140)
        self._import_btn.pack(side="right")
        self._import_btn.configure(state="disabled")

    def _download_template(self):
        from utils.importer import sample_csv_template
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="students_template.csv",
            title="Save template as",
        )
        if path:
            with open(path, "w") as fh:
                fh.write(sample_csv_template())
            self._status.configure(
                text=f"Template saved to {os.path.basename(path)}",
                text_color=SUCCESS)

    def _pick_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV / Excel", "*.csv *.xlsx *.xls")],
            title="Select student file",
        )
        if not path:
            return
        self._file_label.configure(text=os.path.basename(path))
        rows, err = read_students_from_file(path)
        self._rows = rows

        self._preview.configure(state="normal")
        self._preview.delete("1.0", "end")

        if rows:
            preview_lines = [
                f"{r['admission_number']}  |  {r['full_name']}  |  {r.get('gender') or '—'}"
                for r in rows[:8]
            ]
            if len(rows) > 8:
                preview_lines.append(f"... and {len(rows) - 8} more rows")
            self._preview.insert("1.0", "\n".join(preview_lines))
            self._import_btn.configure(state="normal")
            msg = f"{len(rows)} student(s) ready to import."
            if err:
                msg += f"\nWarnings:\n{err}"
            self._status.configure(text=msg, text_color=TEXT_MUTED)
        else:
            self._preview.insert("1.0", err or "No valid rows found.")
            self._import_btn.configure(state="disabled")
            self._status.configure(text="Fix the file and try again.",
                                   text_color=DANGER)

        self._preview.configure(state="disabled")

    def _do_import(self):
        if not self._rows:
            return

        cls_label = self._class_var.get()
        cls = next((c for c in self._classes if
                    f"{c['name']}{' ' + c['stream'] if c['stream'] else ''}"
                    == cls_label), None)
        if not cls:
            self._status.configure(text="Select a valid class first.",
                                   text_color=DANGER)
            return

        from routes.students import create_student
        success, skipped = 0, 0
        for r in self._rows:
            ok, _ = create_student(
                r["full_name"], r["admission_number"],
                cls["id"], r.get("gender"),
            )
            if ok:
                success += 1
            else:
                skipped += 1

        msg = f"✓ Imported {success} student(s)."
        if skipped:
            msg += f"  {skipped} skipped (duplicate admission numbers)."
        self._status.configure(text=msg, text_color=SUCCESS)
        self._import_btn.configure(state="disabled")
        self.after(1800, self.destroy)
        self.after(1800, self._on_done)
