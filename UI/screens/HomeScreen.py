import tkinter as tk
import os
import json
from tkinter import messagebox
from services.SCPDeleteService import SCPDeleteService

from UI.components.StyledButton import StyledButton
from UI.components.Header import Header
from UI.styles.desk_theme import (
    BG_MAIN,
    BG_CARD,
    BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ACCENT_ACTIVE,
    FONT_NORMAL,
    FONT_BOLD
)

from services.SCPIndexService import SCPIndexService


class HomeScreen(tk.Frame):

    def __init__(self, master, controller=None):
        super().__init__(master, bg=BG_MAIN)
        self.controller = controller

        # ── Estado SCPs ──
        self.scps = []
        self.page = 0
        self.page_size = 5  # 👈 aquí controlas cuántos por página

        # ── Estado tabla ──
        self.scp_rows = []
        self.scp_canvas = None
        self.page_label = None

        self.pack(fill="both", expand=True)
        self.create_widgets()

    # ================= UI =================

    def create_widgets(self):
        Header(self, title="FX Price Construction", on_back=None)

        content = tk.Frame(self, bg=BG_MAIN)
        content.pack(fill="x", pady=(20, 0))

        tk.Label(
            content,
            text="Pricing & Analysis",
            font=FONT_BOLD,
            fg=TEXT_SECONDARY,
            bg=BG_MAIN
        ).pack(pady=(0, 20))

        # ── Botonera ──
        button_frame = tk.Frame(content, bg=BG_MAIN)
        button_frame.pack(pady=(0, 20))

        StyledButton(button_frame, "Buscar Traza", self.on_search).grid(row=0, column=0, padx=8)
        StyledButton(button_frame, "Desglosar Spot", self.on_spot).grid(row=0, column=1, padx=8)
        StyledButton(button_frame, "Importar Traza SCP", self.open_trace_import).grid(row=0, column=2, padx=8)
        StyledButton(button_frame, "Ver CRL", self.open_crl_view).grid(row=0, column=3, padx=8)

        # ── Contenedores FIJOS (clave) ──
        self.table_wrapper = tk.Frame(content, bg=BG_MAIN)
        self.table_wrapper.pack(expand=True, pady=(10, 4))

        self.pagination_wrapper = tk.Frame(content, bg=BG_MAIN)
        self.pagination_wrapper.pack(pady=(0, 20))

        self.load_scps()
        self.render_scp_table()
        self.render_pagination_controls()

    def delete_scp_inline(self, scp):
        scp_id = scp.get("scpId")

        if not scp_id:
            return

        confirm = messagebox.askyesno(
            "Eliminar SCP",
            f"¿Eliminar el SCP:\n\n{scp_id}?\n\nEsta acción no se puede deshacer."
        )

        if not confirm:
            return

        service = SCPDeleteService(base_path=os.getcwd())
        deleted = service.delete(scp_id)

        if deleted:
            # Limpia selección si era el activo
            if self.controller.active_scp_id == scp_id:
                self.controller.active_scp_id = None
                self.controller.last_parsed_scp = None

            self.load_scps()
            self.refresh_scp_table()

            messagebox.showinfo(
                "SCP eliminado",
                f"SCP {scp_id} eliminado correctamente."
            )
    # ================= DATA =================

    def load_scps(self):
        service = SCPIndexService(base_path=os.getcwd())
        self.scps = service.list_scps()
        self.page = 0

    @property
    def total_pages(self):
        return max(1, (len(self.scps) - 1) // self.page_size + 1)

    def _page_text(self):
        return f"Page {self.page + 1} / {self.total_pages}"

    def refresh_scp_table(self):
        self.render_scp_table()
        self.update_page_label()

    # ================= SCP TABLE =================

    def render_scp_table(self):
        for w in self.table_wrapper.winfo_children():
            w.destroy()

        if not self.scps:
            return

        headers = ["PriceID", "CCY Pair", "Notional", "Venue", "Time", ""]
        col_widths = [160, 110, 140, 200, 220, 40]  # última = delete
        row_h = 38
        table_width = sum(col_widths)

        canvas = tk.Canvas(
            self.table_wrapper,
            bg=BG_MAIN,
            highlightthickness=0,
            height=260,
            width=table_width
        )
        canvas.pack(anchor="center")
        canvas.bind("<Button-1>", self.on_scp_click)

        self.scp_rows.clear()
        self.scp_canvas = canvas

        x0, y = 0, 16

        # ── HEADER ─────────────────────────────
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

        start = self.page * self.page_size
        end = start + self.page_size

        # ── ROWS ───────────────────────────────
        for scp in self.scps[start:end]:
            rect = canvas.create_rectangle(
                x0, y,
                x0 + table_width, y + row_h,
                fill=BG_CARD,
                outline=BORDER
            )

            values = [
                scp.get("priceId"),
                scp.get("ccyPair"),
                scp.get("notional"),
                scp.get("venue"),
                scp.get("timestamp")
            ]

            texts = []
            x = x0
            for val, w in zip(values, col_widths[:-1]):  # sin la col delete
                t = canvas.create_text(
                    x + w / 2,
                    y + row_h / 2,
                    text=val,
                    fill=TEXT_PRIMARY,
                    font=FONT_NORMAL
                )
                texts.append(t)
                x += w

            # ── DELETE ICON ────────────────────
            delete_x = x0 + table_width - 20
            delete_y = y + row_h / 2

            delete_icon = canvas.create_text(
                delete_x,
                delete_y,
                text="🗑",
                font=("Segoe UI Emoji", 13),
                fill="#9CA3AF"
            )

            # Hover
            canvas.tag_bind(
                delete_icon, "<Enter>",
                lambda e, icon=delete_icon: (
                    canvas.itemconfig(icon, fill="#EF4444"),
                    canvas.config(cursor="hand2")
                )
            )

            canvas.tag_bind(
                delete_icon, "<Leave>",
                lambda e, icon=delete_icon: (
                    canvas.itemconfig(icon, fill="#9CA3AF"),
                    canvas.config(cursor="")
                )
            )

            # Click delete
            canvas.tag_bind(
                delete_icon, "<Button-1>",
                lambda e, scp=scp: self.delete_scp_inline(scp)
            )

            self.scp_rows.append({
                "bbox": canvas.bbox(rect),
                "rect": rect,
                "texts": texts,
                "scp": scp
            })

            y += row_h + 6

    # ================= PAGINATION =================

    def render_pagination_controls(self):

        for w in self.pagination_wrapper.winfo_children():
            w.destroy()

        StyledButton(
            self.pagination_wrapper, "‹",
            self.prev_page, width=32, height=28
        ).pack(side="left", padx=6)

        self.page_label = tk.Label(
            self.pagination_wrapper,
            text=self._page_text(),
            bg=BG_MAIN,
            fg=TEXT_SECONDARY,
            font=FONT_NORMAL
        )
        self.page_label.pack(side="left", padx=8)

        StyledButton(
            self.pagination_wrapper, "›",
            self.next_page, width=32, height=28
        ).pack(side="left", padx=6)

    def update_page_label(self):
        if self.page_label:
            self.page_label.config(text=self._page_text())

    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self.refresh_scp_table()

    def next_page(self):
        if self.page < self.total_pages - 1:
            self.page += 1
            self.refresh_scp_table()

    # ================= INTERACTION =================

    def on_scp_click(self, event):
        for row in self.scp_rows:
            x1, y1, x2, y2 = row["bbox"]
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.select_scp_row(row)
                break

    def select_scp_row(self, row):
        for r in self.scp_rows:
            self.scp_canvas.itemconfig(r["rect"], fill=BG_CARD)
            for t in r["texts"]:
                self.scp_canvas.itemconfig(t, fill=TEXT_PRIMARY)

        self.scp_canvas.itemconfig(row["rect"], fill=ACCENT_ACTIVE)
        for t in row["texts"]:
            self.scp_canvas.itemconfig(t, fill="black")

        scp = row["scp"]
        self.controller.active_scp_id = scp["scpId"]

        path = os.path.join(
            os.getcwd(),
            "resources",
            "scp",
            "history",
            "parsed",
            f"{scp['scpId']}.json"
        )

        try:
            with open(path, "r", encoding="utf-8") as f:
                self.controller.last_parsed_scp = json.load(f)
        except Exception:
            self.controller.last_parsed_scp = None

    # ================= EVENTS =================

    def on_search(self):
        messagebox.showinfo("Info", "Funcionalidad pendiente.")

    def on_spot(self):
        for w in self.master.winfo_children():
            w.destroy()
        from UI.screens.SpotConstructionScreen import SpotConstructionScreen
        SpotConstructionScreen(self.master, controller=self.controller)

    def open_trace_import(self):
        for w in self.master.winfo_children():
            w.destroy()
        from UI.screens.TraceImportScreen import TraceImportScreen
        TraceImportScreen(self.master, controller=self.controller)

    def open_crl_view(self):
        for w in self.master.winfo_children():
            w.destroy()
        from UI.screens.CRLScreen import CRLScreen
        CRLScreen(self.master, controller=self.controller)