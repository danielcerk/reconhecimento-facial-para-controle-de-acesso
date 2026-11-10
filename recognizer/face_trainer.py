
import json
import cv2
import numpy as np

from pathlib import Path

from access_control.db import obter_sessao, Usuario
from .face_detector import FaceDetector


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "data" / "recognizer"

MODEL_PATH = MODEL_DIR / "classificadorEigen.yml"
LABELS_PATH = MODEL_DIR / "labels.json"


def treinar_modelo():
    if not hasattr(cv2, "face"):
        raise RuntimeError(
            "OpenCV Contrib não está instalado. "
            "Instale opencv-contrib-python."
        )

    if not hasattr(cv2.face, "EigenFaceRecognizer_create"):
        raise RuntimeError(
            "O reconhecimento Eigenfaces não está disponível "
            "nesta instalação do OpenCV."
        )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    detector = FaceDetector()

    rostos = []
    labels = []
    mapeamento = {}

    with obter_sessao() as db:
        usuarios = db.query(Usuario).filter(
            Usuario.ativo.is_(True),
            Usuario.foto.isnot(None)
        ).order_by(Usuario.id).all()

        dados = [
            (usuario.id, usuario.foto)
            for usuario in usuarios
        ]

    label_atual = 0

    for usuario_id, caminho_foto in dados:
        caminho = Path(caminho_foto)

        if not caminho.is_file():
            continue

        imagem = cv2.imread(str(caminho))

        if imagem is None:
            continue

        cinza = detector.converter_cinza(imagem)

        encontrados = detector.detectar(cinza)

        if len(encontrados) == 0:
            continue

        # Seleciona o maior rosto encontrado.
        rosto_coords = max(
            encontrados,
            key=lambda item: item[2] * item[3]
        )

        rosto = detector.preparar_rosto(
            cinza,
            rosto_coords
        )

        if rosto is None:
            continue

        rostos.append(rosto)
        labels.append(label_atual)

        # Relaciona o label ao ID real do usuário.
        mapeamento[str(label_atual)] = int(usuario_id)

        label_atual += 1

    # Eigenfaces precisa de pelo menos duas imagens.
    if len(rostos) < 2:
        MODEL_PATH.unlink(missing_ok=True)
        LABELS_PATH.unlink(missing_ok=True)

        return {
            "sucesso": False,
            "quantidade": len(rostos),
            "mensagem": (
                "São necessárias pelo menos duas imagens "
                "válidas para treinar o modelo Eigenfaces."
            )
        }

    reconhecedor = cv2.face.EigenFaceRecognizer_create()

    reconhecedor.train(
        rostos,
        np.array(labels, dtype=np.int32)
    )

    reconhecedor.write(str(MODEL_PATH))

    with open(LABELS_PATH, "w", encoding="utf-8") as arquivo:
        json.dump(
            mapeamento,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    return {
        "sucesso": True,
        "quantidade": len(rostos),
        "mensagem": (
            f"Modelo Eigenfaces treinado com "
            f"{len(rostos)} imagens."
        )
    }
