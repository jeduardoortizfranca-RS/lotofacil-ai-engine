"""
Integração com dados estatísticos Mazusoft
"""

import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class MazusoftAnalyzer:
    """Analisador dos dados Mazusoft (frequência, ciclo, atraso)."""

    def __init__(self, data_path: str = "data/mazusoft_data.json"):
        self.data_path = data_path
        self.data = self._carregar_dados()
        logger.info(f"✅ Mazusoft carregado: {len(self.data)} registros")

    def _carregar_dados(self) -> Dict:
        """Carrega os dados do arquivo local JSON."""
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Arquivo {self.data_path} não encontrado.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Erro ao ler {self.data_path}.")
            return {}

    def load_all_stats(self) -> Dict:
        """Retorna todas as estatísticas brutas."""
        return self.data

    def get_probabilidades_frequencia(self) -> Dict[int, float]:
        """Probabilidade de cada dezena baseada em frequência."""
        return {n: 0.5 for n in range(1, 26)}  # placeholder até ter dados reais

    def get_probabilidades_ciclo(self) -> Dict[int, float]:
        """Probabilidade de cada dezena baseada em ciclo."""
        return {n: 0.5 for n in range(1, 26)}

    def get_probabilidades_gap(self) -> Dict[int, float]:
        """Probabilidade de cada dezena baseada em atraso (gap)."""
        return {n: 0.5 for n in range(1, 26)}

    def calcular_temperatura_atual(self) -> str:
        """Determina se o ambiente estatístico está quente/normal/frio."""
        return "normal"

    def atualizar_com_resultado(self, resultado: List[int]):
        """Atualiza o dataset Mazusoft com novo resultado."""
        logger.info(f"Atualizando Mazusoft com resultado: {resultado}")
