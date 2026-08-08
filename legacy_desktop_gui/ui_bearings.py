"""Zakładka 'Łożyska': tabela, wyszukiwanie, dodawanie/edycja/usuwanie."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import ttk, messagebox

import database as db
from ui_dialogs import BearingDialog

COLUMNS = ("symbol", "d", "D", "B", "ilosc", "regal", "zrodlo", "uwagi")
HEADINGS = {
    "symbol": "Symbol", "d": "d [mm]", "D": "D [mm]", "B": "B [mm]",
    "ilosc": "Ilość", "regal": "Regał", "zrodlo": "Źródło", "uwagi": "Uwagi",
}
ZRODLO_LABELS = {"offline": "baza offline", "internet": "internet", "recznie": "ręcznie"}


class BearingsFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._shelves_by_id: dict[int, db.Shelf] = {}
        self._build()
        self.refresh()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(top, text="Łożyska", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        actions = ctk.CTkFrame(top, fg_color="transparent")
        actions.pack(side="right")
        ctk.CTkButton(actions, text="+ Dodaj łożysko", command=self._add).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Edytuj", command=self._edit).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Usuń", fg_color="#b3392c", hover_color="#8c2c22",
                       command=self._delete).pack(side="left", padx=4)

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.pack(fill="x", padx=20, pady=(0, 10))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ctk.CTkEntry(search_row, textvariable=self.search_var,
                      placeholder_text="Szukaj po symbolu...").pack(fill="x")

        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        style = ttk.Style()
        self._style_treeview(style)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", style="Bearings.Treeview")
        for col in COLUMNS:
            self.tree.heading(col, text=HEADINGS[col])
            width = 90 if col not in ("symbol", "uwagi") else 130
            self.tree.column(col, width=width, anchor="center" if col != "uwagi" else "w")
        self.tree.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        self.tree.bind("<Double-1>", lambda e: self._edit())

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def _style_treeview(self, style: ttk.Style):
        dark = ctk.get_appearance_mode() == "Dark"
        bg = "#2b2b2b" if dark else "#f2f2f2"
        fg = "#e6e6e6" if dark else "#1a1a1a"
        heading_bg = "#212121" if dark else "#dcdcdc"
        style.theme_use("clam")
        style.configure("Bearings.Treeview", background=bg, foreground=fg, fieldbackground=bg,
                         rowheight=28, font=("Segoe UI", 11), borderwidth=0)
        style.configure("Bearings.Treeview.Heading", background=heading_bg, foreground=fg,
                         font=("Segoe UI", 11, "bold"), borderwidth=0)
        style.map("Bearings.Treeview", background=[("selected", "#1f6aa5")], foreground=[("selected", "white")])

    def refresh(self):
        self._shelves_by_id = {s.id: s for s in db.get_shelves()}
        for row in self.tree.get_children():
            self.tree.delete(row)
        for b in db.get_bearings(self.search_var.get().strip()):
            regal = self._shelves_by_id.get(b.regal_id)
            regal_text = regal.nazwa if regal else "—"
            if b.reczny_przydzial:
                regal_text += " (ręcznie)"
            self.tree.insert("", "end", iid=str(b.id), values=(
                b.symbol, _fmt(b.d), _fmt(b.D), _fmt(b.B), b.ilosc,
                regal_text, ZRODLO_LABELS.get(b.zrodlo, b.zrodlo), b.uwagi,
            ))

    def _selected_id(self) -> int | None:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _add(self):
        BearingDialog(self, on_saved=self.refresh)

    def _edit(self):
        bearing_id = self._selected_id()
        if bearing_id is None:
            messagebox.showinfo("Wybierz łożysko", "Zaznacz łożysko w tabeli, aby je edytować.")
            return
        bearing = db.get_bearing(bearing_id)
        BearingDialog(self, on_saved=self.refresh, bearing=bearing)

    def _delete(self):
        bearing_id = self._selected_id()
        if bearing_id is None:
            messagebox.showinfo("Wybierz łożysko", "Zaznacz łożysko w tabeli, aby je usunąć.")
            return
        bearing = db.get_bearing(bearing_id)
        if messagebox.askyesno("Potwierdź usunięcie", f"Usunąć łożysko {bearing.symbol}?"):
            db.delete_bearing(bearing_id)
            self.refresh()


def _fmt(value: float | None) -> str:
    return "" if value is None else f"{value:g}"
