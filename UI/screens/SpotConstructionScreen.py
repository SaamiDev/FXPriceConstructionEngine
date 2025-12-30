import json
import os
import tkinter as tk
from tkinter import messagebox
from decimal import Decimal

from UI.components.Header import Header
from UI.styles.desk_theme import (
    BG_MAIN, BG_CARD, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY,
    FONT_NORMAL, FONT_BOLD,
    ACCENT_LINK
)

# 👇 Builder de auditoría
from services.SPOTAuditExplainService import SpotAuditExplainService

ACTIVE_BORDER = "#F59E0B"


class SpotConstructionScreen(tk.Frame):

    def __init__(self, master, controller=None):
        super().__init__(master, bg=BG_MAIN)
        self.controller = controller
        self._spot_data = None  # JSON completo para Explain
        self.pack(fill="both", expand=True)
        self._build_ui()

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):
        Header(self, title="Desglose Spot", on_back=self.go_back)

        refresh_bar = tk.Frame(self, bg=BG_MAIN)
        refresh_bar.pack(fill="x", pady=(8, 0))

        btn = tk.Label(
            refresh_bar,
            text="↻ Refresh",
            bg=ACCENT_LINK,
            fg="white",
            font=FONT_BOLD,
            padx=14,
            pady=8,
            cursor="hand2"
        )
        btn.pack(anchor="e", padx=24)
        btn.bind("<Button-1>", lambda e: self.refresh_and_render())
        btn.bind("<Enter>", lambda e: btn.config(bg="#2563EB"))
        btn.bind("<Leave>", lambda e: btn.config(bg=ACCENT_LINK))

        container = tk.Frame(self, bg=BG_MAIN)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg=BG_MAIN, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content = tk.Frame(self.canvas, bg=BG_MAIN)
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="n")

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.window_id, width=e.width)
        )
        self.content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.refresh_and_render()

    # =========================================================
    # LOAD / REFRESH
    # =========================================================

    def refresh_and_render(self):
        for w in self.content.winfo_children():
            w.destroy()

        scp_id = getattr(self.controller, "active_scp_id", None)
        if not scp_id:
            messagebox.showwarning("Sin datos", "No hay SCP activo.")
            return

        path = os.path.join(
            os.getcwd(), "resources", "scp", "spot_construction", f"{scp_id}.json"
        )
        if not os.path.exists(path):
            messagebox.showwarning("Sin desglose", "No existe el JSON de Spot.")
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._spot_data = data

        active_amt = None
        notional_raw = data.get("notional", {}).get("amount")

        if notional_raw:
            try:
                notional_amt = Decimal(notional_raw)
                for r in data.get("rungs", []):
                    if Decimal(r["amt"]) >= notional_amt:
                        active_amt = r["amt"]
                        break
            except Exception:
                pass

        self.render_spot_card(self.content, data)
        self.render_rungs_table(
            self.content,
            data.get("rungs", []),
            data.get("context", {}).get("ccyPair"),
            active_amt
        )

    # =========================================================
    # CONTEXT CARD
    # =========================================================

    def render_spot_card(self, parent, data):
        wrapper = tk.Frame(parent, bg=BG_MAIN)
        wrapper.pack(fill="x", pady=36)

        card = tk.Frame(wrapper, bg=BG_CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=24)

        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="both", expand=True, padx=28, pady=22)

        grid = tk.Frame(inner, bg=BG_CARD)
        grid.pack(fill="x")

        for i in range(3):
            grid.columnconfigure(i, weight=1, uniform="cols")

        ctx = data.get("context", {})
        cli = data.get("client", {})
        noti = data.get("notional", {})

        self._info_col(grid, 0, "Context", [
            f"CCY Pair: {ctx.get('ccyPair', '-')}",
            f"Venue: {ctx.get('venue', '-')}",
            f"SM Type: {ctx.get('smType', '-')}",
            f"Pricing Model: {ctx.get('prcModel', '-')}",
            f"Price Competition: {ctx.get('priceCompetition', '-')}",
        ])

        self._info_col(grid, 1, "Client", [
            f"Venue Client ID: {cli.get('venueClientId', '-')}",
            f"Venue Account ID: {cli.get('venueAccountId', '-')}",
            f"Venue User ID: {cli.get('venueUserId') or '-'}",
        ])

        self._info_col(grid, 2, "Notional", [
            f"Amount: {noti.get('amount') or '-'}",
            f"Side: {noti.get('side') or '-'}",
        ])

    def _info_col(self, parent, col, title, lines):
        frame = tk.Frame(parent, bg=BG_CARD)
        frame.grid(row=0, column=col, sticky="nw", padx=24)

        tk.Label(frame, text=title, font=FONT_BOLD,
                 fg=TEXT_SECONDARY, bg=BG_CARD).pack(anchor="w", pady=(0, 10))

        for l in lines:
            tk.Label(frame, text=l, font=FONT_NORMAL,
                     fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w")

    # =========================================================
    # RUNG TABLE
    # =========================================================

    def render_rungs_table(self, parent, rungs, ccy_pair, active_amt):
        wrapper = tk.Frame(parent, bg=BG_MAIN)
        wrapper.pack(pady=32)

        table = tk.Frame(wrapper, bg=BG_MAIN)
        table.pack()

        for i, r in enumerate(rungs):
            active = r.get("amt") == active_amt

            card = tk.Frame(
                table, bg=BG_CARD, width=560, height=420,
                highlightbackground=ACTIVE_BORDER if active else BORDER,
                highlightthickness=2 if active else 1
            )
            card.grid(row=i // 2, column=i % 2, padx=24, pady=24)
            card.grid_propagate(False)

            inner = tk.Frame(card, bg=BG_CARD)
            inner.pack(fill="both", expand=True, padx=24, pady=20)

            header = tk.Frame(inner, bg=BG_CARD)
            header.pack(fill="x", pady=(0, 10))

            tk.Label(
                header,
                text=f"RUNG {r['amt']}",
                font=FONT_BOLD,
                fg=TEXT_PRIMARY,
                bg=BG_CARD
            ).pack(side="left")

            explain_btn = tk.Label(
                header,
                text="Explain",
                font=FONT_BOLD,
                fg=ACCENT_LINK,
                bg=BG_CARD,
                cursor="hand2"
            )
            explain_btn.pack(side="right")
            explain_btn.bind(
                "<Button-1>",
                lambda e, rung=r: self.open_explain_modal(rung)
            )

            grid = tk.Frame(inner, bg=BG_CARD)
            grid.pack(fill="both", expand=True)

            grid.columnconfigure(0, minsize=240)
            grid.columnconfigure(1, minsize=130)
            grid.columnconfigure(2, minsize=130)

            row = 0
            tk.Label(grid, text="BID", font=FONT_BOLD,
                     fg="#10B981", bg=BG_CARD).grid(row=row, column=1)
            tk.Label(grid, text="ASK", font=FONT_BOLD,
                     fg="#EF4444", bg=BG_CARD).grid(row=row, column=2)
            row += 1

            self._meta_row(grid, row, "CCY PAIR:", ccy_pair); row += 1
            self._meta_row(grid, row, "AMOUNT:", f"{int(r['amt']):,}".replace(",", ".")); row += 1
            self._price_row(grid, row, "SPOT CORE:", r["core"]["bid"], r["core"]["ask"]); row += 1
            adj = r.get("adjustment", {})
            self._price_row(grid, row, "ADJUSTMENT:", adj.get("bidSpread", "-"), adj.get("askSpread", "-")); row += 1
            pa = r.get("priceAdjustment", {})
            self._price_row(grid, row, "PRICE ADJ:", pa.get("bid", "-"), pa.get("ask", "-")); row += 1
            ms = r.get("midSpread", {})
            self._single_row(grid, row, "MID:", ms.get("mid"), TEXT_PRIMARY); row += 1
            self._single_row(grid, row, "SPREAD:", ms.get("spread"), TEXT_SECONDARY); row += 1
            pr_rm = r.get("priceAfterRungModifier", {})
            self._price_row(grid, row, "PRICE AFTER RM:", pr_rm.get("bid", "-"), pr_rm.get("ask", "-")); row += 1
            self._single_row(grid, row, "MIN SPREAD:", r.get("minSpread"), TEXT_PRIMARY); row += 1
            pr_ms = r.get("priceAfterMinSpread", {})
            self._price_row(grid, row, "PRICE AFTER MIN SPREAD:", pr_ms.get("bid", "-"), pr_ms.get("ask", "-"))

    # =========================================================
    # EXPLAIN MODAL (AUDITORÍA)
    # =========================================================

    def open_explain_modal(self, rung_data: dict):
        modal = tk.Toplevel(self)
        modal.title("Spot Pricing – Audit Trail")
        modal.configure(bg=BG_MAIN)
        modal.geometry("700x580")
        modal.transient(self)
        modal.grab_set()

        container = tk.Frame(modal, bg=BG_CARD,
                              highlightbackground=BORDER,
                              highlightthickness=1)
        container.pack(fill="both", expand=True, padx=24, pady=24)

        tk.Label(
            container,
            text="Spot Price Construction – Audit Explanation",
            font=FONT_BOLD,
            fg=TEXT_PRIMARY,
            bg=BG_CARD
        ).pack(anchor="w", pady=(0, 16))

        text = tk.Text(container, bg=BG_CARD, fg=TEXT_PRIMARY,
                       font=("Menlo", 12), wrap="word", relief="flat")
        text.pack(fill="both", expand=True)

        text.tag_configure("title", font=("Menlo", 13, "bold"), foreground=TEXT_SECONDARY)
        text.tag_configure("bid", foreground="#10B981", font=("Menlo", 12, "bold"))
        text.tag_configure("ask", foreground="#EF4444", font=("Menlo", 12, "bold"))
        text.tag_configure("normal", foreground=TEXT_PRIMARY)

        explanation = SpotAuditExplainService(
            context=self._spot_data.get("context", {}),
            notional=self._spot_data.get("notional", {}),
            rung=rung_data
        ).build()

        self._insert_explain_with_colors(text, explanation)
        text.config(state="disabled")

    def _insert_explain_with_colors(self, text_widget: tk.Text, content: str):
        for line in content.split("\n"):
            if line.isupper() or line.startswith(("CONTEXT", "RUNG", "SPOT", "TOM", "MID", "MIN", "FINAL")):
                text_widget.insert("end", line + "\n", "title")
            elif "Bid =" in line or "Final Bid" in line:
                text_widget.insert("end", line + "\n", "bid")
            elif "Ask =" in line or "Final Ask" in line:
                text_widget.insert("end", line + "\n", "ask")
            else:
                text_widget.insert("end", line + "\n", "normal")

    # =========================================================
    # HELPERS
    # =========================================================

    def _meta_row(self, grid, row, label, value):
        tk.Label(grid, text=label, font=FONT_NORMAL,
                 fg=TEXT_SECONDARY, bg=BG_CARD).grid(row=row, column=0, sticky="w")
        tk.Label(grid, text=value, font=FONT_BOLD,
                 fg=TEXT_PRIMARY, bg=BG_CARD).grid(row=row, column=0, padx=(110, 0), sticky="w")

    def _price_row(self, grid, row, label, bid, ask):
        tk.Label(grid, text=label, font=FONT_NORMAL,
                 fg=TEXT_SECONDARY, bg=BG_CARD).grid(row=row, column=0, sticky="w")
        tk.Label(grid, text=bid, font=FONT_BOLD,
                 fg="#10B981", bg=BG_CARD).grid(row=row, column=1)
        tk.Label(grid, text=ask, font=FONT_BOLD,
                 fg="#EF4444", bg=BG_CARD).grid(row=row, column=2)

    def _single_row(self, grid, row, label, value, color):
        tk.Label(grid, text=label, font=FONT_NORMAL,
                 fg=TEXT_SECONDARY, bg=BG_CARD).grid(row=row, column=0, sticky="w")
        tk.Label(grid, text=value if value else "-",
                 font=FONT_BOLD, fg=color, bg=BG_CARD).grid(row=row, column=2)

    # =========================================================
    # NAV
    # =========================================================

    def go_back(self):
        for w in self.master.winfo_children():
            w.destroy()
        from UI.screens.HomeScreen import HomeScreen
        HomeScreen(self.master, controller=self.controller)