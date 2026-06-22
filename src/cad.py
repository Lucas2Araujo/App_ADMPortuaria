import enum
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, Enum
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


class Vaga(Base):
    __tablename__ = "vagas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo_vaga: Mapped[str] = mapped_column(String(50))
    status: Mapped[StatusVaga] = mapped_column(
        Enum(StatusVaga), default=StatusVaga.LIVRE, index=True
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
