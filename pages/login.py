import customtkinter as ctk
from utils.theme import *
from routes.auth import login


class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, on_success):
        super().__init__(parent, fg_color=BG)
        self.on_success = on_success
        self._build()

    def _build(self):
        self.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Centre card
        card_frame = card(self, width=360)
        card_frame.place(relx=0.5, rely=0.5, anchor="center")
        card_frame.grid_propagate(False)

        inner = ctk.CTkFrame(card_frame, fg_color="transparent")
        inner.pack(padx=32, pady=32, fill="both", expand=True)

        # Logo row
        logo_box = ctk.CTkFrame(inner, width=36, height=36,
                                 fg_color=ACCENT, corner_radius=8)
        logo_box.pack_propagate(False)
        logo_box.pack(pady=(0, 4))
        ctk.CTkLabel(logo_box, text="GV", text_color="white",
                     font=("", 14, "bold")).place(relx=0.5, rely=0.5, anchor="center")

        heading(inner, "GradeVault", size=22).pack(pady=(6, 2))
        muted(inner, "School administration system", size=12).pack(pady=(0, 20))

        # Fields
        ctk.CTkLabel(inner, text="Username", font=("", 12),
                     text_color=TEXT_MUTED, anchor="w").pack(fill="x")
        self.username = entry(inner, placeholder="e.g. admin", width=296)
        self.username.pack(pady=(2, 10))
        self.username.focus()

        ctk.CTkLabel(inner, text="Password", font=("", 12),
                     text_color=TEXT_MUTED, anchor="w").pack(fill="x")
        self.password = entry(inner, placeholder="••••••••", show="•", width=296)
        self.password.pack(pady=(2, 6))
        self.password.bind("<Return>", lambda e: self._attempt())

        self.error_label = ctk.CTkLabel(inner, text="", text_color=DANGER,
                                        font=("", 12))
        self.error_label.pack(pady=(0, 8))

        primary_btn(inner, "Sign in", command=self._attempt, width=296).pack()

    def _attempt(self):
        self.error_label.configure(text="")
        user = login(self.username.get().strip(), self.password.get())
        if user:
            self.place_forget()
            self.on_success(user)
        else:
            self.error_label.configure(text="Invalid username or password.")
