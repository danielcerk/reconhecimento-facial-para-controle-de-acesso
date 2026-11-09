
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = "sqlite:///sistema_catraca.db"

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
    foto = Column(String(500), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.now)

    acessos = relationship(
        "HistoricoAcesso",
        back_populates="usuario",
        cascade="all, delete-orphan"
    )


class HistoricoAcesso(Base):
    __tablename__ = "historico_acessos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=True
    )
    data_hora = Column(DateTime, default=datetime.now, nullable=False)
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


def cadastrar_usuario(nome, matricula, foto=None):
    with obter_sessao() as db:
        usuario = Usuario(
            nome=nome,
            matricula=matricula,
            foto=foto
        )

        db.add(usuario)
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

        return acesso.id


def listar_historico(limite=100):
    with obter_sessao() as db:
        return db.query(HistoricoAcesso).order_by(
            HistoricoAcesso.data_hora.desc()
        ).limit(limite).all()


def atualizar_usuario(usuario_id, **dados):
    campos_permitidos = {
        "nome", "matricula", "foto", "ativo"
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
    print("Banco de dados inicializado!")
