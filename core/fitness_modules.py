"""
Lotofacil AI Engine v3.0 - Módulos de Fitness
Avalia a qualidade dos jogos gerados
Autor: Inner AI + Jose Eduardo França
Data: Novembro 2025
"""

import logging
from typing import List, Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class FitnessCalculator:
    """
    Calcula o fitness (qualidade) de um jogo baseado em múltiplos critérios.
    Adaptado para funcionar mesmo quando não há histórico disponível.
    """
    
    def __init__(self):
        self.primos = {2, 3, 5, 7, 11, 13, 17, 19, 23}
        self.fibonacci = {1, 2, 3, 5, 8, 13, 21}
        logger.info("✅ Calculador de Fitness inicializado")
    
    def calcular_fitness(
        self,
        jogo: List[int],
        pesos: Dict[str, float],
        historico: Optional[Dict[str, any]] = None,
        concurso_anterior: Optional[List[int]] = None,
        temperatura: float = 1.0
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calcula fitness total do jogo baseado em múltiplos critérios
        
        Args:
            jogo: Lista de 15 dezenas
            pesos: Dicionário com pesos de cada critério
            historico: Dados históricos (pode ser None)
            concurso_anterior: Resultado do concurso anterior (pode ser None)
            temperatura: Fator de aleatoriedade (1.0 = normal)
        
        Returns:
            (fitness_total, scores_detalhados)
        """
        if len(jogo) != 15:
            logger.warning(f"⚠️ Jogo inválido: {len(jogo)} dezenas")
            return 0.0, {}
        
        scores = {}
        
        # Proteção contra histórico None
        historico_safe = historico if historico is not None else {}
        
        # 1. Par/Ímpar
        pares = sum(1 for d in jogo if d % 2 == 0)
        impares = 15 - pares
        scores['par_impar'] = pesos.get('par_impar', 1.0) * (
            1.0 if 6 <= pares <= 9 else 0.5
        )
        
        # 2. Primos
        primos_count = sum(1 for d in jogo if d in self.primos)
        scores['primos'] = pesos.get('primos', 1.0) * (
            1.0 if 5 <= primos_count <= 8 else 0.6
        )
        
        # 3. Fibonacci
        fib_count = sum(1 for d in jogo if d in self.fibonacci)
        scores['fibonacci'] = pesos.get('fibonacci', 1.0) * (
            1.0 if 3 <= fib_count <= 6 else 0.7
        )
        
        # 4. Linhas (1-5, 6-10, 11-15, 16-20, 21-25)
        linhas = [
            sum(1 for d in jogo if 1 <= d <= 5),
            sum(1 for d in jogo if 6 <= d <= 10),
            sum(1 for d in jogo if 11 <= d <= 15),
            sum(1 for d in jogo if 16 <= d <= 20),
            sum(1 for d in jogo if 21 <= d <= 25)
        ]
        linhas_balanceadas = all(1 <= l <= 5 for l in linhas)
        scores['linhas'] = pesos.get('linhas', 1.0) * (1.0 if linhas_balanceadas else 0.5)
        
        # 5. Colunas (5 colunas)
        colunas = [
            sum(1 for d in jogo if d % 5 == i) for i in range(1, 6)
        ]
        colunas_balanceadas = all(1 <= c <= 5 for c in colunas)
        scores['colunas'] = pesos.get('colunas', 1.0) * (1.0 if colunas_balanceadas else 0.5)
        
        # 6. Consecutivos
        jogo_sorted = sorted(jogo)
        consecutivos = sum(
            1 for i in range(len(jogo_sorted) - 1)
            if jogo_sorted[i+1] - jogo_sorted[i] == 1
        )
        scores['consecutivos'] = pesos.get('consecutivos', 1.0) * (
            1.0 if consecutivos <= 3 else 0.6
        )
        
        # 7. Frequência histórica (se disponível)
        if historico_safe and 'frequencias' in historico_safe:
            freq_dict = historico_safe['frequencias']
            freq_media = np.mean([freq_dict.get(d, 0) for d in jogo])
            freq_max = max(freq_dict.values()) if freq_dict else 1
            scores['frequencia'] = pesos.get('frequencia', 1.0) * (freq_media / freq_max if freq_max > 0 else 0.5)
        else:
            scores['frequencia'] = pesos.get('frequencia', 1.0) * 0.5  # Neutro
        
        # 8. Diversidade (spread)
        spread = max(jogo) - min(jogo)
        scores['diversidade'] = pesos.get('diversidade', 1.0) * (
            1.0 if 18 <= spread <= 24 else 0.7
        )
        
        # 9. Soma total
        soma = sum(jogo)
        scores['soma'] = pesos.get('soma', 1.0) * (
            1.0 if 170 <= soma <= 210 else 0.6
        )
        
        # 10. Repetição do concurso anterior (se disponível)
        if concurso_anterior:
            repeticoes = len(set(jogo) & set(concurso_anterior))
            scores['repeticao'] = pesos.get('repeticao', 1.0) * (
                1.0 if 6 <= repeticoes <= 10 else 0.5
            )
        else:
            scores['repeticao'] = pesos.get('repeticao', 1.0) * 0.5  # Neutro
        
        # Fitness total
        fitness_total = sum(scores.values())
        
        # Aplica temperatura (aleatoriedade controlada)
        if temperatura != 1.0:
            noise = np.random.normal(0, 0.1 * temperatura)
            fitness_total *= (1 + noise)
        
        return fitness_total, scores
    
    def avaliar_jogo_completo(
        self,
        jogo: List[int],
        pesos: Dict[str, float],
        historico: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Avaliação completa com explicação detalhada
        """
        fitness, scores = self.calcular_fitness(jogo, pesos, historico)
        
        # Classifica qualidade
        if fitness > 12:
            qualidade = "Excelente"
        elif fitness > 10:
            qualidade = "Ótimo"
        elif fitness > 8:
            qualidade = "Bom"
        elif fitness > 6:
            qualidade = "Regular"
        else:
            qualidade = "Fraco"
        
        # Top 3 critérios
        top_criterios = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            "fitness_total": round(fitness, 2),
            "qualidade": qualidade,
            "scores_detalhados": {k: round(v, 2) for k, v in scores.items()},
            "top_3_criterios": [
                {"criterio": k, "score": round(v, 2)} 
                for k, v in top_criterios
            ],
        }
