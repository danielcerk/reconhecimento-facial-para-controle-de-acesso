
import numpy as np

from access_control.db import obter_sessao, Usuario


def treinar_modelo():
    with obter_sessao() as db:
        usuarios = db.query(Usuario).filter(
            Usuario.ativo.is_(True)
        ).order_by(Usuario.id).all()

        quantidade = 0
        embeddings = []

        for usuario in usuarios:
            embedding = getattr(usuario, "embedding", None)

            if not embedding:
                continue

            try:
                vetor = np.asarray(
                    embedding,
                    dtype=np.float32
                ).flatten()

                if vetor.shape != (512,):
                    continue

                if not np.all(np.isfinite(vetor)):
                    continue

                norma = np.linalg.norm(vetor)

                if norma == 0:
                    continue

                embeddings.append({
                    "usuario_id": usuario.id,
                    "embedding": (vetor / norma).tolist()
                })

                quantidade += 1

            except (ValueError, TypeError):
                continue

    return {
        "sucesso": quantidade > 0,
        "quantidade": quantidade,
        "mensagem": (
            f"{quantidade} embeddings faciais carregados."
            if quantidade
            else "Nenhum embedding facial válido encontrado."
        ),
        "embeddings": embeddings
    }
