"""Okno dodawania / edycji łożyska."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

import database as db
import lookup
from bearing_data import SOURCE_OFFLINE, SOURCE_ONLINE, SOURCE_MANUAL

SOURCE_LABELS = {
    SOURCE_OFFLINE: ("baza offline (pewne)", "#2fa572"),
    SOURCE_ONLINE: ("internet (orientacyjne - zweryfikuj)", "#d19a2a"),
    SOURCE_MANUAL: ("wpisane ręcznie", "#8a8a8a"),
}


class BearingDialog(ctk.CTkToplevel):
    def __init__(self, master, on_saved, bearing: db.Bearing | None = None):
        super().__init__(master)
        self.on_saved = on_saved
        self.bearing = bearing
        self._zrodlo = bearing.zrodlo if bearing else SOURCE_MANUAL

        self.title("Edytuj łożysko" if bearing else "Dodaj łożysko")
        self.geometry("460x560")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        pad = {"padx": 20, "pady": (10, 0)}

        ctk.CTkLabel(self, text="Symbol łożyska", anchor="w").pack(fill="x", **pad)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(2, 0))
        self.symbol_var = ctk.StringVar(value=bearing.symbol if bearing else "")
        ctk.CTkEntry(row, textvariable=self.symbol_var, placeholder_text="np. 6008").pack(
            side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="Pobierz wymiary", width=140,
                       command=self._fetch_by_symbol).pack(side="left", padx=(8, 0))

        dims_row = ctk.CTkFrame(self, fg_color="transparent")
        dims_row.pack(fill="x", padx=20, pady=(14, 0))

        self.d_var = ctk.StringVar(value=_fmt(bearing.d) if bearing else "")
        self.D_var = ctk.StringVar(value=_fmt(bearing.D) if bearing else "")
        self.B_var = ctk.StringVar(value=_fmt(bearing.B) if bearing else "")

        for label, var in (("d wew. [mm]", self.d_var), ("D zew. [mm]", self.D_var), ("Wysokość B [mm]", self.B_var)):
            col = ctk.CTkFrame(dims_row, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True, padx=(0, 6))
            ctk.CTkLabel(col, text=label, anchor="w", font=ctk.CTkFont(size=11)).pack(fill="x")
            ctk.CTkEntry(col, textvariable=var).pack(fill="x")

        ctk.CTkButton(self, text="Znajdź symbol na podstawie wymiarów",
                       command=self._fetch_by_dimensions).pack(fill="x", padx=20, pady=(10, 0))

        self.source_label = ctk.CTkLabel(self, text=self._source_text(), anchor="w")
        self.source_label.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Ilość sztuk", anchor="w").pack(fill="x", **pad)
        self.ilosc_var = ctk.StringVar(value=str(bearing.ilosc) if bearing else "1")
        ctk.CTkEntry(self, textvariable=self.ilosc_var).pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Regał", anchor="w").pack(fill="x", **pad)
        shelf_row = ctk.CTkFrame(self, fg_color="transparent")
        shelf_row.pack(fill="x", padx=20)
        self.shelves = db.get_shelves()
        options = ["Auto (na podstawie średnicy D)"] + [self._shelf_label(s) for s in self.shelves]
        self.shelf_var = ctk.StringVar(value=self._initial_shelf_label())
        ctk.CTkOptionMenu(shelf_row, values=options, variable=self.shelf_var).pack(fill="x")

        ctk.CTkLabel(self, text="Uwagi", anchor="w").pack(fill="x", **pad)
        self.uwagi_var = ctk.StringVar(value=bearing.uwagi if bearing else "")
        ctk.CTkEntry(self, textvariable=self.uwagi_var).pack(fill="x", padx=20)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(btns, text="Anuluj", fg_color="transparent", border_width=1,
                       command=self.destroy).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(btns, text="Zapisz", command=self._save).pack(side="left", expand=True, fill="x", padx=(6, 0))

    def _shelf_label(self, s: db.Shelf) -> str:
        lo = "0" if s.d_min is None else f"{s.d_min:g}"
        hi = "∞" if s.d_max is None else f"{s.d_max:g}"
        return f"{s.nazwa} (poziom {s.poziom}, D: {lo}-{hi} mm)"

    def _initial_shelf_label(self) -> str:
        if self.bearing and self.bearing.reczny_przydzial and self.bearing.regal_id:
            for s in self.shelves:
                if s.id == self.bearing.regal_id:
                    return self._shelf_label(s)
        return "Auto (na podstawie średnicy D)"

    def _source_text(self) -> str:
        label, _ = SOURCE_LABELS.get(self._zrodlo, (self._zrodlo, "#8a8a8a"))
        return f"Źródło danych: {label}"

    def _fetch_by_symbol(self):
        symbol = self.symbol_var.get().strip()
        if not symbol:
            messagebox.showwarning("Brak symbolu", "Wpisz symbol łożyska, np. 6008.")
            return
        result = lookup.lookup_by_symbol(symbol)
        self.symbol_var.set(result.symbol or symbol)
        self._zrodlo = result.source
        if result.d is not None:
            self.d_var.set(_fmt(result.d))
            self.D_var.set(_fmt(result.D))
            self.B_var.set(_fmt(result.B))
        self.source_label.configure(text=self._source_text())
        if result.note:
            messagebox.showinfo("Wynik wyszukiwania", result.note)

    def _fetch_by_dimensions(self):
        d = _parse(self.d_var.get())
        D = _parse(self.D_var.get())
        B = _parse(self.B_var.get())
        if d is None and D is None and B is None:
            messagebox.showwarning("Brak danych", "Wpisz przynajmniej jeden wymiar (d, D lub B).")
            return
        candidates = lookup.lookup_by_dimensions(d, D, B)
        if candidates:
            symbol, bd, bD, bB = candidates[0]
            self.symbol_var.set(symbol)
            self.d_var.set(_fmt(bd))
            self.D_var.set(_fmt(bD))
            self.B_var.set(_fmt(bB))
            self._zrodlo = SOURCE_OFFLINE
            self.source_label.configure(text=self._source_text())
            if len(candidates) > 1:
                inne = ", ".join(c[0] for c in candidates[1:6])
                messagebox.showinfo("Znaleziono kilka pasujących",
                                     f"Wybrano {symbol}. Inne pasujące: {inne}")
            return

        online_symbol = lookup.online_lookup_by_dimensions(d, D, B)
        if online_symbol:
            self.symbol_var.set(online_symbol)
            self._zrodlo = SOURCE_ONLINE
            self.source_label.configure(text=self._source_text())
            messagebox.showinfo("Znaleziono w internecie",
                                 f"Propozycja symbolu: {online_symbol}. Zweryfikuj przed zapisem.")
        else:
            messagebox.showwarning("Brak wyników", "Nie znaleziono pasującego symbolu.")

    def _save(self):
        symbol = self.symbol_var.get().strip()
        if not symbol:
            messagebox.showwarning("Brak symbolu", "Symbol łożyska jest wymagany.")
            return
        d, D, B = _parse(self.d_var.get()), _parse(self.D_var.get()), _parse(self.B_var.get())
        try:
            ilosc = int(float(self.ilosc_var.get().replace(",", ".")))
        except ValueError:
            messagebox.showwarning("Błędna ilość", "Ilość musi być liczbą całkowitą.")
            return

        chosen = self.shelf_var.get()
        reczny = chosen != "Auto (na podstawie średnicy D)"
        regal_id = None
        if reczny:
            for s in self.shelves:
                if self._shelf_label(s) == chosen:
                    regal_id = s.id
                    break

        uwagi = self.uwagi_var.get().strip()

        if self.bearing:
            db.update_bearing(self.bearing.id, symbol, d, D, B, ilosc, self._zrodlo, uwagi, regal_id, reczny)
        else:
            db.add_bearing(symbol, d, D, B, ilosc, self._zrodlo, uwagi, regal_id, reczny)

        self.on_saved()
        self.destroy()


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:g}"


def _parse(text: str) -> float | None:
    text = text.strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None
