
import json
import cv2

from pathlib import Path

from .face_detector import FaceDetector


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "data" / "recognizer"

MODEL_PATH = MODEL_DIR / "trainer.yml"
LABELS_PATH = MODEL_DIR / "labels.json"


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
            reconhecedor = cv2.face.LBPHFaceRecognizer_create()
            reconhecedor.read(str(MODEL_PATH))

            with open(LABELS_PATH, "r", encoding="utf-8") as arquivo:
                labels = json.load(arquivo)

            self.reconhecedor = reconhecedor
            self.labels = labels

            return True

        except Exception:
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

        if self.reconhecedor is None:
            return resultado

        rostos = self.detector.detectar(imagem)

        if len(rostos) == 0:
            return resultado

        # Considera o maior rosto da imagem.
        coordenadas = max(
            rostos,
            key=lambda item: item[2] * item[3]
        )

        rosto = self.detector.preparar_rosto(
            imagem,
            coordenadas
        )

        label, distancia = self.reconhecedor.predict(rosto)

        resultado["rosto"] = coordenadas
        resultado["distancia"] = float(distancia)

        usuario_id = self.labels.get(str(label))

        if usuario_id is not None and distancia <= 75:
            resultado["reconhecido"] = True
            resultado["usuario_id"] = int(usuario_id)

        return resultado
