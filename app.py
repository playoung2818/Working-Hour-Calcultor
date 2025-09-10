# app.py
import os, sys, math
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
from typing import Any, Dict
from labour_data import LABOUR_MAP, all_part_numbers


# ---------- Helpers ----------
def resource_path(relative_path: str) -> str:
    """Absolute path to resource; works in dev and PyInstaller .exe."""
    try:
        base_path = sys._MEIPASS  # set by PyInstaller
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def _num(x: Any, default: float = 0.0) -> float:
    """Coerce to float; blank/NaN/invalid -> default."""
    try:
        if x is None:
            return default
        if isinstance(x, float) and x != x:  # NaN
            return default
        s = str(x).strip()
        if s in ("", "...", "nan", "None"):
            return default
        return float(s)
    except Exception:
        return default


# ---------- Core calculator ----------
def calc_working_hours_single(
    part_number: str,
    units_in_workorder: float,
    assemble: bool,
    gpu_flag: bool,
    labour_map: Dict[str, Dict[str, Any]],
):
    """
    Excel-equivalent:
      ((B*IF(C,K,L) + IF(D>0,B*N,0) + B*O + P + IF(B<J,2,CEIL(B/J,0)*2)) / 100) * 8
    Where:
      B=units_in_workorder, C=assemble, D=gpu_flag,
      K=buildpoints, L=testonlypoints, J=unitsinabox, N=gpu, O=sop, P=extra
    Returns integer hours.
    """
    pn_key = str(part_number).strip().upper()
    cfg = labour_map.get(pn_key)
    if not cfg:
        return "Oha"

    B = _num(units_in_workorder, 0.0)
    if B < 0:
        B = 0.0

    K = _num(cfg.get("buildpoints"))
    L = _num(cfg.get("testonlypoints"))
    J = _num(cfg.get("unitsinabox"))
    N = _num(cfg.get("gpu"))
    O = _num(cfg.get("sop"))     # SOP always applied
    P = _num(cfg.get("extra"))

    term1 = B * (K if assemble else L)
    term2 = (B * N) if gpu_flag else 0.0
    term3 = B * O
    term4 = P
    term5 = 2.0 if J <= 0 or B < J else math.ceil(B / J) * 2.0

    expr = term1 + term2 + term3 + term4 + term5
    hours = (expr / 100.0) * 8.0
    return round(hours)  


# ---------- GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WO Working Hours Calculator")
        self.geometry("420x240")
        self.resizable(True, True)

        # set icon (works in dev & frozen exe)
        try:
            self.iconbitmap(resource_path("Calculator.ico"))
        except Exception:
            pass

        # Shared fonts that we can resize dynamically
        self.base_font = tkFont.Font(family="Segoe UI", size=12)
        self.result_font = tkFont.Font(family="Segoe UI", size=14, weight="bold")

        # ttk styles bound to those fonts
        style = ttk.Style(self)
        style.configure("App.TLabel",       font=self.base_font)
        style.configure("App.TButton",      font=self.base_font)
        style.configure("App.TCheckbutton", font=self.base_font)
        style.configure("App.TEntry",       font=self.base_font)
        style.configure("App.TCombobox",    font=self.base_font)

        # Make Combobox dropdown list use the same font
        self.option_add("*TCombobox*Listbox.font", self.base_font)

        # Layout: make right column expand nicely
        self.columnconfigure(1, weight=1)

        # --- Part Number ---
        ttk.Label(self, text="Part Number", style="App.TLabel").grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )
        self.pn_var = tk.StringVar()
        self.pn_combo = ttk.Combobox(
            self, textvariable=self.pn_var, width=48,
            style="App.TCombobox", values=all_part_numbers()
        )
        self.pn_combo.grid(row=0, column=1, padx=12, pady=12, sticky="ew")
        pn_values = all_part_numbers()
        if pn_values:
            self.pn_combo.set(pn_values[0])

        # --- Units ---
        ttk.Label(self, text="Units in Work Order", style="App.TLabel").grid(
            row=1, column=0, padx=12, pady=12, sticky="w"
        )
        self.units_var = tk.StringVar(value="1")
        self.units_entry = ttk.Entry(
            self, textvariable=self.units_var, width=12, style="App.TEntry"
        )
        self.units_entry.grid(row=1, column=1, padx=12, pady=12, sticky="w")

        # --- Flags ---
        self.assemble_var = tk.BooleanVar(value=True)
        self.gpu_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self, text="Assemble", variable=self.assemble_var, style="App.TCheckbutton"
        ).grid(row=2, column=0, padx=12, pady=8, sticky="w")
        ttk.Checkbutton(
            self, text="GPU", variable=self.gpu_var, style="App.TCheckbutton"
        ).grid(row=2, column=1, padx=12, pady=8, sticky="w")

        # --- Calculate button ---
        self.calc_btn = ttk.Button(
            self, text="Calculate", command=self.calculate, style="App.TButton"
        )
        self.calc_btn.grid(row=3, column=0, columnspan=2, padx=12, pady=16)

        # --- Result ---
        self.result_label = ttk.Label(
            self, text="Hours: --", style="App.TLabel", font=self.result_font
        )
        self.result_label.grid(row=4, column=0, columnspan=2, padx=12, pady=12)

        # Resize binding (fonts scale with window width)
        self.bind("<Configure>", self.on_resize)

    def on_resize(self, event):
        new_size = max(10, event.width // 50)   # adjust divisor to taste
        self.base_font.configure(size=new_size)
        self.result_font.configure(size=new_size + 2)

    def calculate(self):
        pn = self.pn_var.get().strip()
        try:
            units = float(self.units_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Input", "Units must be a number.")
            return
        assemble = self.assemble_var.get()
        gpu_flag = self.gpu_var.get()

        hours = calc_working_hours_single(
            part_number=pn,
            units_in_workorder=units,
            assemble=assemble,
            gpu_flag=gpu_flag,
            labour_map=LABOUR_MAP,
        )
        self.result_label.config(text=f"Hours: {hours}")


if __name__ == "__main__":
    App().mainloop()

