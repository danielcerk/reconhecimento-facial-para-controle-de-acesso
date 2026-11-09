
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from ..db import obter_sessao, Usuario


class Usuarios(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app
        self.usuarios = []
        self.usuario_id = None
        self.modo = "lista"

        self.configure(padding=25)

        self.mostrar_lista()

    def limpar_tela(self):
        for widget in self.winfo_children():
            widget.destroy()

    def ao_mostrar(self, usuario_id=None):
        if usuario_id:
            self.mostrar_visualizacao(usuario_id)
        else:
            self.mostrar_lista()

    # LISTAGEM

    def mostrar_lista(self):
        self.modo = "lista"
        self.usuario_id = None

        self.limpar_tela()

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Usuários",
            font=("Arial", 23, "bold")
        ).pack(side="left")

        ttk.Button(
            header,
            text="+ Novo usuário",
            command=self.mostrar_cadastro
        ).pack(side="right")

        filtros = ttk.Frame(self)
        filtros.pack(fill="x", pady=(0, 15))

        self.busca_var = tk.StringVar()

        busca = ttk.Entry(
            filtros,
            textvariable=self.busca_var,
            font=("Arial", 11)
        )

        busca.pack(side="left", fill="x", expand=True, ipady=7)

        busca.insert(0, "")

        ttk.Button(
            filtros,
            text="Atualizar",
            command=self.carregar_usuarios
        ).pack(side="right", padx=(10, 0))

        tabela_frame = ttk.Frame(self)
        tabela_frame.pack(fill="both", expand=True)

        colunas = (
            "nome",
            "matricula",
            "status",
            "criado"
        )

        self.tabela = ttk.Treeview(
            tabela_frame,
            columns=colunas,
            show="headings",
            height=15
        )

        self.tabela.heading("nome", text="NOME")
        self.tabela.heading("matricula", text="MATRÍCULA")
        self.tabela.heading("status", text="STATUS")
        self.tabela.heading("criado", text="CADASTRADO EM")

        self.tabela.column("nome", width=300)
        self.tabela.column("matricula", width=160, anchor="center")
        self.tabela.column("status", width=120, anchor="center")
        self.tabela.column("criado", width=170, anchor="center")

        scrollbar = ttk.Scrollbar(
            tabela_frame,
            orient="vertical",
            command=self.tabela.yview
        )

        self.tabela.configure(yscrollcommand=scrollbar.set)

        self.tabela.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tabela.tag_configure(
            "ativo",
            foreground="#16a34a"
        )

        self.tabela.tag_configure(
            "inativo",
            foreground="#dc2626"
        )

        self.tabela.bind(
            "<Double-1>",
            self.abrir_selecionado
        )

        self.tabela.bind(
            "<Return>",
            self.abrir_selecionado
        )

        ttk.Label(
            self,
            text="Dê dois cliques em um usuário para visualizar seus dados.",
            foreground="#888888",
            font=("Arial", 9)
        ).pack(anchor="w", pady=(12, 0))

        self.busca_var.trace_add(
            "write",
            lambda *_: self.filtrar_usuarios()
        )

        self.carregar_usuarios()

    def carregar_usuarios(self):
        sessao = obter_sessao()

        try:
            registros = (
                sessao.query(Usuario)
                .order_by(Usuario.nome.asc())
                .all()
            )

            self.usuarios = [
                {
                    "id": usuario.id,
                    "nome": usuario.nome,
                    "matricula": usuario.matricula,
                    "foto": usuario.foto,
                    "ativo": usuario.ativo,
                    "criado_em": usuario.criado_em
                }
                for usuario in registros
            ]

            self.filtrar_usuarios()

        except Exception as erro:
            messagebox.showerror(
                "Erro",
                f"Não foi possível carregar os usuários:\n{erro}"
            )

        finally:
            sessao.close()

    def filtrar_usuarios(self):
        if not hasattr(self, "tabela"):
            return

        pesquisa = self.busca_var.get().strip().lower()

        self.tabela.delete(*self.tabela.get_children())

        for usuario in self.usuarios:
            if (
                pesquisa not in usuario["nome"].lower()
                and pesquisa not in usuario["matricula"].lower()
            ):
                continue

            criado = usuario["criado_em"]

            self.tabela.insert(
                "",
                "end",
                iid=str(usuario["id"]),
                values=(
                    usuario["nome"],
                    usuario["matricula"],
                    "Ativo" if usuario["ativo"] else "Inativo",
                    criado.strftime("%d/%m/%Y %H:%M")
                    if criado else "-"
                ),
                tags=(
                    "ativo" if usuario["ativo"] else "inativo",
                )
            )

    def abrir_selecionado(self, event=None):
        selecionado = self.tabela.selection()

        if not selecionado:
            return

        self.mostrar_visualizacao(int(selecionado[0]))

    # VISUALIZAÇÃO

    def mostrar_visualizacao(self, usuario_id):
        sessao = obter_sessao()

        try:
            usuario = sessao.get(Usuario, usuario_id)

            if not usuario:
                messagebox.showerror(
                    "Erro",
                    "Usuário não encontrado."
                )
                self.mostrar_lista()
                return

            dados = {
                "id": usuario.id,
                "nome": usuario.nome,
                "matricula": usuario.matricula,
                "foto": usuario.foto,
                "ativo": usuario.ativo,
                "criado_em": usuario.criado_em
            }

        finally:
            sessao.close()

        self.modo = "visualizacao"
        self.usuario_id = usuario_id

        self.limpar_tela()

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 25))

        ttk.Button(
            header,
            text="← Voltar",
            command=self.mostrar_lista
        ).pack(side="left")

        ttk.Label(
            header,
            text="Dados do usuário",
            font=("Arial", 21, "bold")
        ).pack(side="left", padx=20)

        ttk.Button(
            header,
            text="Editar usuário",
            command=lambda: self.mostrar_edicao(usuario_id)
        ).pack(side="right")

        conteudo = ttk.Frame(self)
        conteudo.pack(fill="x", anchor="n")

        self.adicionar_campo(
            conteudo, "Nome completo", dados["nome"], 0
        )

        self.adicionar_campo(
            conteudo, "Matrícula", dados["matricula"], 1
        )

        self.adicionar_campo(
            conteudo,
            "Status",
            "Ativo" if dados["ativo"] else "Inativo",
            2
        )

        self.adicionar_campo(
            conteudo,
            "Foto",
            dados["foto"] or "Nenhuma foto cadastrada",
            3
        )

        criado = dados["criado_em"]

        self.adicionar_campo(
            conteudo,
            "Data de cadastro",
            criado.strftime("%d/%m/%Y às %H:%M")
            if criado else "-",
            4
        )

    def adicionar_campo(self, parent, titulo, valor, linha):
        campo = ttk.Frame(parent)
        campo.pack(fill="x", pady=10)

        ttk.Label(
            campo,
            text=titulo,
            font=("Arial", 9, "bold"),
            foreground="#777777"
        ).pack(anchor="w")

        ttk.Label(
            campo,
            text=str(valor),
            font=("Arial", 12)
        ).pack(anchor="w", pady=(5, 0))

        ttk.Separator(parent).pack(fill="x", pady=5)

    # CADASTRO E EDIÇÃO

    def mostrar_cadastro(self):
        self.mostrar_formulario()

    def mostrar_edicao(self, usuario_id):
        sessao = obter_sessao()

        try:
            usuario = sessao.get(Usuario, usuario_id)

            if not usuario:
                messagebox.showerror(
                    "Erro",
                    "Usuário não encontrado."
                )
                self.mostrar_lista()
                return

            dados = {
                "nome": usuario.nome,
                "matricula": usuario.matricula,
                "foto": usuario.foto or "",
                "ativo": usuario.ativo
            }

        finally:
            sessao.close()

        self.mostrar_formulario(usuario_id, dados)

    def mostrar_formulario(self, usuario_id=None, dados=None):
        self.modo = "formulario"
        self.usuario_id = usuario_id

        dados = dados or {}

        self.limpar_tela()

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 25))

        ttk.Button(
            header,
            text="← Voltar",
            command=lambda: (
                self.mostrar_visualizacao(usuario_id)
                if usuario_id else self.mostrar_lista()
            )
        ).pack(side="left")

        ttk.Label(
            header,
            text="Editar usuário" if usuario_id else "Novo usuário",
            font=("Arial", 21, "bold")
        ).pack(side="left", padx=20)

        formulario = ttk.Frame(self)
        formulario.pack(fill="x", anchor="n", padx=5)

        self.nome_var = tk.StringVar(value=dados.get("nome", ""))
        self.matricula_var = tk.StringVar(
            value=dados.get("matricula", "")
        )
        self.foto_var = tk.StringVar(value=dados.get("foto", ""))
        self.ativo_var = tk.BooleanVar(
            value=dados.get("ativo", True)
        )

        self.criar_input(
            formulario,
            "Nome completo",
            self.nome_var,
            0
        )

        self.criar_input(
            formulario,
            "Matrícula",
            self.matricula_var,
            1
        )

        ttk.Label(
            formulario,
            text="Foto do usuário",
            font=("Arial", 10, "bold")
        ).grid(row=4, column=0, sticky="w", pady=(18, 7))

        foto_frame = ttk.Frame(formulario)
        foto_frame.grid(row=5, column=0, sticky="ew")

        foto_frame.columnconfigure(0, weight=1)

        ttk.Entry(
            foto_frame,
            textvariable=self.foto_var
        ).grid(row=0, column=0, sticky="ew", ipady=6)

        ttk.Button(
            foto_frame,
            text="Selecionar foto",
            command=self.selecionar_foto
        ).grid(row=0, column=1, padx=(10, 0))

        ttk.Checkbutton(
            formulario,
            text="Usuário ativo",
            variable=self.ativo_var
        ).grid(row=6, column=0, sticky="w", pady=20)

        botoes = ttk.Frame(formulario)
        botoes.grid(row=7, column=0, sticky="e", pady=20)

        ttk.Button(
            botoes,
            text="Cancelar",
            command=lambda: (
                self.mostrar_visualizacao(usuario_id)
                if usuario_id else self.mostrar_lista()
            )
        ).pack(side="left", padx=5)

        ttk.Button(
            botoes,
            text="Salvar alterações" if usuario_id else "Cadastrar usuário",
            command=self.salvar_usuario
        ).pack(side="left")

        formulario.columnconfigure(0, weight=1)

    def criar_input(self, parent, titulo, variavel, linha):
        ttk.Label(
            parent,
            text=titulo,
            font=("Arial", 10, "bold")
        ).grid(
            row=linha * 2,
            column=0,
            sticky="w",
            pady=(15, 7)
        )

        ttk.Entry(
            parent,
            textvariable=variavel,
            font=("Arial", 11)
        ).grid(
            row=linha * 2 + 1,
            column=0,
            sticky="ew",
            ipady=7
        )

    def selecionar_foto(self):
        caminho = filedialog.askopenfilename(
            title="Selecionar foto do usuário",
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg *.webp"),
                ("Todos os arquivos", "*.*")
            ]
        )

        if caminho:
            self.foto_var.set(caminho)

    def salvar_usuario(self):
        nome = self.nome_var.get().strip()
        matricula = self.matricula_var.get().strip()
        foto = self.foto_var.get().strip() or None
        ativo = self.ativo_var.get()

        if not nome or not matricula:
            messagebox.showwarning(
                "Campos obrigatórios",
                "Preencha o nome e a matrícula."
            )
            return

        sessao = obter_sessao()

        try:
            if self.usuario_id:
                usuario = sessao.get(Usuario, self.usuario_id)

                if not usuario:
                    messagebox.showerror(
                        "Erro",
                        "Usuário não encontrado."
                    )
                    return

            else:
                usuario = Usuario()
                sessao.add(usuario)

            usuario.nome = nome
            usuario.matricula = matricula
            usuario.foto = foto
            usuario.ativo = ativo

            sessao.commit()

            usuario_id = usuario.id

            messagebox.showinfo(
                "Sucesso",
                "Usuário atualizado com sucesso."
                if self.usuario_id
                else "Usuário cadastrado com sucesso."
            )

        except IntegrityError:
            sessao.rollback()

            messagebox.showerror(
                "Matrícula duplicada",
                "Já existe um usuário cadastrado com essa matrícula."
            )
            return

        except Exception as erro:
            sessao.rollback()

            messagebox.showerror(
                "Erro",
                f"Não foi possível salvar o usuário:\n{erro}"
            )
            return

        finally:
            sessao.close()

        self.mostrar_visualizacao(usuario_id)
