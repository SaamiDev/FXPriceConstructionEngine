import tkinter as tk
from tkinter import messagebox
from decimal import Decimal

from UI.components.Header import Header
from UI.styles.desk_theme import (
    BG_MAIN,
    BG_PANEL,
    BG_CARD,
    BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ACCENT_ACTIVE,
    FONT_NORMAL,
    FONT_BOLD
)
from services.CRLService import extract_all_crls, explain_triangulation


class CRLScreen(tk.Frame):
    def __init__(self, master, controller=None):
        super().__init__(master, bg=BG_MAIN)
        self.controller = controller
        self.pack(fill="both", expand=True)

        self.final_crl_pair = None
        self.final_crl_origin = None
        self.active_row_bbox = None

        self.create_widgets()

    # ================= UI =================

    def create_widgets(self):
        Header(
            parent=self,
            title="Ver CRL",
            on_back=self.go_back
        )

        parsed_scp = getattr(self.controller, "last_parsed_scp", None)
        if not parsed_scp:
            messagebox.showwarning("Sin datos", "No hay ningún SCP desglosado.")
            return

        try:
            crls = extract_all_crls(parsed_scp)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if not crls:
            messagebox.showwarning("Sin CRL", "No se encontró información de CRL.")
            return

        self.final_crl_pair = crls[-1]["ccyPair"]
        self.final_crl_origin = crls[-1]["origin"]

        notional = Decimal(parsed_scp["clientPrc"][0]["notionalAmt"])

        self.render_crl_summary(crls)
        self.render_rungs_table(crls, notional)

    # ================= NAV =================

    def go_back(self):
        for widget in self.master.winfo_children():
            widget.destroy()

        from UI.screens.HomeScreen import HomeScreen
        HomeScreen(self.master, controller=self.controller)

    # ================= SUMMARY =================

    def render_crl_summary(self, crls):
        summary_wrapper = tk.Frame(self, bg=BG_MAIN)
        summary_wrapper.pack(fill="x", pady=20)

        summary = tk.Frame(summary_wrapper, bg=BG_MAIN)
        summary.pack(anchor="center")

        CARD_WIDTH = 320
        CARD_HEIGHT = 150

        for crl in crls:
            card = tk.Frame(
                summary,
                bg=BG_CARD,
                width=CARD_WIDTH,
                height=CARD_HEIGHT,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            card.pack(side="left", padx=16)
            card.pack_propagate(False)

            inner = tk.Frame(card, bg=BG_CARD)
            inner.pack(expand=True, fill="both", padx=16, pady=14)

            tk.Label(
                inner,
                text=crl["ccyPair"],
                font=FONT_BOLD,
                bg=BG_CARD,
                fg=TEXT_PRIMARY
            ).pack(anchor="w")

            tk.Label(
                inner,
                text=f'ID: {crl["id"]}',
                font=FONT_NORMAL,
                bg=BG_CARD,
                fg=TEXT_SECONDARY
            ).pack(anchor="w", pady=(4, 10))

            tk.Label(
                inner,
                text=f'{crl["origin"]} | {crl["valDt"]}',
                font=FONT_NORMAL,
                bg=BG_CARD,
                fg=TEXT_PRIMARY
            ).pack(anchor="w")

            tk.Label(
                inner,
                text=crl["rType"],
                font=FONT_NORMAL,
                bg=BG_CARD,
                fg=TEXT_PRIMARY
            ).pack(anchor="w", pady=(6, 0))

    # ================= TABLE =================

    def render_rungs_table(self, crls, notional):
        frame = tk.Frame(self, bg=BG_MAIN)
        frame.pack(fill="both", expand=True, padx=40, pady=10)

        canvas = tk.Canvas(frame, bg=BG_MAIN, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        canvas.bind("<Double-1>", self.on_canvas_double_click)

        headers = ["CCY", "Amount", "Bid", "Ask", "Spread"]
        col_widths = [110, 150, 150, 150, 150]
        row_h = 38

        table_width = sum(col_widths)

        canvas.update_idletasks()
        canvas_width = canvas.winfo_width() or table_width
        x0 = (canvas_width - table_width) // 2
        y = 24

        # ---- Header ----
        x = x0
        for h, w in zip(headers, col_widths):
            canvas.create_text(
                x + w / 2,
                y + row_h / 2,
                text=h,
                fill=TEXT_SECONDARY,
                font=FONT_BOLD
            )
            x += w

        y += row_h + 10

        final_crl = crls[-1]

        active_amt = None
        for rung in sorted(final_crl["rungs"], key=lambda r: r["amt"]):
            if Decimal(rung["amt"]) >= notional:
                active_amt = rung["amt"]
                break

        for crl in crls:
            for rung in crl["rungs"]:
                bid = Decimal(rung["bidPrice"])
                ask = Decimal(rung["askPrice"])
                spread = ask - bid

                is_active = (
                    crl is final_crl and rung["amt"] == active_amt
                )

                bg = ACCENT_ACTIVE if is_active else BG_CARD
                fg = "black" if is_active else TEXT_PRIMARY

                rect = canvas.create_rectangle(
                    x0, y,
                    x0 + table_width,
                    y + row_h,
                    fill=bg,
                    outline=""
                )

                if is_active:
                    self.active_row_bbox = canvas.bbox(rect)

                values = [
                    crl["ccyPair"],
                    rung["amt"],
                    f"{bid:.5f}",
                    f"{ask:.5f}",
                    f"{spread:.5f}"
                ]

                colors = [
                    fg,
                    fg,
                    "#10B981",  # BID verde
                    "#EF4444",  # ASK rojo
                    TEXT_SECONDARY
                ]

                x = x0
                for val, w, c in zip(values, col_widths, colors):
                    canvas.create_text(
                        x + w / 2,
                        y + row_h / 2,
                        text=val,
                        fill=c if not is_active else "black",
                        font=FONT_NORMAL
                    )
                    x += w

                y += row_h + 8

        self.canvas = canvas

    # ================= INTERACTION =================

    def on_canvas_double_click(self, event):
        if not self.active_row_bbox:
            return

        x1, y1, x2, y2 = self.active_row_bbox
        if not (x1 <= event.x <= x2 and y1 <= event.y <= y2):
            return

        if self.final_crl_origin != "SYNTHETIC":
            return

        try:
            data = explain_triangulation(self.controller.last_parsed_scp)
            self.show_calculation_popup(data)
        except Exception as e:
            messagebox.showerror("Calculation error", str(e))

    # ================= POPUP =================

    def show_calculation_popup(self, data):
        popup = tk.Toplevel(self)
        popup.title("Price construction")
        popup.geometry("560x440")
        popup.configure(bg=BG_MAIN)
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()

        container = tk.Frame(popup, bg=BG_MAIN, padx=20, pady=18)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text=f"Price construction – {data['finalPair']}",
            font=FONT_BOLD,
            bg=BG_MAIN,
            fg=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 18))

        def block(title, payload, color):
            card = tk.Frame(
                container,
                bg=BG_PANEL,
                highlightbackground=BORDER,
                highlightthickness=1,
                padx=16,
                pady=14
            )
            card.pack(fill="x", pady=10)

            tk.Label(
                card,
                text=title,
                font=FONT_BOLD,
                bg=BG_PANEL,
                fg=color
            ).pack(anchor="w", pady=(0, 8))

            for comp in payload["components"]:
                tk.Label(
                    card,
                    text=f"{comp['pair']} ({comp[title.lower()]})",
                    font=FONT_NORMAL,
                    bg=BG_PANEL,
                    fg=TEXT_SECONDARY
                ).pack(anchor="w", padx=14)

            tk.Label(
                card,
                text=f"= {payload['result']}",
                font=FONT_BOLD,
                bg=BG_PANEL,
                fg=TEXT_PRIMARY
            ).pack(anchor="w", padx=14, pady=(8, 0))

        block("BID", data["bid"], "#10B981")
        block("ASK", data["ask"], "#EF4444")