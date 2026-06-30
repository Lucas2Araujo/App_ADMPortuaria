from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass(frozen=True)
class CargaDTO:
    id: Optional[int]
    descricao: str
    categoria: str
    quantidade_toneladas: int
    eh_perecivel: bool
    documento_alfandega: bool

@dataclass(frozen=True)
class NavioDTO:
    imo_id: str
    nome: str
    nome_capitao: str
    companhia: str
    status: str
    data_solicitacao: datetime
    cargas: List[CargaDTO]
    score: float = 0.0

@dataclass(frozen=True)
class VagaDTO:
    id: int
    tipo_vaga: str
    status: str
    navio_atracado: Optional[NavioDTO] = None
    data_hora_inicio: Optional[datetime] = None

@dataclass(frozen=True)
class OperacaoLogDTO:
    id: int
    tipo: str  # "ATRACAO" ou "DESATRACAO"
    navio_imo_id: str
    vaga_id: int
    data_hora: datetime
    navio_nome: str = "Desconhecido"

