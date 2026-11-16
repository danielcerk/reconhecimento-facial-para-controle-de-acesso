
import cv2
import numpy as np

from pathlib import Path


class FaceDetector:

    def __init__(self):
        base_dir = Path(__file__).resolve().parent

        caminho = (
            base_dir
            / "cascades"
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

        self.clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

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

    def normalizar_iluminacao(self, imagem):
        if imagem is None:
            return None

        cinza = self.converter_cinza(imagem)

        # Estima a iluminação de fundo.
        fundo = cv2.GaussianBlur(
            cinza,
            (0, 0),
            sigmaX=15
        )

        # Corrige variações de iluminação.
        normalizada = cv2.divide(
            cinza,
            fundo,
            scale=128
        )

        return cv2.normalize(
            normalizada,
            None,
            0,
            255,
            cv2.NORM_MINMAX
        )

    def equalizar_histograma(self, imagem):
        if imagem is None:
            return None

        return self.clahe.apply(imagem)

    def preprocessar(self, imagem):
        if imagem is None:
            return None

        cinza = self.converter_cinza(imagem)

        normalizada = self.normalizar_iluminacao(cinza)

        equalizada = self.equalizar_histograma(normalizada)

        return equalizada

    def detectar(self, imagem):
        if imagem is None:
            return []

        cinza = self.converter_cinza(imagem)

        rostos = self.cascade.detectMultiScale(
            cinza,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(100, 100)
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

        rosto = self.preprocessar(rosto)

        return rosto
