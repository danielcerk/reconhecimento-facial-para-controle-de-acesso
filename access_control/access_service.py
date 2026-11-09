
import time

from access_control.db import obter_sessao, Usuario, HistoricoAcesso
from recognizer.face_recognizer import FaceRecognizer


class AccessService:
    def __init__(self, intervalo=8):
        self.recognizer = FaceRecognizer()
        self.intervalo = intervalo
        self.ultimos_registros = {}

    def recarregar_modelo(self):
        return self.recognizer.carregar_modelo()

    def reconstruir_modelo(self):
        from ..recognizer.face_trainer import treinar_modelo

        resultado = treinar_modelo()

        if resultado["sucesso"]:
            self.recarregar_modelo()

        return resultado

    def _registrar(self, usuario_id, autorizado, motivo):
        agora = time.monotonic()
        chave = usuario_id if usuario_id is not None else "desconhecido"

        ultimo = self.ultimos_registros.get(chave, 0)

        if agora - ultimo < self.intervalo:
            return False

        with obter_sessao() as db:
            acesso = HistoricoAcesso(
                usuario_id=usuario_id,
                autorizado=autorizado,
                motivo=motivo
            )

            db.add(acesso)
            db.commit()

        self.ultimos_registros[chave] = agora

        return True

    def processar_frame(self, frame):
        reconhecimento = self.recognizer.reconhecer(frame)

        resultado = {
            "status": "desconhecido",
            "nome": None,
            "matricula": None,
            "usuario_id": None,
            "distancia": reconhecimento["distancia"],
            "rosto": reconhecimento["rosto"],
            "registrado": False,
            "motivo": "Rosto não reconhecido"
        }

        if not reconhecimento["reconhecido"]:
            if reconhecimento["rosto"] is not None:
                resultado["registrado"] = self._registrar(
                    None,
                    False,
                    "Rosto não reconhecido"
                )

            return resultado

        usuario_id = reconhecimento["usuario_id"]

        with obter_sessao() as db:
            usuario = db.get(Usuario, usuario_id)

            if usuario is None:
                resultado["registrado"] = self._registrar(
                    None,
                    False,
                    "Usuário não encontrado"
                )
                resultado["motivo"] = "Usuário não encontrado"
                return resultado

            resultado["nome"] = usuario.nome
            resultado["matricula"] = usuario.matricula
            resultado["usuario_id"] = usuario.id

            if not usuario.ativo:
                resultado["status"] = "negado"
                resultado["motivo"] = "Usuário inativo"

            else:
                resultado["status"] = "autorizado"
                resultado["motivo"] = "Acesso autorizado"

            nome = usuario.nome
            matricula = usuario.matricula
            ativo = usuario.ativo

        resultado["registrado"] = self._registrar(
            usuario_id,
            ativo,
            resultado["motivo"]
        )

        return resultado
