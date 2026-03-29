import customtkinter as ctk
import os
import shutil
from PIL import Image as PILImage
from pathlib import Path
from tkinter import filedialog
from utils.theme import *
from routes.settings import get_setting, set_setting, get_all_settings
from routes.terms import get_current_term


# Store logo in ~/.gradevault/assets/
ASSETS_DIR = Path.home() / ".gradevault" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._build()
        self._load()

    def _build(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)

        heading(self, "School settings").pack(anchor="w", pady=(0, 20))

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        # ── School info card ─────────────────────────────────
        self._info_card = self._section(scroll, "School information")
        f = ctk.CTkFrame(self._info_card, fg_color="transparent")
        f.pack(fill="x", padx=20, pady=(0, 16))

        muted(f, "School name").pack(anchor="w")
        self._school_name = ctk.CTkEntry(
            f, width=400, fg_color=SURFACE, border_color=BORDER)
        self._school_name.pack(anchor="w", pady=(4, 12))

        muted(f, "Motto (optional)").pack(anchor="w")
        self._motto = ctk.CTkEntry(
            f, width=400, fg_color=SURFACE, border_color=BORDER)
        self._motto.pack(anchor="w", pady=(4, 12))

        muted(f, "Contact / address (optional)").pack(anchor="w")
        self._contact = ctk.CTkEntry(
            f, width=400, fg_color=SURFACE, border_color=BORDER,
            placeholder_text="e.g. P.O. Box 123, Meru  |  0712 345 678")
        self._contact.pack(anchor="w", pady=(4, 14))

        self._info_msg = ctk.CTkLabel(
            f, text="", font=("", 12), text_color=SUCCESS)
        self._info_msg.pack(anchor="w")
        primary_btn(f, "Save school info",
                    command=self._save_info, width=160).pack(
            anchor="w", pady=(8, 0))

        # ── Logo card ────────────────────────────────────────
        logo_card = self._section(scroll, "School logo / letterhead")
        lf = ctk.CTkFrame(logo_card, fg_color="transparent")
        lf.pack(fill="x", padx=20, pady=(0, 16))

        muted(lf,
              "Upload your school logo or letterhead image.\n"
              "It will appear at the top of all printed documents (class lists, report cards).\n"
              "Supported formats: PNG, JPG. Recommended: PNG with transparent background."
              ).pack(anchor="w", pady=(0, 12))

        # Logo preview
        self._logo_preview_frame = ctk.CTkFrame(
            lf, fg_color="#F3F4F6", corner_radius=8,
            width=320, height=100)
        self._logo_preview_frame.pack(anchor="w", pady=(0, 10))
        self._logo_preview_frame.pack_propagate(False)
        self._logo_status = ctk.CTkLabel(
            self._logo_preview_frame,
            text="No logo uploaded",
            font=("", 12), text_color=TEXT_MUTED)
        self._logo_status.place(relx=0.5, rely=0.5, anchor="center")

        btn_row = ctk.CTkFrame(lf, fg_color="transparent")
        btn_row.pack(anchor="w")
        primary_btn(btn_row, "Upload logo",
                    command=self._upload_logo, width=130).pack(side="left")
        ghost_btn(btn_row, "Remove logo",
                  command=self._remove_logo, width=120).pack(
            side="left", padx=(10, 0))

        self._logo_msg = ctk.CTkLabel(
            lf, text="", font=("", 12), text_color=SUCCESS)
        self._logo_msg.pack(anchor="w", pady=(8, 0))

        # ── Print header preview card ────────────────────────
        preview_card = self._section(scroll, "Print header preview")
        pf = ctk.CTkFrame(preview_card, fg_color="transparent")
        pf.pack(fill="x", padx=20, pady=(0, 16))

        muted(pf,
              "This is how your header will look on printed documents."
              ).pack(anchor="w", pady=(0, 10))

        self._preview_box = ctk.CTkFrame(
            pf, fg_color=SURFACE, border_color=BORDER,
            border_width=1, corner_radius=8)
        self._preview_box.pack(fill="x")

        self._preview_name = ctk.CTkLabel(
            self._preview_box, text="",
            font=("", 16, "bold"), text_color=ACCENT)
        self._preview_name.pack(pady=(14, 2))

        self._preview_motto = ctk.CTkLabel(
            self._preview_box, text="",
            font=("", 11), text_color=TEXT_MUTED)
        self._preview_motto.pack(pady=(0, 4))

        self._preview_contact = ctk.CTkLabel(
            self._preview_box, text="",
            font=("", 11), text_color=TEXT_MUTED)
        self._preview_contact.pack(pady=(0, 14))

    def _section(self, parent, title):
        c = card(parent)
        c.pack(fill="x", pady=(0, 16))
        hdr = ctk.CTkFrame(c, fg_color=ACCENT_BG, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=title, font=("", 13, "bold"),
                     text_color=ACCENT).pack(
            anchor="w", padx=16, pady=10)
        return c

    def _load(self):
        s = get_all_settings()
        name    = s.get("school_name", "")
        motto   = s.get("school_motto", "")
        contact = s.get("school_contact", "")
        logo    = s.get("school_logo", "")

        self._school_name.delete(0, "end")
        self._school_name.insert(0, name)
        self._motto.delete(0, "end")
        self._motto.insert(0, motto)
        self._contact.delete(0, "end")
        self._contact.insert(0, contact)

        self._update_preview(name, motto, contact)
        self._update_logo_status(logo)

    def _save_info(self):
        name    = self._school_name.get().strip()
        motto   = self._motto.get().strip()
        contact = self._contact.get().strip()

        if not name:
            self._info_msg.configure(
                text="School name is required.", text_color=DANGER)
            return

        set_setting("school_name",    name)
        set_setting("school_motto",   motto)
        set_setting("school_contact", contact)

        self._info_msg.configure(
            text="✓ Saved successfully.", text_color=SUCCESS)
        self._update_preview(name, motto, contact)
        self.after(2000, lambda: self._info_msg.configure(text=""))

    def _update_preview(self, name, motto, contact):
        self._preview_name.configure(text=name or "School name")
        self._preview_motto.configure(text=motto)
        self._preview_contact.configure(text=contact)

    def _upload_logo(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.PNG *.JPG")],
            title="Select school logo",
        )
        if not path:
            return

        # Copy to ~/.gradevault/assets/logo.ext
        ext = Path(path).suffix
        dest = ASSETS_DIR / f"school_logo{ext}"
        shutil.copy2(path, dest)
        set_setting("school_logo", str(dest))

        self._logo_msg.configure(
            text=f"✓ Logo uploaded: {Path(path).name}",
            text_color=SUCCESS)
        self._update_logo_status(str(dest))

    def _remove_logo(self):
        logo = get_setting("school_logo", "")
        if logo and Path(logo).exists():
            Path(logo).unlink()
        set_setting("school_logo", "")
        self._logo_msg.configure(
            text="Logo removed.", text_color=TEXT_MUTED)
        self._update_logo_status("")

    def _update_logo_status(self, logo_path):
        # Clear existing preview contents
        for w in self._logo_preview_frame.winfo_children():
            w.destroy()

        if logo_path and Path(logo_path).exists():
            try:
                pil_img = PILImage.open(logo_path)
                # Scale to fit preview frame (320x100)
                pil_img.thumbnail((300, 90), PILImage.LANCZOS)
                from customtkinter import CTkImage
                ctk_img = CTkImage(light_image=pil_img,
                                   dark_image=pil_img,
                                   size=(pil_img.width, pil_img.height))
                lbl = ctk.CTkLabel(self._logo_preview_frame,
                                   image=ctk_img, text="")
                lbl.image = ctk_img  # keep reference
                lbl.place(relx=0.5, rely=0.5, anchor="center")
                self._logo_preview_frame.configure(fg_color="#F0FDF4")
            except Exception as e:
                ctk.CTkLabel(self._logo_preview_frame,
                             text=f"✓ {Path(logo_path).name}",
                             font=("", 12), text_color=SUCCESS
                             ).place(relx=0.5, rely=0.5, anchor="center")
                self._logo_preview_frame.configure(fg_color="#F0FDF4")
        else:
            ctk.CTkLabel(self._logo_preview_frame,
                         text="No logo uploaded",
                         font=("", 12), text_color=TEXT_MUTED
                         ).place(relx=0.5, rely=0.5, anchor="center")
            self._logo_preview_frame.configure(fg_color="#F3F4F6")
