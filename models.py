
from sqlalchemy import create_engine, Column, DateTime, Integer, String, Float, func, Enum, Text, TIMESTAMP, ForeignKey, \
    Date
from sqlalchemy.orm import sessionmaker, declarative_base
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()
engine = create_engine('mysql+pymysql://root:senaisp@localhost:3306/flashlog')
SessionLocalExemplo = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

class Usuario(Base):
    __tablename__ = 'usuario'
    id_usuario = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    data_nascimento = Column(DateTime, nullable=True)
    senha = Column(Text, nullable=False)
    email = Column(String, nullable=False, unique=True)
    perfil = Column(String, default="FUNCIONARIO")

    def set_password(self, password):
        self.senha = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.senha, password)

    def serialize(self):
        dados = {
            "id": self.id_usuario,
            "nome": self.nome,
            "email": self.email,
            "data_nascimento": self.data_nascimento,
            "perfil": self.perfil,
        }

        return dados

class Cliente(Base):
    __tablename__ = 'cliente'
    id_cliente = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    cpf = Column(String, unique=True, nullable=False)
    telefone = Column(String(50), nullable=False)
    endereco = Column(String(25), nullable=False)
    rua = Column(String, nullable=False)
    numero_casa = Column(String(10), nullable=False)

    def serialize(self):
        dados = {
            "id_cliente": self.id_cliente,
            "nome": self.nome,
            "cpf": self.cpf,
            "telefone": self.telefone,
            "endereco": self.endereco,
            "rua": self.rua,
            "numero_casa": self.numero_casa,
        }

        return dados

class Encomenda(Base):
    __tablename__ = 'encomenda'
    id_encomenda = Column(Integer, primary_key=True)
    remetente = Column(String,nullable=True)
    status_encomenda = Column(String, default="POSTADO")
    codigo_r = Column(String(30), unique=True)
    cliente_id = Column(Integer, ForeignKey('cliente.id_cliente'))
    def serialize(self):
        dados = {
            "id_encomenda": self.id_encomenda,
            "remetente": self.remetente,
            "status_encomenda": self.status_encomenda,
            "codigo_r": self.codigo_r,
            "cliente_id": self.cliente_id,
        }

        return dados

class Galpao(Base):
    __tablename__ = 'galpao'
    id_galpao = Column(Integer, primary_key=True)
    estado = Column(String, nullable=False)
    cidade = Column(String, nullable=False)


    def serialize(self):
        dados = {
            "id_galpao": self.id_galpao,
            "estado": self.estado,
            "cidade": self.cidade,

        }

        return dados

class Movimentacao(Base):
    __tablename__ = 'movimentacao'
    id_movimentacao = Column(Integer, primary_key=True)
    data_atual = Column(DateTime, default=func.now())
    status_movimentacao = Column(String, default="ENTRADA")
    galpao_id = Column(Integer, ForeignKey('galpao.id_galpao'))
    encomenda_id = Column(Integer, ForeignKey('encomenda.id_encomenda'))

    def serialize(self):
        dados = {
            "id_movimentacao": self.id_movimentacao,
            "data_atual": self.data_atual,
            "galpao_id": self.galpao_id,
            "encomenda_id": self.encomenda_id,
            "status_movimentacao": self.status_movimentacao,
        }

        return dados