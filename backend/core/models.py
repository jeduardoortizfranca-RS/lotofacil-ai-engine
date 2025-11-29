# backend/core/models.py

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# --- Modelos para dados do Supabase ---

class Concurso(BaseModel):
    """Representa um registro da tabela 'concursos'."""
    numero: int
    data_sorteio: str # Pode ser datetime ou str, dependendo de como você armazena
    dezenas_sorteadas: List[int]
    soma_dezenas: Optional[int] = None
    pares: Optional[int] = None
    impares: Optional[int] = None
    primos: Optional[int] = None
    fibonacci: Optional[int] = None
    multiplos_3: Optional[int] = None
    moldura: Optional[int] = None
    centro: Optional[int] = None
    repetidas_anterior: Optional[int] = None
    ciclo: Optional[int] = None
    ciclo_qtd: Optional[int] = None
    ausentes: Optional[List[int]] = None

class Frequencia(BaseModel):
    """Representa um registro da tabela 'frequencias'."""
    dezena: int
    ocorrencias: int
    ultima_aparicao: int # Número do concurso
    updated_at: str # Pode ser datetime ou str

class PesoIA(BaseModel):
    """Representa um registro da tabela 'pesos_ia'."""
    id: Optional[int] = None
    versao: int
    pesos: Dict[str, float]
    data_atualizacao: str # Pode ser datetime ou str
    motivo_ajuste: str
    created_at: Optional[str] = None # Pode ser datetime ou str

class Premio(BaseModel):
    """Representa um registro da tabela 'premios'."""
    id: Optional[int] = None
    acertos: int
    valor: float
    data_criacao: str # Pode ser datetime ou str

class JogoGerado(BaseModel):
    """Representa um jogo individual dentro de um lote."""
    dezenas: List[int]
    score: float
    confianca: float = 0.0 # Exemplo, pode ser mais detalhado
    detalhes_fitness: Dict[str, Any] = {}
    analise_mazusoft: Dict[str, Any] = {}
    evento_raro: bool = False
    tipo_raro: Optional[str] = None

class LoteJogosGerados(BaseModel):
    """Representa um registro da tabela 'jogos_gerados'."""
    id: str # UUID
    concurso_alvo: int
    quantidade_jogos: int
    jogos: List[List[int]] # Lista de listas de dezenas
    data_geracao: str # Pode ser datetime ou str
    custo_total: float
    status_conferencia: str = "pendente"

class ResultadoConferencia(BaseModel):
    """Representa um registro da tabela 'resultados_conferencia'."""
    id: Optional[int] = None
    concurso_numero: int
    data_conferencia: str # Pode ser datetime ou str
    jogos_gerados_id: str
    resultado_oficial: List[int]
    total_jogos: int
    distribuicao_acertos: Dict[str, int]
    premio_total: float
    lucro: float
    acertos_por_jogo: Optional[List[int]] = None # Adicionado, pois existe na tabela

class HistoricoTreinamento(BaseModel):
    """Representa um registro da tabela 'historico_treinamento'."""
    id: Optional[int] = None
    episodio: int
    epsilon: float
    recompensa_media: float
    melhor_fitness: float
    timestamp: str # Pode ser datetime ou str
