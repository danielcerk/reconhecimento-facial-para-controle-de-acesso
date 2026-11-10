
import cv2
from pathlib import Path


class FaceDetector:
    def __init__(self):
        pasta_projeto = Path(__file__).resolve().parent.parent

        caminho = (
            pasta_projeto
            / "data"
            / "haarcascade_frontalface_default.xml"
        )

        if not caminho.is_file():
            raise FileNotFoundError(
                f"Arquivo do detector facial não encontrado: {caminho}"
            )

        self.cascade = cv2.CascadeClassifier(str(caminho))

        if self.cascade.empty():
            raise RuntimeError(
                "Não foi possível carregar o detector facial."
            )

        self.tamanho_rosto = (200, 200)

    def converter_cinza(self, imagem):
        if imagem is None:
            return None

        if len(imagem.shape) == 2:
            return imagem

        if len(imagem.shape) == 3:
            return cv2.cvtColor(
                imagem,
                cv2.COLOR_BGR2GRAY
            )

        raise ValueError("Formato de imagem inválido.")

    def detectar(self, imagem):
        if imagem is None:
            return []

        cinza = self.converter_cinza(imagem)

        rostos = self.cascade.detectMultiScale(
            cinza,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(80, 80)
        )

        return rostos

    def preparar_rosto(self, imagem, coordenadas):
        if imagem is None:
            return None

        x, y, largura, altura = coordenadas

        cinza = self.converter_cinza(imagem)

        rosto = cinza[
            y:y + altura,
            x:x + largura
        ]

        if rosto.size == 0:
            return None

        rosto = cv2.resize(
            rosto,
            self.tamanho_rosto,
            interpolation=cv2.INTER_AREA
        )

        return rosto
