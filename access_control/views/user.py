
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageTk
from sqlalchemy.exc import IntegrityError

from ..db import (
    obter_sessao,
    Usuario,
    cadastrar_usuario,
    salvar_vetor_facial,
    excluir_vetores_faciais,
    listar_vetores_faciais,
)


BASE_DIR = Path(__file__).resolve().parents[2]
CASCADE_DIR = BASE_DIR / "recognizer" / "cascades"

FACE_CASCADE_PATH = CASCADE_DIR / "haarcascade_frontalface_default.xml"
EYE_CASCADE_PATH = CASCADE_DIR / "haarcascade_eye_tree_eyeglasses.xml"

face_cascade = cv2.CascadeClassifier(str(FACE_CASCADE_PATH))
eye_cascade = cv2.CascadeClassifier(str(EYE_CASCADE_PATH))

if face_cascade.empty():
    raise RuntimeError(f"Não foi possível carregar: {FACE_CASCADE_PATH}")

if eye_cascade.empty():
    raise RuntimeError(f"Não foi possível carregar: {EYE_CASCADE_PATH}")

face_analysis = None


def obter_modelo_facial():
    global face_analysis

    if face_analysis is None:
        from insightface.app import FaceAnalysis

        face_analysis = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )
        face_analysis.prepare(ctx_id=-1, det_size=(640, 640))

    return face_analysis


class Usuarios(ttk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app
        self.usuarios = []
        self.usuario_id = None
        self.modo = "lista"

        self.camera = None
        self.camera_aberta = False
        self.janela_camera = None
        self.ultimo_frame = None
        self.vetores_capturados = []
        self.preview_camera = None
        self.camera_after_id = None

        self.configure(padding=25)
        self.mostrar_lista()

    def limpar_tela(self):
        self.fechar_captura_facial()

        for widget in self.winfo_children():
            widget.destroy()

    def ao_mostrar(self, usuario_id=None):
        if usuario_id:
            self.mostrar_visualizacao(usuario_id)
        else:
            self.mostrar_lista()

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

        ttk.Button(
            filtros,
            text="Atualizar",
            command=self.carregar_usuarios
        ).pack(side="right", padx=(10, 0))

        tabela_frame = ttk.Frame(self)
        tabela_frame.pack(fill="both", expand=True)

        colunas = ("nome", "matricula", "status", "criado")

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

        self.tabela.tag_configure("ativo", foreground="#16a34a")
        self.tabela.tag_configure("inativo", foreground="#dc2626")

        self.tabela.bind("<Double-1>", self.abrir_selecionado)
        self.tabela.bind("<Return>", self.abrir_selecionado)

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
                    criado.strftime("%d/%m/%Y %H:%M") if criado else "-"
                ),
                tags=("ativo" if usuario["ativo"] else "inativo",)
            )

    def abrir_selecionado(self, event=None):
        selecionado = self.tabela.selection()

        if not selecionado:
            return

        self.mostrar_visualizacao(int(selecionado[0]))

    def mostrar_visualizacao(self, usuario_id):
        self.fechar_captura_facial()

        sessao = obter_sessao()

        try:
            usuario = sessao.get(Usuario, usuario_id)

            if not usuario:
                messagebox.showerror("Erro", "Usuário não encontrado.")
                self.mostrar_lista()
                return

            dados = {
                "id": usuario.id,
                "nome": usuario.nome,
                "matricula": usuario.matricula,
                "ativo": usuario.ativo,
                "criado_em": usuario.criado_em
            }

            quantidade_vetores = len(
                listar_vetores_faciais(usuario_id)
            )

        except Exception as erro:
            messagebox.showerror(
                "Erro",
                f"Não foi possível carregar o usuário:\n{erro}"
            )
            return

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
            conteudo,
            "Nome completo",
            dados["nome"],
            0
        )

        self.adicionar_campo(
            conteudo,
            "Matrícula",
            dados["matricula"],
            1
        )

        self.adicionar_campo(
            conteudo,
            "Status",
            "Ativo" if dados["ativo"] else "Inativo",
            2
        )

        self.adicionar_campo(
            conteudo,
            "Amostras faciais cadastradas",
            quantidade_vetores,
            3
        )

        criado = dados["criado_em"]

        self.adicionar_campo(
            conteudo,
            "Data de cadastro",
            criado.strftime("%d/%m/%Y às %H:%M") if criado else "-",
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

    def mostrar_cadastro(self):
        self.mostrar_formulario()

    def mostrar_edicao(self, usuario_id):
        sessao = obter_sessao()

        try:
            usuario = sessao.get(Usuario, usuario_id)

            if not usuario:
                messagebox.showerror("Erro", "Usuário não encontrado.")
                self.mostrar_lista()
                return

            dados = {
                "nome": usuario.nome,
                "matricula": usuario.matricula,
                "ativo": usuario.ativo
            }

        finally:
            sessao.close()

        self.mostrar_formulario(usuario_id, dados)

    def mostrar_formulario(self, usuario_id=None, dados=None):
        self.fechar_captura_facial()

        self.modo = "formulario"
        self.usuario_id = usuario_id
        self.vetores_capturados = []

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
            text="Reconhecimento facial",
            font=("Arial", 10, "bold")
        ).grid(
            row=4,
            column=0,
            sticky="w",
            pady=(18, 7)
        )

        facial_frame = ttk.Frame(formulario)
        facial_frame.grid(row=5, column=0, sticky="ew")

        self.status_facial = tk.StringVar(
            value="Nenhuma amostra capturada"
        )

        ttk.Label(
            facial_frame,
            textvariable=self.status_facial
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            facial_frame,
            text="Abrir webcam",
            command=self.abrir_captura_facial
        ).pack(side="right")

        if usuario_id:
            quantidade = len(listar_vetores_faciais(usuario_id))

            ttk.Label(
                formulario,
                text=f"Amostras atualmente cadastradas: {quantidade}",
                foreground="#777777"
            ).grid(
                row=6,
                column=0,
                sticky="w",
                pady=(8, 0)
            )

        ttk.Checkbutton(
            formulario,
            text="Usuário ativo",
            variable=self.ativo_var
        ).grid(
            row=7,
            column=0,
            sticky="w",
            pady=20
        )

        botoes = ttk.Frame(formulario)
        botoes.grid(row=8, column=0, sticky="e", pady=20)

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

    def abrir_captura_facial(self):
        if self.camera_aberta:
            return

        try:
            self.camera = cv2.VideoCapture(0)

            if not self.camera.isOpened():
                self.camera.release()
                self.camera = None
                messagebox.showerror(
                    "Webcam",
                    "Não foi possível acessar a webcam."
                )
                return

            self.camera_aberta = True

            self.janela_camera = tk.Toplevel(self)
            self.janela_camera.title("Captura facial")
            self.janela_camera.geometry("760x650")
            self.janela_camera.resizable(False, False)
            self.janela_camera.transient(self.winfo_toplevel())
            self.janela_camera.protocol(
                "WM_DELETE_WINDOW",
                self.fechar_captura_facial
            )

            container = ttk.Frame(self.janela_camera, padding=15)
            container.pack(fill="both", expand=True)

            self.preview_camera = ttk.Label(container)
            self.preview_camera.pack(fill="both", expand=True)

            self.contador_amostras = tk.StringVar(
                value=f"Amostras capturadas: {len(self.vetores_capturados)}/5"
            )

            ttk.Label(
                container,
                textvariable=self.contador_amostras,
                font=("Arial", 11, "bold")
            ).pack(pady=10)

            self.status_camera = tk.StringVar(
                value="Posicione seu rosto diante da câmera."
            )

            ttk.Label(
                container,
                textvariable=self.status_camera
            ).pack(pady=5)

            botoes = ttk.Frame(container)
            botoes.pack(pady=10)

            ttk.Button(
                botoes,
                text="Capturar amostra",
                command=self.capturar_amostra
            ).pack(side="left", padx=5)

            ttk.Button(
                botoes,
                text="Finalizar captura",
                command=self.fechar_captura_facial
            ).pack(side="left", padx=5)

            self.atualizar_camera()

        except Exception as erro:
            self.fechar_captura_facial()

            messagebox.showerror(
                "Erro",
                f"Não foi possível iniciar a webcam:\n{erro}"
            )

    def atualizar_camera(self):
        if (
            not self.camera_aberta
            or self.camera is None
            or self.janela_camera is None
            or not self.janela_camera.winfo_exists()
        ):
            return

        sucesso, frame = self.camera.read()

        if not sucesso:
            self.status_camera.set("Não foi possível obter imagem da câmera.")
            self.camera_after_id = self.janela_camera.after(
                100,
                self.atualizar_camera
            )
            return

        self.ultimo_frame = frame.copy()

        imagem_cinza = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        rostos = face_cascade.detectMultiScale(
            imagem_cinza,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(100, 100)
        )

        rosto_valido = False

        for (x, y, largura, altura) in rostos:
            roi_olhos = imagem_cinza[
                y:y + altura,
                x:x + largura
            ]

            olhos = eye_cascade.detectMultiScale(
                roi_olhos,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(15, 15)
            )

            cor = (0, 200, 0) if len(olhos) >= 2 else (0, 165, 255)

            cv2.rectangle(
                frame,
                (x, y),
                (x + largura, y + altura),
                cor,
                2
            )

            for (ex, ey, ew, eh) in olhos:
                cv2.rectangle(
                    frame,
                    (x + ex, y + ey),
                    (x + ex + ew, y + ey + eh),
                    (255, 0, 0),
                    1
                )

            if len(olhos) >= 2:
                rosto_valido = True

        if rosto_valido:
            self.status_camera.set(
                "Rosto e olhos detectados. Você pode capturar."
            )
        elif len(rostos):
            self.status_camera.set(
                "Mantenha os olhos visíveis diante da câmera."
            )
        else:
            self.status_camera.set(
                "Nenhum rosto detectado."
            )

        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        imagem = Image.fromarray(frame_rgb)
        imagem.thumbnail((720, 480))

        foto = ImageTk.PhotoImage(imagem)

        self.preview_camera.configure(image=foto)
        self.preview_camera.image = foto

        self.camera_after_id = self.janela_camera.after(
            30,
            self.atualizar_camera
        )

    def extrair_embedding(self, frame):
        imagem_cinza = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        rostos = face_cascade.detectMultiScale(
            imagem_cinza,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(100, 100)
        )

        if len(rostos) != 1:
            raise ValueError(
                "Mantenha apenas um rosto visível na câmera."
            )

        x, y, largura, altura = rostos[0]

        roi_olhos = imagem_cinza[
            y:y + altura,
            x:x + largura
        ]

        olhos = eye_cascade.detectMultiScale(
            roi_olhos,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(15, 15)
        )

        if len(olhos) < 2:
            raise ValueError(
                "Não foi possível detectar os dois olhos."
            )

        modelo = obter_modelo_facial()
        faces = modelo.get(frame)

        if not faces:
            raise ValueError(
                "O modelo facial não conseguiu reconhecer o rosto."
            )

        centro_x = x + largura / 2
        centro_y = y + altura / 2

        def distancia(face):
            esquerda, superior, direita, inferior = face.bbox

            face_x = (esquerda + direita) / 2
            face_y = (superior + inferior) / 2

            return (
                (face_x - centro_x) ** 2
                + (face_y - centro_y) ** 2
            )

        face = min(faces, key=distancia)

        embedding = np.asarray(
            face.normed_embedding,
            dtype=np.float32
        )

        if embedding.shape != (512,):
            raise ValueError(
                "O modelo retornou um vetor facial inválido."
            )

        if not np.all(np.isfinite(embedding)):
            raise ValueError(
                "O vetor facial contém valores inválidos."
            )

        norma = np.linalg.norm(embedding)

        if norma == 0:
            raise ValueError(
                "Não foi possível normalizar o vetor facial."
            )

        return embedding / norma

    def capturar_amostra(self):
        if self.ultimo_frame is None:
            return

        if len(self.vetores_capturados) >= 5:
            self.status_camera.set(
                "Limite de 5 amostras atingido."
            )
            return

        try:
            embedding = self.extrair_embedding(
                self.ultimo_frame.copy()
            )

            self.vetores_capturados.append(embedding)

            quantidade = len(self.vetores_capturados)

            self.contador_amostras.set(
                f"Amostras capturadas: {quantidade}/5"
            )

            self.status_camera.set(
                f"Amostra {quantidade} capturada com sucesso."
            )

        except Exception as erro:
            self.status_camera.set(str(erro))

    def fechar_captura_facial(self):
        self.camera_aberta = False

        if self.camera_after_id and self.janela_camera:
            try:
                self.janela_camera.after_cancel(
                    self.camera_after_id
                )
            except tk.TclError:
                pass

        self.camera_after_id = None

        if self.camera is not None:
            self.camera.release()
            self.camera = None

        if self.janela_camera is not None:
            try:
                if self.janela_camera.winfo_exists():
                    self.janela_camera.destroy()
            except tk.TclError:
                pass

        self.janela_camera = None
        self.preview_camera = None
        self.ultimo_frame = None

        if hasattr(self, "status_facial"):
            try:
                if self.winfo_exists():
                    quantidade = len(self.vetores_capturados)

                    self.status_facial.set(
                        f"{quantidade} amostra(s) capturada(s)"
                        if quantidade
                        else "Nenhuma amostra capturada"
                    )
            except tk.TclError:
                pass

    def salvar_usuario(self):
        nome = self.nome_var.get().strip()
        matricula = self.matricula_var.get().strip()
        ativo = self.ativo_var.get()

        if not nome or not matricula:
            messagebox.showwarning(
                "Campos obrigatórios",
                "Preencha o nome e a matrícula."
            )
            return

        if self.camera_aberta:
            messagebox.showwarning(
                "Captura em andamento",
                "Finalize a captura da webcam antes de salvar."
            )
            return

        if not self.usuario_id and len(self.vetores_capturados) < 3:
            messagebox.showwarning(
                "Reconhecimento facial",
                "Capture pelo menos 3 amostras faciais antes de cadastrar."
            )
            return

        if self.vetores_capturados and len(self.vetores_capturados) < 3:
            messagebox.showwarning(
                "Reconhecimento facial",
                "Capture pelo menos 3 amostras para substituir os vetores existentes."
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

                usuario.nome = nome
                usuario.matricula = matricula
                usuario.ativo = ativo

                sessao.commit()
                usuario_id = usuario.id

                if self.vetores_capturados:
                    excluir_vetores_faciais(usuario_id)

                    for vetor in self.vetores_capturados:
                        salvar_vetor_facial(
                            usuario_id,
                            vetor
                        )

            else:
                sessao.close()
                sessao = None

                usuario = cadastrar_usuario(
                    nome,
                    matricula,
                    vetores=self.vetores_capturados
                )

                usuario_id = usuario.id

            messagebox.showinfo(
                "Sucesso",
                "Usuário atualizado com sucesso."
                if self.usuario_id
                else "Usuário cadastrado com sucesso."
            )

        except IntegrityError:
            if sessao:
                sessao.rollback()

            messagebox.showerror(
                "Matrícula duplicada",
                "Já existe um usuário cadastrado com essa matrícula."
            )
            return

        except Exception as erro:
            if sessao:
                sessao.rollback()

            messagebox.showerror(
                "Erro",
                f"Não foi possível salvar o usuário:\n{erro}"
            )
            return

        finally:
            if sessao:
                sessao.close()

        self.vetores_capturados = []
        self.mostrar_visualizacao(usuario_id)
