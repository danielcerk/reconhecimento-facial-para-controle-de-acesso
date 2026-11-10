
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import shutil

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    inspect
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


# ==========================================
# CONFIGURAÇÕES
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE_URL = "sqlite:///sistema_catraca.db"

PASTA_FOTOS = BASE_DIR / "fotos"

PRIMEIRO_USUARIO = {
    "nome": "Administrador",
    "matricula": "0001",
    "foto": str(BASE_DIR / "imagens" / "administrador.png"),
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


# ==========================================
# MODELOS
# ==========================================

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    matricula = Column(String(50), unique=True, nullable=False)
    foto = Column(String(500), nullable=True)
    foto_origem = Column(String(500), nullable=True)

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


# ==========================================
# INICIALIZAÇÃO DO BANCO
# ==========================================

def criar_tabelas():
    Base.metadata.create_all(bind=engine)

    # Compatibilidade com bancos já existentes
    colunas = [
        coluna["name"]
        for coluna in inspect(engine).get_columns("usuarios")
    ]

    if "foto_origem" not in colunas:
        with engine.begin() as conexao:
            conexao.exec_driver_sql(
                "ALTER TABLE usuarios ADD COLUMN foto_origem VARCHAR(500)"
            )


def obter_sessao():
    return SessionLocal()


# ==========================================
# GERENCIAMENTO DE FOTOS
# ==========================================

def salvar_foto(caminho_origem):
    if not caminho_origem:
        return None

    origem = Path(caminho_origem)

    if not origem.is_file():
        raise FileNotFoundError(
            f"Foto não encontrada: {caminho_origem}"
        )

    PASTA_FOTOS.mkdir(parents=True, exist_ok=True)

    # Nome aleatório para a imagem
    nome_aleatorio = f"{uuid4().hex}{origem.suffix}"

    destino = PASTA_FOTOS / nome_aleatorio

    shutil.copy2(origem, destino)

    return str(destino)


# ==========================================
# PRIMEIRO USUÁRIO AUTOMÁTICO
# ==========================================


def inicializar_primeiro_usuario():

    dados = PRIMEIRO_USUARIO.copy()

    with obter_sessao() as db:

        usuario = db.query(Usuario).order_by(
            Usuario.id.asc()
        ).first()

        # Se não existir nenhum usuário, cria o administrador
        if usuario is None:

            caminho_foto = None

            if dados.get("foto"):
                caminho_foto = salvar_foto(dados["foto"])

            usuario = Usuario(
                nome=dados["nome"],
                matricula=dados["matricula"],
                foto=caminho_foto,
                foto_origem=dados.get("foto"),
                ativo=dados["ativo"]
            )

            db.add(usuario)
            db.commit()
            db.refresh(usuario)

            print(f"Administrador criado! ID: {usuario.id}")

            return usuario.id

        # Se já existir, verifica alterações
        alterado = False

        for campo in ("nome", "matricula", "ativo"):

            if getattr(usuario, campo) != dados[campo]:
                setattr(usuario, campo, dados[campo])
                alterado = True

        nova_origem = dados.get("foto")

        if usuario.foto_origem != nova_origem:

            nova_foto = None

            if nova_origem:
                nova_foto = salvar_foto(nova_origem)

            usuario.foto = nova_foto
            usuario.foto_origem = nova_origem

            alterado = True

        if alterado:
            db.commit()
            print("Administrador atualizado!")
        else:
            print("Administrador já está atualizado!")

        return usuario.id



# ==========================================
# CADASTRO DE USUÁRIO
# ==========================================

def cadastrar_usuario(nome, matricula, foto=None):

    caminho_foto = salvar_foto(foto) if foto else None

    with obter_sessao() as db:

        usuario = Usuario(
            nome=nome,
            matricula=matricula,
            foto=caminho_foto,
            foto_origem=foto
        )

        db.add(usuario)
        db.commit()
        db.refresh(usuario)

        return usuario.id


# ==========================================
# CONSULTAS
# ==========================================

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


# ==========================================
# HISTÓRICO DE ACESSOS
# ==========================================

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


# ==========================================
# ATUALIZAR USUÁRIO
# ==========================================

def atualizar_usuario(usuario_id, **dados):

    campos_permitidos = {
        "nome", "matricula", "foto", "ativo"
    }

    with obter_sessao() as db:

        usuario = db.get(Usuario, usuario_id)

        if not usuario:
            return False

        for campo, valor in dados.items():

            if campo not in campos_permitidos:
                continue

            if campo == "foto":
                usuario.foto = salvar_foto(valor) if valor else None
                usuario.foto_origem = valor

            else:
                setattr(usuario, campo, valor)

        db.commit()

        return True


# ==========================================
# EXCLUIR USUÁRIO
# ==========================================

def excluir_usuario(usuario_id):

    with obter_sessao() as db:

        usuario = db.get(Usuario, usuario_id)

        if not usuario:
            return False

        db.delete(usuario)
        db.commit()

        return True


# ==========================================
# INICIALIZAÇÃO DO SISTEMA
# ==========================================

if __name__ == "__main__":

    criar_tabelas()

    inicializar_primeiro_usuario()

    print("Banco de dados inicializado!")
