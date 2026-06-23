import enum
import os
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, Enum, create_engine
from typing import List, Optional, Tuple


class StatusNavio(enum.Enum):
    """Enum para representar os possíveis status de um navio no sistema."""

    PENDENTE = "PENDENTE"
    VALIDADO = "VALIDADO"
    REJEITADO = "REJEITADO"
    ATRACADO = "ATRACADO"
    FINALIZADO = "FINALIZADO"


class StatusVaga(enum.Enum):
    """Enum para representar os possíveis status de uma vaga no cais."""

    LIVRE = "LIVRE"
    OCUPADA = "OCUPADA"


class Base(DeclarativeBase):
    """Classe base declarativa para os modelos SQLAlchemy."""

    pass


class Navio(Base):
    """
    Modelo de dados para representar um Navio.

    Atributos:
        imo_id (str): Identificador único IMO (International Maritime Organization) do navio. Chave primária.
        nome (str): Nome do navio.
        nome_capitao (str): Nome do capitão atual do navio.
        companhia (str): Companhia de navegação à qual o navio pertence.
        status (StatusNavio): Status atual do navio no porto (PENDENTE, VALIDADO, etc.).
        data_solicitacao (datetime): Data e hora da solicitação de pré-cadastro.
        cargas (List[Carga]): Lista de cargas associadas a este navio (relacionamento one-to-many).
    """

    __tablename__ = "navios"

    imo_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    nome_capitao: Mapped[str] = mapped_column(String(100))
    companhia: Mapped[str] = mapped_column(String(100))
    status: Mapped[StatusNavio] = mapped_column(
        Enum(StatusNavio), default=StatusNavio.PENDENTE, index=True
    )
    data_solicitacao: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    cargas: Mapped[List["Carga"]] = relationship(
        back_populates="navio", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Navio(imo_id={self.imo_id!r}, capitão={self.nome_capitao!r}, companhia={self.companhia!r})"

    def to_dto(self, score: float = 0.0) -> "NavioDTO":
        from dto import NavioDTO
        return NavioDTO(
            imo_id=self.imo_id,
            nome=self.nome,
            nome_capitao=self.nome_capitao,
            companhia=self.companhia,
            status=self.status.value,
            data_solicitacao=self.data_solicitacao,
            cargas=[c.to_dto() for c in self.cargas],
            score=score
        )


class Carga(Base):
    __tablename__ = "cargas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    navio_imo_id: Mapped[str] = mapped_column(ForeignKey("navios.imo_id"))
    descricao: Mapped[str] = mapped_column(String(200))
    categoria: Mapped[str] = mapped_column(String(50))
    quantidade_toneladas: Mapped[int] = mapped_column(Integer)
    eh_perecivel: Mapped[bool] = mapped_column(Boolean, default=False)
    documento_alfandega: Mapped[bool] = mapped_column(Boolean, default=False)

    navio: Mapped["Navio"] = relationship(back_populates="cargas")

    def to_dto(self) -> "CargaDTO":
        from dto import CargaDTO
        return CargaDTO(
            id=self.id,
            descricao=self.descricao,
            categoria=self.categoria,
            quantidade_toneladas=self.quantidade_toneladas,
            eh_perecivel=self.eh_perecivel,
            documento_alfandega=self.documento_alfandega
        )


class Vaga(Base):
    __tablename__ = "vagas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo_vaga: Mapped[str] = mapped_column(String(50))
    status: Mapped[StatusVaga] = mapped_column(
        Enum(StatusVaga), default=StatusVaga.LIVRE, index=True
    )

    def to_dto(self, navio_atracado: Optional["NavioDTO"] = None, data_hora_inicio: Optional[datetime] = None) -> "VagaDTO":
        from dto import VagaDTO
        return VagaDTO(
            id=self.id,
            tipo_vaga=self.tipo_vaga,
            status=self.status.value,
            navio_atracado=navio_atracado,
            data_hora_inicio=data_hora_inicio
        )


class Atracacao(Base):
    __tablename__ = "atracacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    navio_imo_id: Mapped[str] = mapped_column(ForeignKey("navios.imo_id"), index=True)
    vaga_id: Mapped[int] = mapped_column(ForeignKey("vagas.id"), index=True)
    data_hora_inicio: Mapped[datetime] = mapped_column(DateTime)
    data_hora_fim: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )


# --- GERENCIAMENTO DE CONEXÕES CENTRALIZADO ---
_engine = None
_session_maker = None

def inicializar_banco(db_path: str):
    """Inicializa a engine global e cria as tabelas."""
    global _engine, _session_maker
    if _engine is None:
        from sqlalchemy.pool import NullPool
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            poolclass=NullPool
        )
        Base.metadata.create_all(_engine)
        _session_maker = sessionmaker(bind=_engine)
    return _engine

def obter_sessao() -> Session:
    """Retorna uma nova sessão de banco de dados ativa."""
    global _session_maker
    if _session_maker is None:
        diretorio_src = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(diretorio_src, "porto.db")
        inicializar_banco(db_path)
    return _session_maker()

