from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, ForeignKey
from typing import List

class Base(DeclarativeBase):
    pass

class Navio(Base):
    __tablename__ = "navios"

    imo_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=True) # Nome do navio original
    nome_capitao: Mapped[str] = mapped_column(String(100))
    companhia: Mapped[str] = mapped_column(String(100))
    cargas: Mapped[List["Carga"]] = relationship(back_populates="navio", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"Navio(imo_id={self.imo_id!r}, capitão={self.nome_capitao!r}, companhia={self.companhia!r})"

class Carga(Base):
    __tablename__ = "cargas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    navio_imo_id: Mapped[str] = mapped_column(ForeignKey("navios.imo_id"))
    descricao: Mapped[str] = mapped_column(String(200)) 
    categoria: Mapped[str] = mapped_column(String(50))
    quantidade_toneladas: Mapped[int] = mapped_column(Integer)
    dAlfandega: Mapped[bool] = mapped_column(Boolean, default=False)

    navio: Mapped["Navio"] = relationship(back_populates="cargas")

class Vaga(Base):
    __tablename__ = "vagas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    disponivel: Mapped[bool] = mapped_column(Boolean, default=True)
