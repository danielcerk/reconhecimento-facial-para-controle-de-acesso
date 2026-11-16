
import time

from access_control.db import (
    obter_sessao,
    Usuario,
    HistoricoAcesso
)

from recognizer.face_recognizer import FaceRecognizer


MOTIVO_LIBERACAO_INICIAL = "LIBERACAO_INICIAL_ADMIN"


class AccessService:

    def __init__(self, intervalo=8):
        self.recognizer = FaceRecognizer()
        self.intervalo = intervalo
        self.ultimos_registros = {}

    def recarregar_modelo(self):
        return self.recognizer.carregar_modelo()

    def reconstruir_modelo(self):
        quantidade = self.recognizer.carregar_modelo()

        return {
            "sucesso": True,
            "quantidade": self.recognizer.quantidade_vetores(),
            "mensagem": (
                f"Reconhecimento atualizado com "
                f"{self.recognizer.quantidade_vetores()} "
                f"vetores faciais."
                if quantidade
                else "Nenhum vetor facial cadastrado."
            )
        }

    def _registrar(self, usuario_id, autorizado, motivo):
        agora = time.monotonic()

        chave = (
            usuario_id
            if usuario_id is not None
            else "desconhecido"
        )

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

    def _obter_administrador_inicial(self, db):
        return (
            db.query(Usuario)
            .order_by(Usuario.id.asc())
            .first()
        )

    def _liberacao_inicial_disponivel(self, db):
        registro = (
            db.query(HistoricoAcesso)
            .filter(
                HistoricoAcesso.motivo == MOTIVO_LIBERACAO_INICIAL
            )
            .first()
        )

        return registro is None

    def _processar_primeiro_acesso(self, reconhecimento):
        embedding = reconhecimento.get("embedding")

        if embedding is None:
            return None

        with obter_sessao() as db:
            administrador = self._obter_administrador_inicial(db)

            if administrador is None:
                return None

            possui_vetores = self.recognizer.possui_vetores_usuario(
                administrador.id
            )

            if possui_vetores:
                return None

            if not self._liberacao_inicial_disponivel(db):
                return None

            administrador_id = administrador.id
            nome = administrador.nome
            matricula = administrador.matricula
            ativo = administrador.ativo

        if not ativo:
            return {
                "status": "negado",
                "nome": nome,
                "matricula": matricula,
                "usuario_id": administrador_id,
                "distancia": None,
                "rosto": reconhecimento["rosto"],
                "registrado": False,
                "motivo": "Administrador inicial inativo"
            }

        registrado = self._registrar(
            administrador_id,
            True,
            MOTIVO_LIBERACAO_INICIAL
        )

        if not registrado:
            return None

        return {
            "status": "cadastro_admin",
            "nome": nome,
            "matricula": matricula,
            "usuario_id": administrador_id,
            "distancia": None,
            "rosto": reconhecimento["rosto"],
            "registrado": True,
            "motivo": (
                "Primeiro acesso liberado. "
                "Cadastre imediatamente a face do administrador."
            )
        }

    def processar_frame(self, frame):
        reconhecimento = self.recognizer.reconhecer(frame)

        resultado = {
            "status": "desconhecido",
            "nome": None,
            "matricula": None,
            "usuario_id": None,
            "distancia": reconhecimento["distancia"],
            "similaridade": reconhecimento.get("similaridade"),
            "rosto": reconhecimento["rosto"],
            "registrado": False,
            "motivo": "Rosto não reconhecido"
        }

        if not reconhecimento["reconhecido"]:
            primeiro_acesso = self._processar_primeiro_acesso(
                reconhecimento
            )

            if primeiro_acesso is not None:
                return primeiro_acesso

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

            ativo = usuario.ativo

        resultado["registrado"] = self._registrar(
            usuario_id,
            ativo,
            resultado["motivo"]
        )

        return resultado
