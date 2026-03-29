import customtkinter as ctk
from utils.theme import *
from routes.settings import get_setting
import time
import threading


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent, on_ready, duration=2.5):
        super().__init__(parent)
        self._on_ready  = on_ready
        self._duration  = duration
        self.overrideredirect(True)   # no title bar
        self.resizable(False, False)

        # Centre on screen
        w, h = 420, 280
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(fg_color=ACCENT)
        self.lift()
        self.attributes('-topmost', True)

        self._build()
        self._animate()

    def _build(self):
        # Logo box
        logo = ctk.CTkFrame(self, width=64, height=64,
                             fg_color="white", corner_radius=16)
        logo.pack(pady=(44, 0))
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="GV", font=("", 26, "bold"),
                     text_color=ACCENT).place(relx=0.5, rely=0.5,
                                               anchor="center")

        ctk.CTkLabel(self, text="GradeVault",
                     font=("", 26, "bold"),
                     text_color="white").pack(pady=(14, 2))

        school = get_setting("school_name", "")
        if school:
            ctk.CTkLabel(self, text=school,
                         font=("", 13),
                         text_color="#C7D2FE").pack()

        self._status = ctk.CTkLabel(
            self, text="Starting up…",
            font=("", 11), text_color="#A5B4FC")
        self._status.pack(pady=(28, 0))

        # Progress bar
        self._bar = ctk.CTkProgressBar(
            self, width=260, height=4,
            fg_color="#6366F1",
            progress_color="white",
            corner_radius=2)
        self._bar.set(0)
        self._bar.pack(pady=(10, 0))

    def _animate(self):
        messages = [
            (0.0,  "Starting up…"),
            (0.25, "Loading database…"),
            (0.55, "Preparing modules…"),
            (0.80, f"Welcome to GradeVault 👋"),
            (1.0,  "Ready!"),
        ]
        start = time.time()
        dur   = self._duration

        def tick():
            elapsed  = time.time() - start
            progress = min(elapsed / dur, 1.0)
            self._bar.set(progress)

            # Update message
            msg = messages[0][1]
            for threshold, text in messages:
                if progress >= threshold:
                    msg = text
            self._status.configure(text=msg)

            if progress < 1.0:
                self.after(40, tick)
            else:
                self.after(300, self._finish)

        self.after(40, tick)

    def _finish(self):
        self.destroy()
        self._on_ready()
