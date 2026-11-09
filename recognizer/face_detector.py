
import cv2


class FaceDetector:
    def __init__(self):
        caminho = (
            cv2.data.haarcascades
            + "haarcascade_frontalface_default.xml"
        )

        self.cascade = cv2.CascadeClassifier(caminho)

        if self.cascade.empty():
            raise RuntimeError("Não foi possível carregar o detector facial.")

    def detectar(self, imagem):
        if imagem is None:
            return []

        escala = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)

        rostos = self.cascade.detectMultiScale(
            escala,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(80, 80)
        )

        return rostos

    def preparar_rosto(self, imagem, coordenadas):
        x, y, largura, altura = coordenadas

        cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        rosto = cinza[y:y + altura, x:x + largura]

        rosto = cv2.resize(rosto, (200, 200))

        return rosto
