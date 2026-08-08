"""Zakładka 'Regały': podgląd i ręczna ingerencja w zakresy/kolejność regałów."""
from __future__ import annotations

import sqlite3

import customtkinter as ctk
from tkinter import messagebox

import database as db


class ShelvesFrame(ctk.CTkFrame):
    def __init__(self, master, on_change=None):
        super().__init__(master, fg_color="transparent")
        self.on_change = on_change
        self._row_widgets: list[dict] = []
        self._build()
        self.refresh()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20, 6))
        ctk.CTkLabel(top, text="Regały", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        actions = ctk.CTkFrame(top, fg_color="transparent")
        actions.pack(side="right")
        ctk.CTkButton(actions, text="Zapisz zmiany", command=self._save_all).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Przelicz automatyczne przydziały",
                       command=self._reassign).pack(side="left", padx=4)

        ctk.CTkLabel(
            self,
            text=("Duże łożyska (większa średnica zewnętrzna D) trafiają na regały o niższym poziomie, "
                  "małe - na regały o wyższym poziomie. Zakresy D możesz dowolnie zmieniać. "
                  "Łożyska przypisane ręcznie (w oknie edycji) nie są ruszane przy przeliczaniu."),
            wraplength=760, justify="left", text_color=("gray30", "gray70"),
        ).pack(fill="x", padx=20, pady=(0, 10))

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20)
        for text, w in (("Poziom", 70), ("Nazwa", 190), ("D od [mm]", 100),
                        ("D do [mm]", 100), ("Pozycje", 80), ("Sztuki", 80)):
            ctk.CTkLabel(header, text=text, width=w, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)

        self.rows_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.rows_container.pack(fill="both", expand=True, padx=20, pady=(4, 20))

    def refresh(self):
        for child in self.rows_container.winfo_children():
            child.destroy()
        self._row_widgets.clear()

        counts = db.shelf_counts()
        shelves = db.get_shelves()  # poziom malejąco (dół -> góra)
        for shelf in shelves:
            row = ctk.CTkFrame(self.rows_container, fg_color="transparent")
            row.pack(fill="x", pady=3)

            poziom_var = ctk.StringVar(value=str(shelf.poziom))
            nazwa_var = ctk.StringVar(value=shelf.nazwa)
            dmin_var = ctk.StringVar(value="" if shelf.d_min is None else f"{shelf.d_min:g}")
            dmax_var = ctk.StringVar(value="" if shelf.d_max is None else f"{shelf.d_max:g}")

            ctk.CTkEntry(row, textvariable=poziom_var, width=70).pack(side="left", padx=4)
            ctk.CTkEntry(row, textvariable=nazwa_var, width=190).pack(side="left", padx=4)
            ctk.CTkEntry(row, textvariable=dmin_var, width=100, placeholder_text="0").pack(side="left", padx=4)
            ctk.CTkEntry(row, textvariable=dmax_var, width=100, placeholder_text="bez limitu").pack(side="left", padx=4)

            pozycje, sztuki = counts.get(shelf.id, (0, 0))
            ctk.CTkLabel(row, text=str(pozycje), width=80).pack(side="left", padx=4)
            ctk.CTkLabel(row, text=str(sztuki), width=80).pack(side="left", padx=4)

            self._row_widgets.append({
                "id": shelf.id, "poziom": poziom_var, "nazwa": nazwa_var,
                "d_min": dmin_var, "d_max": dmax_var,
            })

    def _save_all(self):
        try:
            updates = []
            for w in self._row_widgets:
                poziom = int(w["poziom"].get())
                nazwa = w["nazwa"].get().strip() or f"Regał {poziom}"
                d_min = _parse(w["d_min"].get())
                d_max = _parse(w["d_max"].get())
                updates.append((w["id"], nazwa, poziom, d_min, d_max))
        except ValueError:
            messagebox.showwarning("Błędne dane", "Poziom oraz zakresy D muszą być liczbami.")
            return

        try:
            for shelf_id, nazwa, poziom, d_min, d_max in updates:
                db.update_shelf(shelf_id, nazwa, poziom, d_min, d_max)
        except sqlite3.IntegrityError:
            messagebox.showwarning("Konflikt poziomów", "Każdy regał musi mieć unikalny poziom.")
            return

        messagebox.showinfo("Zapisano", "Zmiany w regałach zostały zapisane.")
        self.refresh()
        if self.on_change:
            self.on_change()

    def _reassign(self):
        self._save_all()
        changed = db.reassign_all_auto()
        messagebox.showinfo("Przeliczono", f"Zaktualizowano przydział regału dla {changed} łożysk "
                                            f"(bez tych przypisanych ręcznie).")
        self.refresh()
        if self.on_change:
            self.on_change()


def _parse(text: str) -> float | None:
    text = text.strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        raise ValueError
