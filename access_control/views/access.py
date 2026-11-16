
import tkinter as tk
from tkinter import ttk, messagebox
import time

import cv2

from PIL import Image, ImageTk

from access_control.access_service import AccessService


class Catraca(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app
        self.camera = None
        self.ativo = False
        self.after_id = None

        self.servico = AccessService()

        self.ultimo_processamento = 0
        self.intervalo_processamento = 0.5

        self.criar_interface()

    def criar_interface(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        topo = ttk.Frame(self, padding=15)
        topo.grid(row=0, column=0, sticky="ew")

        ttk.Label(
            topo,
            text="Controle de acesso",
            font=("Arial", 18, "bold")
        ).pack(side="left")

        self.status_camera = ttk.Label(
            topo,
            text="Câmera desligada"
        )
        self.status_camera.pack(side="right")

        conteudo = ttk.Frame(self, padding=15)
        conteudo.grid(row=1, column=0, sticky="nsew")

        conteudo.columnconfigure(0, weight=3)
        conteudo.columnconfigure(1, weight=1)
        conteudo.rowconfigure(0, weight=1)

        camera_frame = ttk.LabelFrame(
            conteudo,
            text="Câmera",
            padding=10
        )
        camera_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 10)
        )

        camera_frame.rowconfigure(0, weight=1)
        camera_frame.columnconfigure(0, weight=1)

        self.camera_label = ttk.Label(
            camera_frame,
            text="Aguardando câmera..."
        )
        self.camera_label.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        painel = ttk.LabelFrame(
            conteudo,
            text="Resultado da identificação",
            padding=15
        )
        painel.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        self.nome_var = tk.StringVar(
            value="Aguardando identificação"
        )
        self.matricula_var = tk.StringVar(value="-")
        self.resultado_var = tk.StringVar(
            value="Aguardando rosto"
        )
        self.motivo_var = tk.StringVar(value="-")

        ttk.Label(painel, text="Nome").pack(anchor="w")

        ttk.Label(
            painel,
            textvariable=self.nome_var,
            font=("Arial", 13, "bold"),
            wraplength=220
        ).pack(anchor="w", pady=(3, 15))

        ttk.Label(painel, text="Matrícula").pack(anchor="w")

        ttk.Label(
            painel,
            textvariable=self.matricula_var
        ).pack(anchor="w", pady=(3, 15))

        ttk.Label(painel, text="Status").pack(anchor="w")

        self.resultado_label = ttk.Label(
            painel,
            textvariable=self.resultado_var,
            font=("Arial", 13, "bold")
        )
        self.resultado_label.pack(anchor="w", pady=(3, 15))

        ttk.Label(painel, text="Motivo").pack(anchor="w")

        ttk.Label(
            painel,
            textvariable=self.motivo_var,
            wraplength=220
        ).pack(anchor="w", pady=(3, 15))


    def ao_mostrar(self, **kwargs):
        self.iniciar_camera()

    def ao_ocultar(self):
        self.parar_camera()

    def iniciar_camera(self):
        if self.ativo:
            return

        try:
            self.camera = cv2.VideoCapture(0)

            if not self.camera.isOpened():
                self.camera.release()
                self.camera = None

                messagebox.showerror(
                    "Câmera",
                    "Não foi possível abrir a webcam."
                )
                return

            self.ativo = True
            self.status_camera.config(text="Câmera ativa")

            self.atualizar_frame()

        except Exception as erro:
            self.parar_camera()

            messagebox.showerror("Erro", str(erro))

    def parar_camera(self):
        self.ativo = False

        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None

        if self.camera:
            self.camera.release()
            self.camera = None

        self.camera_label.configure(
            image="",
            text="Câmera desligada"
        )

        self.camera_label.image = None
        self.status_camera.config(text="Câmera desligada")

    def atualizar_frame(self):
        if not self.ativo or not self.camera:
            return

        sucesso, frame = self.camera.read()

        if not sucesso:
            self.status_camera.config(text="Erro na câmera")
            self.after_id = self.after(100, self.atualizar_frame)
            return

        agora = time.monotonic()

        if agora - self.ultimo_processamento >= self.intervalo_processamento:
            self.ultimo_processamento = agora

            try:
                resultado = self.servico.processar_frame(frame)

                if self.atualizar_resultado(resultado):
                    return

            except Exception as erro:
                self.motivo_var.set(str(erro))

        detector = self.servico.recognizer.detector
        rostos = detector.detectar(frame)

        for x, y, largura, altura in rostos:
            cv2.rectangle(
                frame,
                (x, y),
                (x + largura, y + altura),
                (0, 180, 0),
                2
            )

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        imagem = Image.fromarray(frame)
        imagem.thumbnail((900, 600))

        foto = ImageTk.PhotoImage(imagem)

        self.camera_label.configure(image=foto, text="")
        self.camera_label.image = foto

        if self.ativo:
            self.after_id = self.after(30, self.atualizar_frame)

    def atualizar_resultado(self, resultado):
        status = resultado.get("status")

        self.nome_var.set(
            resultado.get("nome") or "Desconhecido"
        )

        self.matricula_var.set(
            resultado.get("matricula") or "-"
        )

        self.motivo_var.set(
            resultado.get("motivo") or "-"
        )

        if status == "autorizado":
            self.resultado_var.set("ACESSO AUTORIZADO")
            self.resultado_label.configure(foreground="green")

            self.app.liberar_acesso()
            return True

        elif status == "negado":
            self.resultado_var.set("ACESSO NEGADO")
            self.resultado_label.configure(foreground="red")

        elif status in ("cadastro_administrador", "cadastro_admin"):
            self.nome_var.set(
                resultado.get("nome") or "Administrador"
            )

            self.matricula_var.set("0001")
            self.resultado_var.set("CADASTRO INICIAL")

            self.motivo_var.set(
                "Primeiro acesso. Administrador precisa cadastrar "
                "seus dados faciais."
            )

            self.resultado_label.configure(foreground="blue")

        elif resultado.get("rosto") is not None:
            self.resultado_var.set("NÃO RECONHECIDO")
            self.resultado_label.configure(foreground="red")

        else:
            self.nome_var.set("Aguardando identificação")
            self.matricula_var.set("-")
            self.resultado_var.set("Aguardando rosto")
            self.motivo_var.set("-")

            self.resultado_label.configure(foreground="gray")

        return False

    def atualizar_modelo(self):
        try:
            resultado = self.servico.reconstruir_modelo()

            messagebox.showinfo(
                "Reconhecimento facial",
                resultado["mensagem"]
            )

        except Exception as erro:
            messagebox.showerror(
                "Erro no treinamento",
                str(erro)
            )
