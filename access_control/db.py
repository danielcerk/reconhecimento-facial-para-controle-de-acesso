
from datetime import datetime
from pathlib import Path

import numpy as np

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    LargeBinary,
    inspect
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


BASE_DIR = Path(__file__).resolve().parent

DATABASE_URL = "sqlite:///sistema_catraca.db"

PRIMEIRO_USUARIO = {
    "nome": "Administrador",
    "matricula": "0001",
    "ativo": True
}


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    matricula = Column(String(50), unique=True, nullable=False)

    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.now)

    acessos = relationship(
        "HistoricoAcesso",
        back_populates="usuario",
        cascade="all, delete-orphan"
    )

    vetores_faciais = relationship(
        "VetorFacial",
        back_populates="usuario",
        cascade="all, delete-orphan"
    )


class VetorFacial(Base):
    __tablename__ = "vetores_faciais"

    id = Column(Integer, primary_key=True, index=True)

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    vetor = Column(LargeBinary, nullable=False)

    criado_em = Column(
        DateTime,
        default=datetime.now,
        nullable=False
    )

    usuario = relationship(
        "Usuario",
        back_populates="vetores_faciais"
    )


class HistoricoAcesso(Base):
    __tablename__ = "historico_acessos"

    id = Column(Integer, primary_key=True, index=True)

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=True
    )

    data_hora = Column(
        DateTime,
        default=datetime.now,
        nullable=False
    )

    autorizado = Column(Boolean, nullable=False)
    motivo = Column(String(255), nullable=True)

    usuario = relationship(
        "Usuario",
        back_populates="acessos"
    )

def criar_tabelas():
    Base.metadata.create_all(bind=engine)


def obter_sessao():
    return SessionLocal()

def converter_vetor_bytes(vetor):
    vetor = np.asarray(vetor, dtype=np.float32)

    if vetor.ndim != 1 or vetor.size == 0:
        raise ValueError("Vetor facial inválido.")

    if not np.all(np.isfinite(vetor)):
        raise ValueError("O vetor contém valores inválidos.")

    return vetor.tobytes()


def converter_bytes_vetor(dados):
    return np.frombuffer(
        dados,
        dtype=np.float32
    ).copy()

def salvar_vetor_facial(usuario_id, vetor):

    vetor_bytes = converter_vetor_bytes(vetor)

    with obter_sessao() as db:

        usuario = db.get(Usuario, usuario_id)

        if not usuario:
            raise ValueError("Usuário não encontrado.")

        registro = VetorFacial(
            usuario_id=usuario_id,
            vetor=vetor_bytes
        )

        db.add(registro)
        db.commit()
        db.refresh(registro)

        return registro.id


def listar_vetores_faciais(usuario_id):

    with obter_sessao() as db:

        registros = db.query(VetorFacial).filter(
            VetorFacial.usuario_id == usuario_id
        ).all()

        return [
            converter_bytes_vetor(registro.vetor)
            for registro in registros
        ]


def listar_todos_vetores_faciais():

    with obter_sessao() as db:

        registros = db.query(VetorFacial).join(
            Usuario
        ).filter(
            Usuario.ativo.is_(True)
        ).all()

        return [
            {
                "id": registro.id,
                "usuario_id": registro.usuario_id,
                "vetor": converter_bytes_vetor(registro.vetor)
            }
            for registro in registros
        ]


def excluir_vetores_faciais(usuario_id):

    with obter_sessao() as db:

        db.query(VetorFacial).filter(
            VetorFacial.usuario_id == usuario_id
        ).delete(synchronize_session=False)

        db.commit()


def inicializar_primeiro_usuario():

    dados = PRIMEIRO_USUARIO.copy()

    with obter_sessao() as db:

        usuario = db.query(Usuario).order_by(
            Usuario.id.asc()
        ).first()

        if usuario is None:

            usuario = Usuario(**dados)

            db.add(usuario)
            db.commit()
            db.refresh(usuario)

            print(f"Administrador criado! ID: {usuario.id}")

            return usuario.id

        alterado = False

        for campo, valor in dados.items():

            if getattr(usuario, campo) != valor:
                setattr(usuario, campo, valor)
                alterado = True

        if alterado:
            db.commit()
            print("Administrador atualizado!")

        return usuario.id

def cadastrar_usuario(nome, matricula, vetores=None):

    with obter_sessao() as db:

        usuario = Usuario(
            nome=nome,
            matricula=matricula
        )

        db.add(usuario)
        db.flush()

        if vetores is not None:

            for vetor in vetores:

                registro = VetorFacial(
                    usuario_id=usuario.id,
                    vetor=converter_vetor_bytes(vetor)
                )

                db.add(registro)

        db.commit()
        db.refresh(usuario)

        return usuario.id

def buscar_usuario(matricula):

    with obter_sessao() as db:

        return db.query(Usuario).filter(
            Usuario.matricula == matricula
        ).first()


def listar_usuarios():

    with obter_sessao() as db:

        return db.query(Usuario).order_by(
            Usuario.nome
        ).all()

def registrar_acesso(usuario_id, autorizado, motivo=None):

    with obter_sessao() as db:

        acesso = HistoricoAcesso(
            usuario_id=usuario_id,
            autorizado=autorizado,
            motivo=motivo
        )

        db.add(acesso)
        db.commit()
        db.refresh(acesso)

        return acesso.id


def listar_historico(limite=100):

    with obter_sessao() as db:

        return db.query(HistoricoAcesso).order_by(
            HistoricoAcesso.data_hora.desc()
        ).limit(limite).all()

def atualizar_usuario(usuario_id, **dados):

    campos_permitidos = {
        "nome",
        "matricula",
        "ativo"
    }

    with obter_sessao() as db:

        usuario = db.get(Usuario, usuario_id)

        if not usuario:
            return False

        for campo, valor in dados.items():

            if campo in campos_permitidos:
                setattr(usuario, campo, valor)

        db.commit()

        return True

def excluir_usuario(usuario_id):

    with obter_sessao() as db:

        usuario = db.get(Usuario, usuario_id)

        if not usuario:
            return False

        db.delete(usuario)
        db.commit()

        return True

if __name__ == "__main__":

    criar_tabelas()

    inicializar_primeiro_usuario()

    print("Banco de dados inicializado!")
