import tkinter as tk
from tkinter import messagebox, ttk
from decimal import Decimal

from UI.components.Header import Header
from UI.styles.theme import BACKGROUND, FONT_FAMILY
from services.CRLService import extract_all_crls, explain_triangulation


class CRLScreen(tk.Frame):
    def __init__(self, master, controller=None):
        super().__init__(master, bg=BACKGROUND)
        self.controller = controller
        self.pack(fill="both", expand=True)

        self.tree = None
        self.final_crl_pair = None
        self.final_crl_origin = None

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
        summary = tk.Frame(self, bg=BACKGROUND)
        summary.pack(fill="x", padx=30, pady=15)

        CARD_WIDTH = 260
        CARD_HEIGHT = 120

        for crl in crls:
            card = tk.Frame(
                summary,
                bg="#F4F6F8",
                width=CARD_WIDTH,
                height=CARD_HEIGHT,
                highlightbackground="#DEE2E6",
                highlightthickness=1
            )
            card.pack(side="left", padx=10)
            card.pack_propagate(False)

            inner = tk.Frame(card, bg="#F4F6F8")
            inner.pack(expand=True, fill="both", padx=12, pady=10)

            tk.Label(
                inner,
                text=crl["ccyPair"],
                font=(FONT_FAMILY, 12, "bold"),
                bg="#F4F6F8",
                fg="black"
            ).pack(anchor="w")

            tk.Label(
                inner,
                text=f'ID: {crl["id"]}',
                font=(FONT_FAMILY, 9),
                bg="#F4F6F8",
                fg="#6C757D"
            ).pack(anchor="w", pady=(2, 6))

            tk.Label(
                inner,
                text=f'{crl["origin"]} | {crl["valDt"]}',
                font=(FONT_FAMILY, 10),
                bg="#F4F6F8",
                fg="black"
            ).pack(anchor="w")

            tk.Label(
                inner,
                text=crl["rType"],
                font=(FONT_FAMILY, 10),
                bg="#F4F6F8",
                fg="black"
            ).pack(anchor="w")

    # ================= TABLE =================

    def render_rungs_table(self, crls, notional):
        table_frame = tk.Frame(self, bg=BACKGROUND)
        table_frame.pack(fill="both", expand=True, padx=30, pady=10)

        columns = (
            "ccyPair",
            "amt",
            "bid",
            "ask",
            "spread",
            "bidCond",
            "askCond"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=10
        )

        headings = {
            "ccyPair": "CCY Pair",
            "amt": "Amount",
            "bid": "Bid",
            "ask": "Ask",
            "spread": "Spread",
            "bidCond": "Bid Cond",
            "askCond": "Ask Cond"
        }

        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, anchor="center")

        self.tree.tag_configure(
            "active_rung",
            background="#FFA500",
            foreground="black"
        )

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

                tags = ()
                if crl is final_crl and rung["amt"] == active_amt:
                    tags = ("active_rung",)

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        crl["ccyPair"],
                        rung["amt"],
                        f"{bid:.5f}",
                        f"{ask:.5f}",
                        f"{spread:.5f}",
                        rung["bidCond"],
                        rung["askCond"]
                    ),
                    tags=tags
                )

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_rung_double_click)

    # ================= TRIANGULATION =================

    def on_rung_double_click(self, event):
        selected = self.tree.focus()
        if not selected:
            return

        values = self.tree.item(selected, "values")
        clicked_pair = values[0]

        # SOLO CRL FINAL y SOLO si es SYNTHETIC
        if (
            clicked_pair != self.final_crl_pair
            or self.final_crl_origin != "SYNTHETIC"
        ):
            return

        try:
            data = explain_triangulation(self.controller.last_parsed_scp)
            self.show_calculation_popup(data)
        except Exception as e:
            messagebox.showerror("Calculation error", str(e))

    def show_calculation_popup(self, data):
        popup = tk.Toplevel(self)
        popup.title("Triangulated price calculation")
        popup.geometry("520x360")
        popup.resizable(False, False)

        container = tk.Frame(popup, padx=16, pady=14)
        container.pack(fill="both", expand=True)

        def section(title):
            tk.Label(
                container,
                text=title,
                font=(FONT_FAMILY, 11, "bold")
            ).pack(anchor="w", pady=(12, 4))

        def line(text):
            tk.Label(
                container,
                text=text,
                font=(FONT_FAMILY, 10),
                justify="left",
                anchor="w"
            ).pack(anchor="w")

        tk.Label(
            container,
            text=f"Final pair: {data['finalPair']}",
            font=(FONT_FAMILY, 12, "bold")
        ).pack(anchor="w")

        section("BID")
        bid = data["bid"]
        line(" × ".join(
            f"{c['pair']} ({c['bid']})" for c in bid["components"]
        ))
        line(f"= {bid['result']}")

        section("ASK")
        ask = data["ask"]
        line(" × ".join(
            f"{c['pair']} ({c['ask']})" for c in ask["components"]
        ))
        line(f"= {ask['result']}")

        section("Sources")
        for src in data["sources"]:
            line(f"- {src['pair']} ({src['origin']}) [{src['id']}]")