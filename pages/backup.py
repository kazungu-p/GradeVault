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
        self._build_online_backup(scroll)
        self._build_auto_backups(scroll)

    # ── Current database info ─────────────────────────────────
    def _build_db_info(self, parent):
        sec = self._section(parent, "Current database")
        f   = ctk.CTkFrame(sec, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=(14, 16))

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
        warn.pack(fill="x", pady=(12, 14))
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

    # ── Online backup ─────────────────────────────────────────
    def _build_online_backup(self, parent):
        sec = self._section(parent, "Online backup (Google Drive)")
        f   = ctk.CTkFrame(sec, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=(0, 16))

        muted(f,
              "Upload a backup directly to your Google Drive.\nRequires a one-time sign-in — your data stays in your own account."
              ).pack(anchor="w", pady=(0, 8))

        # Google verification note
        warn = ctk.CTkFrame(f, fg_color="#FEF3C7",
                             border_color="#FCD34D", border_width=1,
                             corner_radius=8)
        warn.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(warn,
                     text="⚠  Google shows a warning screen the first time:\n"
                          "'GradeVault has not completed verification.'\n"
                          "Click Advanced → Go to GradeVault (unsafe) to proceed.\n"
                          "This is normal for apps in development / not yet submitted for review.",
                     font=("", 11), text_color="#92400E",
                     justify="left").pack(padx=12, pady=8, anchor="w")

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x")

        primary_btn(btn_row, "Upload to Google Drive",
                    command=self._upload_to_drive, width=200
                    ).pack(side="left")

        self._online_status = ctk.CTkLabel(
            f, text="", font=("", 12), text_color=TEXT_MUTED,
            wraplength=500, justify="left")
        self._online_status.pack(anchor="w", pady=(10, 0))

    def _upload_to_drive(self):
        self._online_status.configure(
            text="Checking dependencies…", text_color=TEXT_MUTED)
        self.update()
        try:
            import importlib
            for pkg in ("google.oauth2", "googleapiclient"):
                if importlib.util.find_spec(pkg.split(".")[0]) is None:
                    raise ImportError(pkg)
        except ImportError:
            self._online_status.configure(
                text="Required packages not installed.\n"
                     "Run: pip install google-auth google-auth-oauthlib "
                     "google-auth-httplib2 google-api-python-client",
                text_color=DANGER)
            return
        GoogleDriveUploadDialog(self, self._online_status)

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
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(fill="both", expand=True)

        f = ctk.CTkFrame(outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=(24, 0))

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
        ).pack(anchor="w", pady=(0, 12))

        # Pinned footer
        btn_row = ctk.CTkFrame(outer, fg_color=SURFACE,
                               border_color=BORDER, border_width=1,
                               corner_radius=0, height=56)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)
        ghost_btn(btn_row, "Cancel", command=self.destroy,
                  width=100).pack(side="left", padx=20, pady=10)
        ctk.CTkButton(
            btn_row, text="Yes, restore",
            width=120, height=36,
            fg_color=DANGER, hover_color="#DC2626",
            corner_radius=8, font=("", 13),
            command=lambda: [self.destroy(), self._on_confirm()],
        ).pack(side="right", padx=20, pady=10)


# ── Google Drive upload dialog ────────────────────────────────
class GoogleDriveUploadDialog(ctk.CTkToplevel):
    """
    Handles OAuth2 sign-in and upload to Google Drive.
    Uses google-auth + google-api-python-client.
    Install: pip install google-auth google-auth-oauthlib
             google-auth-httplib2 google-api-python-client
    """
    SCOPES     = ["https://www.googleapis.com/auth/drive.file"]
    TOKEN_FILE = str(
        __import__("pathlib").Path.home() / ".gradevault" / "gdrive_token.json"
    )

    def __init__(self, parent, status_label):
        super().__init__(parent)
        self.title("Upload to Google Drive")
        self.geometry("480x320")
        self.resizable(False, False)
        self.grab_set()
        self._status_lbl = status_label
        self._build()
        self.after(200, self._start_auth)

    def _build(self):
        outer = ctk.CTkFrame(self, fg_color=BG)
        outer.pack(fill="both", expand=True)

        f = ctk.CTkFrame(outer, fg_color=BG)
        f.pack(fill="both", expand=True, padx=28, pady=(24, 0))

        heading(f, "Google Drive backup", size=15).pack(
            anchor="w", pady=(0, 8))

        self._info = ctk.CTkLabel(
            f,
            text="A browser window will open for you to sign in\n"
                 "to your Google account. GradeVault only gets\n"
                 "permission to upload files — nothing else.",
            font=("", 12), text_color=TEXT_MUTED,
            justify="left")
        self._info.pack(anchor="w", pady=(0, 16))

        self._progress = ctk.CTkLabel(
            f, text="Waiting for sign-in…",
            font=("", 12), text_color=TEXT_MUTED)
        self._progress.pack(anchor="w", pady=(0, 12))

        self._bar = ctk.CTkProgressBar(f, width=400, mode="indeterminate")
        self._bar.pack(anchor="w", pady=(0, 8))
        self._bar.start()

        # Pinned footer
        btn_row = ctk.CTkFrame(outer, fg_color=SURFACE,
                               border_color=BORDER, border_width=1,
                               corner_radius=0, height=56)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)
        ghost_btn(btn_row, "Cancel", command=self.destroy,
                  width=100).pack(side="right", padx=20, pady=10)

    def _start_auth(self):
        import threading
        threading.Thread(target=self._auth_and_upload, daemon=True).start()

    def _auth_and_upload(self):
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            import json, os
            from pathlib import Path

            creds = None
            token_path = Path(self.TOKEN_FILE)

            if token_path.exists():
                creds = Credentials.from_authorized_user_file(
                    str(token_path), self.SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Need client secrets — use a built-in app credentials
                    import os as _os
                    # Search in order: next to main.py → cwd → ~/.gradevault
                    _candidates = [
                        Path(__file__).parent.parent / "client_secrets.json",
                        Path(_os.getcwd()) / "client_secrets.json",
                        Path.home() / ".gradevault" / "client_secrets.json",
                    ]
                    secrets = next((p for p in _candidates if p.exists()), None)
                    if not secrets:
                        checked = "\n".join(f"  {p}" for p in _candidates)
                        self._set_status(
                            f"client_secrets.json not found.\nSearched:\n{checked}",
                            DANGER)
                        return

                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(secrets), self.SCOPES)
                    self._set_status(
                        "Browser opened — please sign in…", TEXT_MUTED)
                    creds = flow.run_local_server(port=0)

                token_path.parent.mkdir(parents=True, exist_ok=True)
                token_path.write_text(creds.to_json())

            # Create backup file
            self._set_status("Creating backup…", TEXT_MUTED)
            ok, bak_path = backup()
            if not ok:
                self._set_status(f"Backup failed: {bak_path}", DANGER)
                return

            # Upload
            self._set_status("Uploading to Google Drive…", TEXT_MUTED)
            service   = build("drive", "v3", credentials=creds)
            file_name = os.path.basename(bak_path)
            media     = MediaFileUpload(bak_path, mimetype="application/octet-stream")
            uploaded  = service.files().create(
                body={"name": file_name},
                media_body=media, fields="id,name").execute()

            self._set_status(
                f"✓ Uploaded: {uploaded['name']}", SUCCESS)
            self._bar.stop()
            try:
                self._status_lbl.configure(
                    text=f"✓ Uploaded to Google Drive: {uploaded['name']}",
                    text_color=SUCCESS)
            except Exception:
                pass
            self.after(2000, self.destroy)

        except Exception as e:
            self._set_status(f"Error: {e}", DANGER)
            self._bar.stop()

    def _set_status(self, msg, color=None):
        try:
            self._progress.configure(
                text=msg,
                text_color=color or TEXT_MUTED)
        except Exception:
            pass
