
import tkinter as tk
from tkinter import ttk
from datetime import datetime, date, time

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..db import obter_sessao, Usuario, HistoricoAcesso


class Dashboard(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app
        self.acessos = []
        self.indicadores = {}

        self.configure(padding=25)

        self.criar_cabecalho()
        self.criar_indicadores()
        self.criar_tabela()

        self.atualizar()

    def criar_cabecalho(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 25))

        ttk.Label(
            header,
            text="Dashboard",
            font=("Arial", 23, "bold")
        ).pack(side="left")

        ttk.Label(
            header,
            text="Visão geral dos acessos à catraca",
            font=("Arial", 10),
            foreground="#777777"
        ).pack(side="left", padx=18, pady=(8, 0))

        ttk.Button(
            header,
            text="Atualizar",
            command=self.atualizar
        ).pack(side="right")

    def criar_indicadores(self):
        cards = ttk.Frame(self)
        cards.pack(fill="x", pady=(0, 25))

        indicadores = [
            ("Usuários cadastrados", "#2563eb"),
            ("Acessos hoje", "#16a34a"),
            ("Acessos permitidos", "#0891b2"),
            ("Acessos negados", "#dc2626")
        ]

        for titulo, cor in indicadores:
            card = tk.Frame(
                cards,
                bg="white",
                highlightbackground="#e5e7eb",
                highlightthickness=1
            )

            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, 12)
            )

            tk.Label(
                card,
                text=titulo,
                bg="white",
                fg="#666666",
                font=("Arial", 10)
            ).pack(anchor="w", padx=18, pady=(18, 8))

            valor = tk.Label(
                card,
                text="0",
                bg="white",
                fg=cor,
                font=("Arial", 25, "bold")
            )

            valor.pack(anchor="w", padx=18, pady=(0, 18))

            self.indicadores[titulo] = valor

    def criar_tabela(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 15))

        ttk.Label(
            header,
            text="Últimos acessos",
            font=("Arial", 15, "bold")
        ).pack(side="left")

        ttk.Label(
            header,
            text="Exibindo os 10 registros mais recentes",
            foreground="#777777"
        ).pack(side="right", pady=5)

        tabela_frame = ttk.Frame(container)
        tabela_frame.pack(fill="both", expand=True)

        colunas = (
            "usuario",
            "data",
            "hora",
            "situacao"
        )

        self.tabela = ttk.Treeview(
            tabela_frame,
            columns=colunas,
            show="headings",
            height=10
        )

        self.tabela.heading("usuario", text="USUÁRIO")
        self.tabela.heading("data", text="DATA")
        self.tabela.heading("hora", text="HORÁRIO")
        self.tabela.heading("situacao", text="SITUAÇÃO")

        self.tabela.column("usuario", width=300)
        self.tabela.column("data", width=150, anchor="center")
        self.tabela.column("hora", width=120, anchor="center")
        self.tabela.column("situacao", width=150, anchor="center")

        scrollbar = ttk.Scrollbar(
            tabela_frame,
            orient="vertical",
            command=self.tabela.yview
        )

        self.tabela.configure(
            yscrollcommand=scrollbar.set
        )

        self.tabela.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tabela.tag_configure(
            "permitido",
            foreground="#16a34a"
        )

        self.tabela.tag_configure(
            "negado",
            foreground="#dc2626"
        )

        self.tabela.bind(
            "<Double-1>",
            self.abrir_registro
        )

        self.tabela.bind(
            "<Return>",
            self.abrir_registro
        )

        ttk.Label(
            container,
            text="Dê dois cliques em um registro para visualizar o usuário.",
            foreground="#888888",
            font=("Arial", 9)
        ).pack(anchor="w", pady=(12, 0))

    def atualizar(self):
        sessao = obter_sessao()

        try:
            inicio = datetime.combine(date.today(), time.min)
            fim = datetime.combine(date.today(), time.max)

            total_usuarios = (
                sessao.query(func.count(Usuario.id))
                .scalar() or 0
            )

            acessos_hoje = (
                sessao.query(func.count(HistoricoAcesso.id))
                .filter(
                    HistoricoAcesso.data_hora >= inicio,
                    HistoricoAcesso.data_hora <= fim
                )
                .scalar() or 0
            )

            permitidos = (
                sessao.query(func.count(HistoricoAcesso.id))
                .filter(HistoricoAcesso.autorizado.is_(True))
                .scalar() or 0
            )

            negados = (
                sessao.query(func.count(HistoricoAcesso.id))
                .filter(HistoricoAcesso.autorizado.is_(False))
                .scalar() or 0
            )

            self.indicadores["Usuários cadastrados"].config(
                text=str(total_usuarios)
            )

            self.indicadores["Acessos hoje"].config(
                text=str(acessos_hoje)
            )

            self.indicadores["Acessos permitidos"].config(
                text=str(permitidos)
            )

            self.indicadores["Acessos negados"].config(
                text=str(negados)
            )

            self.acessos = (
                sessao.query(HistoricoAcesso)
                .options(joinedload(HistoricoAcesso.usuario))
                .order_by(HistoricoAcesso.data_hora.desc())
                .limit(10)
                .all()
            )

            self.carregar_acessos(self.acessos)

        except Exception as erro:
            print(f"Erro ao atualizar dashboard: {erro}")

        finally:
            sessao.close()

    def carregar_acessos(self, acessos):
        self.tabela.delete(*self.tabela.get_children())

        for acesso in acessos:
            permitido = acesso.autorizado

            usuario = (
                acesso.usuario.nome
                if acesso.usuario
                else "Usuário não identificado"
            )

            data_hora = acesso.data_hora

            self.tabela.insert(
                "",
                "end",
                iid=str(acesso.id),
                values=(
                    usuario,
                    data_hora.strftime("%d/%m/%Y"),
                    data_hora.strftime("%H:%M:%S"),
                    "Permitido" if permitido else "Negado"
                ),
                tags=(
                    "permitido" if permitido else "negado",
                )
            )

    def abrir_registro(self, event=None):
        selecionado = self.tabela.selection()

        if not selecionado:
            return

        acesso_id = int(selecionado[0])

        acesso = next(
            (
                item for item in self.acessos
                if item.id == acesso_id
            ),
            None
        )

        if acesso and acesso.usuario_id:
            self.app.abrir_usuario(
                usuario_id=acesso.usuario_id
            )

    def ao_mostrar(self):
        self.atualizar()
