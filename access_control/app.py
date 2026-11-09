
import tkinter as tk
from tkinter import ttk


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Simulador de Catraca")
        self.geometry("1200x750")
        self.minsize(950, 600)

        self.configure(bg="#f5f5f5")

        self.frames = {}
        self.tela_atual = None

        self.configurar_estilos()
        self.criar_layout()
        self.registrar_telas()

        self.mostrar_tela("dashboard")

    def configurar_estilos(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "Sidebar.TFrame",
            background="#20252b"
        )

        style.configure(
            "Sidebar.TLabel",
            background="#20252b",
            foreground="white",
            font=("Arial", 15, "bold")
        )

        style.configure(
            "Menu.TButton",
            font=("Arial", 10),
            padding=12,
            anchor="w"
        )

        style.configure(
            "Title.TLabel",
            font=("Arial", 22, "bold")
        )

        style.configure(
            "Treeview",
            rowheight=35,
            font=("Arial", 10)
        )

        style.configure(
            "Treeview.Heading",
            font=("Arial", 10, "bold")
        )

    def criar_layout(self):
        self.sidebar = ttk.Frame(
            self,
            style="Sidebar.TFrame",
            width=220
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ttk.Label(
            self.sidebar,
            text="SIMULADOR\nDE CATRACA",
            style="Sidebar.TLabel",
            justify="center"
        ).pack(fill="x", pady=30)

        self.criar_menu("Dashboard", "dashboard")
        self.criar_menu("Usuários", "usuarios")
        self.criar_menu("Acesso à catraca", "catraca")

        ttk.Frame(
            self.sidebar,
            style="Sidebar.TFrame"
        ).pack(expand=True, fill="both")

        ttk.Separator(
            self.sidebar
        ).pack(fill="x", padx=15, pady=10)

        self.criar_menu("Minha conta", "conta")

        self.container = ttk.Frame(self)
        self.container.pack(
            side="right",
            fill="both",
            expand=True
        )

    def criar_menu(self, texto, tela):
        ttk.Button(
            self.sidebar,
            text=texto,
            style="Menu.TButton",
            command=lambda: self.mostrar_tela(tela)
        ).pack(fill="x", padx=12, pady=3)

    def registrar_telas(self):
        from .views.dashboard import Dashboard
        from .views.user import Usuarios
        from .views.access import Catraca

        telas = {
            "dashboard": Dashboard,
            "usuarios": Usuarios,
            "catraca": Catraca
        }

        for nome, classe in telas.items():
            frame = classe(self.container, self)

            frame.place(
                x=0,
                y=0,
                relwidth=1,
                relheight=1
            )

            self.frames[nome] = frame

    def mostrar_tela(self, nome, **kwargs):
        if nome not in self.frames:
            raise ValueError(f"Tela não encontrada: {nome}")

        if self.tela_atual:
            atual = self.frames[self.tela_atual]

            if hasattr(atual, "ao_ocultar"):
                atual.ao_ocultar()

        frame = self.frames[nome]

        frame.tkraise()
        self.tela_atual = nome

        if hasattr(frame, "ao_mostrar"):
            frame.ao_mostrar(**kwargs)

    def abrir_usuario(self, usuario_id=None):
        self.mostrar_tela(
            "usuarios",
            usuario_id=usuario_id
        )

    def adicionar_tela(self, nome, classe):
        if nome in self.frames:
            return False

        frame = classe(self.container, self)

        frame.place(
            x=0,
            y=0,
            relwidth=1,
            relheight=1
        )

        self.frames[nome] = frame
        return True

    def remover_tela(self, nome):
        if nome not in self.frames:
            return False

        if self.tela_atual == nome:
            self.mostrar_tela("dashboard")

        self.frames[nome].destroy()
        del self.frames[nome]

        return True


if __name__ == "__main__":
    app = App()
    app.mainloop()
