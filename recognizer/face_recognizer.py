
import json
import cv2

from pathlib import Path

from .face_detector import FaceDetector


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "data" / "recognizer"

MODEL_PATH = MODEL_DIR / "classificadorEigen.yml"
LABELS_PATH = MODEL_DIR / "labels.json"

# Valor inicial experimental.
# Deve ser calibrado com imagens reais do seu sistema.
DISTANCIA_MAXIMA = 5000.0


class FaceRecognizer:
    def __init__(self):
        self.detector = FaceDetector()

        self.reconhecedor = None
        self.labels = {}

        self.carregar_modelo()

    def carregar_modelo(self):
        if not MODEL_PATH.is_file() or not LABELS_PATH.is_file():
            self.reconhecedor = None
            self.labels = {}
            return False

        try:
            reconhecedor = cv2.face.EigenFaceRecognizer_create()

            reconhecedor.read(str(MODEL_PATH))

            with open(LABELS_PATH, "r", encoding="utf-8") as arquivo:
                labels = json.load(arquivo)

            self.reconhecedor = reconhecedor
            self.labels = labels

            return True

        except Exception as erro:
            print(f"Erro ao carregar modelo Eigenfaces: {erro}")

            self.reconhecedor = None
            self.labels = {}

            return False

    def reconhecer(self, imagem):
        resultado = {
            "reconhecido": False,
            "usuario_id": None,
            "distancia": None,
            "rosto": None
        }

        if imagem is None:
            return resultado

        cinza = self.detector.converter_cinza(imagem)

        rostos = self.detector.detectar(cinza)

        if len(rostos) == 0:
            return resultado

        # Seleciona o maior rosto da imagem.
        coordenadas = max(
            rostos,
            key=lambda item: item[2] * item[3]
        )

        resultado["rosto"] = coordenadas

        if self.reconhecedor is None:
            return resultado

        rosto = self.detector.preparar_rosto(
            cinza,
            coordenadas
        )

        if rosto is None:
            return resultado

        try:
            label, distancia = self.reconhecedor.predict(rosto)

            distancia = float(distancia)

            resultado["distancia"] = distancia

            usuario_id = self.labels.get(str(label))

            if (
                usuario_id is not None
                and distancia <= DISTANCIA_MAXIMA
            ):
                resultado["reconhecido"] = True
                resultado["usuario_id"] = int(usuario_id)

        except cv2.error as erro:
            print(f"Erro durante o reconhecimento facial: {erro}")

        return resultado
