import json
import os
import tkinter as tk
from tkinter import messagebox

from UI.components.Header import Header
from UI.styles.desk_theme import (
    BG_MAIN,
    BG_CARD,
    BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    FONT_NORMAL,
    FONT_BOLD
)


class SpotConstructionScreen(tk.Frame):
    def __init__(self, master, controller=None):
        super().__init__(master, bg=BG_MAIN)
        self.controller = controller
        self.pack(fill="both", expand=True)

        self.create_widgets()

    # ================= UI =================

    def create_widgets(self):
        # ── HEADER (FIJO) ──
        Header(
            parent=self,
            title="Desglose Spot",
            on_back=self.go_back
        )

        # ── CONTENEDOR SCROLL ──
        container = tk.Frame(self, bg=BG_MAIN)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            container,
            bg=BG_MAIN,
            highlightthickness=0
        )
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(
            container,
            orient="vertical",
            command=canvas.yview
        )
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        # Frame REAL donde va todo el contenido
        self.scrollable_frame = tk.Frame(canvas, bg=BG_MAIN)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )

        # Scroll con rueda (macOS friendly)
        canvas.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        )

        # ── CARGA DE CONTENIDO ──
        self.load_spot_content()

    # ================= DATA LOAD =================

    def load_spot_content(self):
        scp_id = getattr(self.controller, "active_scp_id", None)
        if not scp_id:
            messagebox.showwarning("Sin datos", "No hay ningún SCP activo.")
            return

        spot_path = os.path.join(
            os.getcwd(),
            "resources",
            "scp",
            "spot_construction",
            f"{scp_id}.json"
        )

        if not os.path.exists(spot_path):
            messagebox.showwarning(
                "Sin desglose",
                "No se encontró el desglose Spot para este SCP."
            )
            return

        with open(spot_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.render_spot_card(data)
        self.render_rungs_table(
            rungs=data["rungs"],
            ccy_pair=data["context"]["ccyPair"]
        )

    # ================= CONTEXT CARD =================

    def render_spot_card(self, data):
        wrapper = tk.Frame(self.scrollable_frame, bg=BG_MAIN)
        wrapper.pack(fill="x", pady=36)

        card = tk.Frame(
            wrapper,
            bg=BG_CARD,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        card.pack(anchor="center")

        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="both", expand=True, padx=28, pady=22)

        row = tk.Frame(inner, bg=BG_CARD)
        row.pack(fill="x")

        self.column(
            row,
            "Context",
            [
                f"CCY Pair:  {data['context']['ccyPair']}",
                f"Venue:  {data['context']['venue']}",
                f"Group:  {data['context']['group'] or '-'}",
                f"SM Type:  {data['context']['smType']}",
                f"Pricing Model:  {data['context']['prcModel']}",
                f"Price Competition:  {data['context']['priceCompetition']}",
            ]
        )

        self.column(
            row,
            "Client",
            [
                f"Venue Client ID:  {data['client']['venueClientId'] or '-'}",
                f"Venue Account ID:  {data['client']['venueAccountId'] or '-'}",
                f"Venue User ID:  {data['client']['venueUserId'] or '-'}",
            ]
        )

        self.column(
            row,
            "Notional",
            [
                f"Amount:  {data['notional']['amount']}",
                f"Side:  {data['notional']['side']}",
            ]
        )

    def column(self, parent, title, lines):
        col = tk.Frame(parent, bg=BG_CARD)
        col.pack(side="left", expand=True, fill="both", padx=18)

        tk.Label(
            col,
            text=title,
            font=FONT_BOLD,
            fg=TEXT_SECONDARY,
            bg=BG_CARD
        ).pack(anchor="w", pady=(0, 10))

        for line in lines:
            tk.Label(
                col,
                text=line,
                font=FONT_NORMAL,
                fg=TEXT_PRIMARY,
                bg=BG_CARD
            ).pack(anchor="w", pady=2)

    # ================= RUNG TABLE =================

    def render_rungs_table(self, rungs, ccy_pair):
        wrapper = tk.Frame(self.scrollable_frame, bg=BG_MAIN)
        wrapper.pack(fill="x", pady=32)

        table = tk.Frame(wrapper, bg=BG_MAIN)
        table.pack(anchor="center")

        MAX_COLS = 2
        CARD_W = 520
        CARD_H = 150

        for idx, rung in enumerate(rungs):
            row = idx // MAX_COLS
            col = idx % MAX_COLS

            card = tk.Frame(
                table,
                bg=BG_CARD,
                width=CARD_W,
                height=CARD_H,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            card.grid(row=row, column=col, padx=24, pady=24)
            card.grid_propagate(False)

            inner = tk.Frame(card, bg=BG_CARD)
            inner.pack(fill="both", expand=True, padx=24, pady=20)

            grid = tk.Frame(inner, bg=BG_CARD)
            grid.pack(fill="both", expand=True)

            grid.columnconfigure(0, minsize=220)
            grid.columnconfigure(1, minsize=110)
            grid.columnconfigure(2, minsize=110)

            # HEADER
            tk.Label(
                grid,
                text="BID",
                font=FONT_BOLD,
                fg="#10B981",
                bg=BG_CARD
            ).grid(row=0, column=1)

            tk.Label(
                grid,
                text="ASK",
                font=FONT_BOLD,
                fg="#EF4444",
                bg=BG_CARD
            ).grid(row=0, column=2)

            # CCY PAIR
            tk.Label(
                grid,
                text="CCY PAIR:",
                font=FONT_NORMAL,
                fg=TEXT_SECONDARY,
                bg=BG_CARD,
                anchor="w"
            ).grid(row=1, column=0, sticky="w")

            tk.Label(
                grid,
                text=ccy_pair,
                font=FONT_BOLD,
                fg=TEXT_PRIMARY,
                bg=BG_CARD,
                anchor="w"
            ).grid(row=1, column=0, sticky="w", padx=(90, 0))

            # AMOUNT (con .)
            amount_fmt = f"{int(rung['amt']):,}".replace(",", ".")
            tk.Label(
                grid,
                text="AMOUNT:",
                font=FONT_NORMAL,
                fg=TEXT_SECONDARY,
                bg=BG_CARD,
                anchor="w"
            ).grid(row=2, column=0, sticky="w", pady=(6, 0))

            tk.Label(
                grid,
                text=amount_fmt,
                font=FONT_BOLD,
                fg=TEXT_PRIMARY,
                bg=BG_CARD,
                anchor="w"
            ).grid(row=2, column=0, sticky="w", padx=(90, 0), pady=(6, 0))

            # SPOT CORE
            tk.Label(
                grid,
                text="SPOT CORE:",
                font=FONT_NORMAL,
                fg=TEXT_SECONDARY,
                bg=BG_CARD,
                anchor="w"
            ).grid(row=3, column=0, sticky="w", pady=(14, 0))

            tk.Label(
                grid,
                text=rung["core"]["bid"],
                font=FONT_BOLD,
                fg="#10B981",
                bg=BG_CARD
            ).grid(row=3, column=1, pady=(14, 0))

            tk.Label(
                grid,
                text=rung["core"]["ask"],
                font=FONT_BOLD,
                fg="#EF4444",
                bg=BG_CARD
            ).grid(row=3, column=2, pady=(14, 0))

    # ================= NAV =================

    def go_back(self):
        for widget in self.master.winfo_children():
            widget.destroy()

        from UI.screens.HomeScreen import HomeScreen
        HomeScreen(self.master, controller=self.controller)