"""
Magazyn Łożysk - aplikacja do klasyfikacji łożysk na 9 regałach.

Uruchomienie:
    python app.py
"""
from __future__ import annotations

import customtkinter as ctk
from tkinter import ttk

import database as db
from ui_bearings import BearingsFrame
from ui_shelves import ShelvesFrame

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Magazyn Łożysk")
        self.geometry("1180x720")
        self.minsize(980, 600)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()
        self._show_bearings()

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="⚙ Magazyn\nŁożysk", font=ctk.CTkFont(size=20, weight="bold"),
                     justify="left").pack(padx=20, pady=(24, 30), anchor="w")

        self.nav_bearings = ctk.CTkButton(sidebar, text="🔩  Łożyska", anchor="w",
                                           command=self._show_bearings)
        self.nav_bearings.pack(fill="x", padx=16, pady=4)

        self.nav_shelves = ctk.CTkButton(sidebar, text="🗄  Regały", anchor="w",
                                          command=self._show_shelves)
        self.nav_shelves.pack(fill="x", padx=16, pady=4)

        bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=20)
        ctk.CTkLabel(bottom, text="Wygląd", anchor="w", font=ctk.CTkFont(size=11)).pack(fill="x")
        ctk.CTkOptionMenu(bottom, values=["Dark", "Light", "System"],
                           command=self._change_appearance).pack(fill="x", pady=(4, 0))

    def _build_content(self):
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.bearings_frame = BearingsFrame(self.content)
        self.shelves_frame = ShelvesFrame(self.content, on_change=self._on_shelves_changed)

    def _show_bearings(self):
        self.shelves_frame.grid_forget()
        self.bearings_frame.grid(row=0, column=0, sticky="nsew")
        self.bearings_frame.refresh()
        self._highlight_nav(self.nav_bearings)

    def _show_shelves(self):
        self.bearings_frame.grid_forget()
        self.shelves_frame.grid(row=0, column=0, sticky="nsew")
        self.shelves_frame.refresh()
        self._highlight_nav(self.nav_shelves)

    def _highlight_nav(self, active_btn):
        for btn in (self.nav_bearings, self.nav_shelves):
            btn.configure(fg_color=("#3b8ed0" if btn is active_btn else "transparent"))

    def _on_shelves_changed(self):
        self.bearings_frame.refresh()

    def _change_appearance(self, mode: str):
        ctk.set_appearance_mode(mode)
        self.after(50, lambda: self.bearings_frame._style_treeview(ttk.Style()))


def main():
    db.init_db()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
