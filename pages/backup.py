import customtkinter as ctk
import os
from tkinter import filedialog
from utils.theme import *
from utils.backup import (
    backup, restore, validate_backup,
    list_auto_backups, get_db_info, BAK_EXT,
)


class BackupPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._build()

    def _build(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)
        heading(self, "Backup & Restore").pack(anchor="w", pady=(0, 16))

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        self._build_db_info(scroll)
        self._build_backup(scroll)
        self._build_restore(scroll)
        self._build_auto_backups(scroll)

    # ── Current database info ─────────────────────────────────
    def _build_db_info(self, parent):
        sec = self._section(parent, "Current database")
        f   = ctk.CTkFrame(sec, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=(0, 16))

        info = get_db_info()
        if not info:
            muted(f, "No database found.").pack(anchor="w")
            return

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x")
        row.columnconfigure((0, 1, 2, 3), weight=1, uniform="s")

        for col, (lbl, val) in enumerate([
            ("Students",    str(info.get("students", 0))),
            ("Classes",     str(info.get("classes",  0))),
            ("Marks saved", str(info.get("marks",    0))),
            ("DB size",     f"{info.get('size_kb', 0)} KB"),
        ]):
            c = ctk.CTkFrame(row, fg_color=SURFACE,
                             border_color=BORDER, border_width=1,
                             corner_radius=8)
            c.grid(row=0, column=col,
                   padx=(0, 10) if col < 3 else 0, sticky="ew")
            inner = ctk.CTkFrame(c, fg_color="transparent")
            inner.pack(padx=14, pady=(20, 16), fill="both", expand=True)
            muted(inner, lbl, size=11).pack(anchor="center")
            label(inner, val, size=22, weight="bold").pack(anchor="center")

        muted(f, f"Location: {info.get('path', '—')}"
              ).pack(anchor="w", pady=(10, 0))

    # ── Backup ────────────────────────────────────────────────
    def _build_backup(self, parent):
        sec = self._section(parent, "Create backup")
        f   = ctk.CTkFrame(sec, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=(0, 16))

        muted(f,
              "Saves a complete copy of your database including all students,\n"
              "marks, classes and settings. Keep backups in a safe place."
              ).pack(anchor="w", pady=(0, 14))

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x")

        primary_btn(btn_row, "Save backup to file…",
                    command=self._do_backup_save, width=180
                    ).pack(side="left", padx=(0, 10))

        ghost_btn(btn_row, "Quick backup (auto-named)",
                  command=self._do_backup_auto, width=200
                  ).pack(side="left")

        self._backup_status = ctk.CTkLabel(
            f, text="", font=("", 12), text_color=TEXT_MUTED)
        self._backup_status.pack(anchor="w", pady=(10, 0))

    def _do_backup_save(self):
        from datetime import datetime
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=BAK_EXT,
            filetypes=[("GradeVault backup", f"*{BAK_EXT}"),
                       ("All files", "*.*")],
            initialfile=f"gradevault_backup_{ts}{BAK_EXT}",
            title="Save backup as",
        )
        if not path:
            return
        self._run_backup(path)

    def _do_backup_auto(self):
        self._run_backup(None)

    def _run_backup(self, path):
        self._backup_status.configure(
            text="Creating backup…", text_color=TEXT_MUTED)
        self.update()
        ok, msg = backup(path)
        if ok:
            short = os.path.basename(msg)
            self._backup_status.configure(
                text=f"✓ Backup saved: {short}",
                text_color=SUCCESS)
            self._refresh_auto_list()
        else:
            self._backup_status.configure(
                text=msg, text_color=DANGER)

    # ── Restore ───────────────────────────────────────────────
    def _build_restore(self, parent):
        sec = self._section(parent, "Restore from backup")
        f   = ctk.CTkFrame(sec, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=(0, 16))

        # Warning box
        warn = ctk.CTkFrame(f, fg_color="#FEF3C7",
                             border_color="#FCD34D", border_width=1,
                             corner_radius=8)
        warn.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            warn,
            text="⚠  Restoring will REPLACE your current database.\n"
                 "Your current data will be automatically backed up first.",
            font=("", 12), text_color="#92400E",
            justify="left",
        ).pack(padx=14, pady=10, anchor="w")

        muted(f, "Choose a .gvbak file to restore from:"
              ).pack(anchor="w", pady=(0, 8))

        file_row = ctk.CTkFrame(f, fg_color="transparent")
        file_row.pack(fill="x")
        self._restore_path_lbl = muted(file_row, "No file selected")
        self._restore_path_lbl.pack(side="left", expand=True, anchor="w")
        ghost_btn(file_row, "Choose file…",
                  command=self._pick_restore_file, width=120
                  ).pack(side="right")

        self._restore_btn = ctk.CTkButton(
            f, text="Restore now",
            width=140, height=38,
            fg_color=DANGER, hover_color="#DC2626",
            corner_radius=8, font=("", 13),
            state="disabled",
            command=self._do_restore,
        )
        self._restore_btn.pack(anchor="w", pady=(12, 0))

        self._restore_status = ctk.CTkLabel(
            f, text="", font=("", 12), text_color=TEXT_MUTED,
            wraplength=500, justify="left")
        self._restore_status.pack(anchor="w", pady=(8, 0))

        self._restore_file = None

    def _pick_restore_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("GradeVault backup", f"*{BAK_EXT}"),
                       ("SQLite database", "*.db"),
                       ("All files", "*.*")],
            title="Select backup file",
        )
        if not path:
            return
        self._restore_file = path
        self._restore_path_lbl.configure(
            text=os.path.basename(path))

        # Validate immediately
        ok, msg = validate_backup(path)
        if ok:
            self._restore_status.configure(
                text=f"✓ Valid backup.", text_color=SUCCESS)
            self._restore_btn.configure(state="normal")
        else:
            self._restore_status.configure(
                text=f"✗ {msg}", text_color=DANGER)
            self._restore_btn.configure(state="disabled")

    def _do_restore(self):
        if not self._restore_file:
            return
        # Confirm dialog
        RestoreConfirmDialog(
            self,
            path=self._restore_file,
            on_confirm=self._run_restore,
        )

    def _run_restore(self):
        self._restore_status.configure(
            text="Restoring…", text_color=TEXT_MUTED)
        self.update()
        ok, msg = restore(self._restore_file)
        if ok:
            self._restore_status.configure(
                text=f"✓ {msg}", text_color=SUCCESS)
            self._restore_btn.configure(state="disabled")
            self._refresh_db_info()
        else:
            self._restore_status.configure(
                text=f"✗ {msg}", text_color=DANGER)

    # ── Auto backups list ─────────────────────────────────────
    def _build_auto_backups(self, parent):
        sec = self._section(parent, "Recent auto-backups")
        self._auto_frame = ctk.CTkFrame(sec, fg_color="transparent")
        self._auto_frame.pack(fill="x", padx=16, pady=(0, 16))
        self._render_auto_list()

    def _render_auto_list(self):
        for w in self._auto_frame.winfo_children():
            w.destroy()

        baks = list_auto_backups()
        if not baks:
            muted(self._auto_frame,
                  "No auto-backups yet. They appear here after quick backups "
                  "and pre-restore safety copies."
                  ).pack(anchor="w")
            return

        # Header
        thead = ctk.CTkFrame(self._auto_frame, fg_color="#F3F4F6",
                             corner_radius=6)
        thead.pack(fill="x", pady=(0, 4))
        for txt, w in [("Filename", 280), ("Date", 160),
                        ("Size", 80), ("Actions", 180)]:
            ctk.CTkLabel(thead, text=txt, font=("", 11, "bold"),
                         text_color=TEXT_MUTED, width=w,
                         anchor="w").pack(
                side="left", padx=(10, 0), pady=6)

        for i, bak in enumerate(baks[:10]):  # show latest 10
            bg = SURFACE if i % 2 == 0 else "#FAFAFA"
            row = ctk.CTkFrame(self._auto_frame, fg_color=bg,
                               corner_radius=0, height=36)
            row.pack(fill="x")
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=bak["name"], font=("", 11),
                         text_color=TEXT, width=280,
                         anchor="w").pack(
                side="left", padx=(10, 0))
            ctk.CTkLabel(row, text=bak["modified"], font=("", 11),
                         text_color=TEXT_MUTED, width=160,
                         anchor="w").pack(side="left", padx=(10, 0))
            ctk.CTkLabel(row, text=f"{bak['size_kb']} KB",
                         font=("", 11), text_color=TEXT_MUTED,
                         width=80, anchor="w").pack(
                side="left", padx=(10, 0))

            acts = ctk.CTkFrame(row, fg_color="transparent")
            acts.pack(side="left", padx=6)

            ghost_btn(acts, "Restore",
                      command=lambda p=bak["path"]: self._restore_from_list(p),
                      width=80).pack(side="left", padx=(0, 6))

            ghost_btn(acts, "Delete",
                      command=lambda p=bak["path"]: self._delete_backup(p),
                      width=70).pack(side="left")

        if len(baks) > 10:
            muted(self._auto_frame,
                  f"  … {len(baks)-10} older backup(s) not shown."
                  ).pack(anchor="w", pady=(4, 0))

    def _restore_from_list(self, path):
        self._restore_file = path
        self._restore_path_lbl.configure(
            text=os.path.basename(path))
        ok, msg = validate_backup(path)
        if ok:
            self._restore_status.configure(
                text="✓ Valid backup.", text_color=SUCCESS)
            self._restore_btn.configure(state="normal")
            RestoreConfirmDialog(self, path=path,
                                 on_confirm=self._run_restore)
        else:
            self._restore_status.configure(
                text=f"✗ {msg}", text_color=DANGER)

    def _delete_backup(self, path):
        import os as _os
        try:
            _os.remove(path)
            self._refresh_auto_list()
        except Exception as e:
            pass

    # ── Helpers ───────────────────────────────────────────────
    def _refresh_auto_list(self):
        self._render_auto_list()

    def _refresh_db_info(self):
        # Rebuild the whole page to reflect restored data
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def _section(self, parent, title):
        c = card(parent)
        c.pack(fill="x", pady=(0, 14))
        hdr = ctk.CTkFrame(c, fg_color=ACCENT_BG, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=title, font=("", 13, "bold"),
                     text_color=ACCENT).pack(
            anchor="w", padx=16, pady=10)
        return c


# ── Restore confirmation dialog ───────────────────────────────
class RestoreConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, path, on_confirm):
        super().__init__(parent)
        self.title("Confirm restore")
        self.geometry("460x240")
        self.resizable(False, False)
        self.grab_set()
        self._path       = path
        self._on_confirm = on_confirm
        self._build()

    def _build(self):
        f = ctk.CTkFrame(self, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=28)

        heading(f, "Restore database?", size=15).pack(
            anchor="w", pady=(0, 8))

        ctk.CTkLabel(
            f,
            text=f"File: {os.path.basename(self._path)}\n\n"
                 "This will replace ALL current data.\n"
                 "A safety backup of your current database will be\n"
                 "created automatically before restoring.",
            font=("", 12), text_color=TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", pady=(0, 20))

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x")
        ghost_btn(btn_row, "Cancel", command=self.destroy,
                  width=100).pack(side="left")
        ctk.CTkButton(
            btn_row, text="Yes, restore",
            width=120, height=38,
            fg_color=DANGER, hover_color="#DC2626",
            corner_radius=8, font=("", 13),
            command=lambda: [self.destroy(), self._on_confirm()],
        ).pack(side="right")
