
import cv2
import numpy as np

from insightface.app import FaceAnalysis

from access_control.db import (
    obter_sessao,
    Usuario,
    VetorFacial,
    converter_bytes_vetor
)

from .face_detector import FaceDetector


SIMILARIDADE_MINIMA = 0.45

face_analysis = None


def obter_modelo_facial():
    global face_analysis

    if face_analysis is None:
        face_analysis = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )

        face_analysis.prepare(
            ctx_id=-1,
            det_size=(640, 640)
        )

    return face_analysis


class FaceRecognizer:

    def __init__(self):
        self.detector = FaceDetector()
        self.vetores = []
        self.carregar_modelo()

    def carregar_modelo(self):
        novos_vetores = []

        with obter_sessao() as db:
            registros = (
                db.query(VetorFacial)
                .join(Usuario, Usuario.id == VetorFacial.usuario_id)
                .filter(Usuario.ativo.is_(True))
                .all()
            )

            for registro in registros:
                try:
                    vetor = converter_bytes_vetor(registro.vetor)
                    vetor = np.asarray(vetor, dtype=np.float32)

                    if vetor.shape != (512,):
                        continue

                    if not np.all(np.isfinite(vetor)):
                        continue

                    norma = np.linalg.norm(vetor)

                    if norma == 0:
                        continue

                    novos_vetores.append({
                        "usuario_id": registro.usuario_id,
                        "vetor": vetor / norma
                    })

                except Exception:
                    continue

        self.vetores = novos_vetores

        return bool(self.vetores)

    def quantidade_vetores(self):
        return len(self.vetores)

    def possui_vetores_usuario(self, usuario_id):
        return any(
            item["usuario_id"] == usuario_id
            for item in self.vetores
        )

    def extrair_embedding(self, imagem):
        if imagem is None:
            return None, None

        faces = obter_modelo_facial().get(imagem)

        if not faces:
            return None, None

        face = max(
            faces,
            key=lambda item: (
                item.bbox[2] - item.bbox[0]
            ) * (
                item.bbox[3] - item.bbox[1]
            )
        )

        embedding = np.asarray(
            face.normed_embedding,
            dtype=np.float32
        )

        if embedding.shape != (512,):
            return None, None

        if not np.all(np.isfinite(embedding)):
            return None, None

        norma = np.linalg.norm(embedding)

        if norma == 0:
            return None, None

        embedding = embedding / norma

        bbox = face.bbox.astype(int)

        x1, y1, x2, y2 = bbox

        rosto = (
            int(x1),
            int(y1),
            int(x2 - x1),
            int(y2 - y1)
        )

        return embedding, rosto

    def reconhecer(self, imagem):
        resultado = {
            "reconhecido": False,
            "usuario_id": None,
            "similaridade": None,
            "distancia": None,
            "rosto": None,
            "embedding": None
        }

        if imagem is None:
            return resultado

        embedding, rosto = self.extrair_embedding(imagem)

        if embedding is None:
            return resultado

        resultado["rosto"] = rosto
        resultado["embedding"] = embedding

        if not self.vetores:
            return resultado

        melhores_resultados = {}

        for registro in self.vetores:
            vetor_cadastrado = registro["vetor"]

            similaridade = float(
                np.dot(embedding, vetor_cadastrado)
            )

            usuario_id = registro["usuario_id"]

            atual = melhores_resultados.get(usuario_id)

            if atual is None or similaridade > atual:
                melhores_resultados[usuario_id] = similaridade

        if not melhores_resultados:
            return resultado

        usuario_id, similaridade = max(
            melhores_resultados.items(),
            key=lambda item: item[1]
        )

        distancia = 1.0 - similaridade

        resultado["similaridade"] = similaridade
        resultado["distancia"] = distancia

        if similaridade >= SIMILARIDADE_MINIMA:
            resultado["reconhecido"] = True
            resultado["usuario_id"] = usuario_id

        return resultado
