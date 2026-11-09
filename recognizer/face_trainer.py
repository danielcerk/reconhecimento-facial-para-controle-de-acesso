
import json
import cv2

from pathlib import Path

from access_control.db import obter_sessao, Usuario
from .face_detector import FaceDetector


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "data" / "recognizer"

MODEL_PATH = MODEL_DIR / "trainer.yml"
LABELS_PATH = MODEL_DIR / "labels.json"


def treinar_modelo():
    if not hasattr(cv2, "face"):
        raise RuntimeError(
            "OpenCV Contrib não está instalado. "
            "Instale opencv-contrib-python."
        )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    detector = FaceDetector()

    rostos = []
    labels = []
    mapeamento = {}

    label_atual = 0

    with obter_sessao() as db:
        usuarios = db.query(Usuario).filter(
            Usuario.ativo.is_(True),
            Usuario.foto.isnot(None)
        ).all()

        dados = [
            (usuario.id, usuario.foto)
            for usuario in usuarios
        ]

    for usuario_id, caminho_foto in dados:
        caminho = Path(caminho_foto)

        if not caminho.is_file():
            continue

        imagem = cv2.imread(str(caminho))

        if imagem is None:
            continue

        encontrados = detector.detectar(imagem)

        if len(encontrados) == 0:
            continue

        # Utiliza o maior rosto encontrado na foto.
        rosto_coords = max(
            encontrados,
            key=lambda item: item[2] * item[3]
        )

        rosto = detector.preparar_rosto(
            imagem,
            rosto_coords
        )

        rostos.append(rosto)
        labels.append(label_atual)

        mapeamento[str(label_atual)] = usuario_id
        label_atual += 1

    if not rostos:
        MODEL_PATH.unlink(missing_ok=True)
        LABELS_PATH.unlink(missing_ok=True)

        return {
            "sucesso": False,
            "quantidade": 0,
            "mensagem": "Nenhuma foto válida encontrada."
        }

    reconhecedor = cv2.face.LBPHFaceRecognizer_create(
        radius=1,
        neighbors=8,
        grid_x=8,
        grid_y=8,
        threshold=75
    )

    reconhecedor.train(
        rostos,
        __import__("numpy").array(labels)
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
        "mensagem": f"{len(rostos)} rostos treinados."
    }
