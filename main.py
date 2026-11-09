from access_control.app import App

from access_control.db import criar_tabelas
from recognizer.face_trainer import treinar_modelo

def iniciar():
    criar_tabelas()

    try:
        treinar_modelo()
    except Exception as erro:
        print(f"Erro ao treinar reconhecimento facial: {erro}")

    app = App()
    app.mainloop()


if __name__ == "__main__":
    iniciar()