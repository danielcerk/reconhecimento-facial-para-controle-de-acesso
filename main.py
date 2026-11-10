
from access_control.app import App

from access_control.db import (
    criar_tabelas,
    inicializar_primeiro_usuario
)

from recognizer.face_trainer import treinar_modelo


def iniciar():

    print("Inicializando banco de dados...")

    criar_tabelas()

    print("Verificando primeiro usuário...")

    inicializar_primeiro_usuario()

    try:
        treinar_modelo()

    except Exception as erro:
        print(f"Erro ao treinar reconhecimento facial: {erro}")

    print("Iniciando aplicação...")

    app = App()
    app.mainloop()


if __name__ == "__main__":
    iniciar()
