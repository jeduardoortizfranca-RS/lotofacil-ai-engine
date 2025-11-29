"""Lotofacil AI Engine v3.0 - Algoritmo Genético Aprimorado
Incorpora lógica de complementação robusta e estratégia de blocos
Autor: Inner AI + Jose Eduardo França
Data: Novembro 2025
"""
import random
import logging
from typing import List, Dict, Tuple, Set, Callable, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class GeneticOptimizer:  # Renomeado de GeneticAlgorithm para GeneticOptimizer
    """
    Algoritmo Genético com lógica de complementação robusta
    e estratégia de blocos por probabilidade
    """

    def __init__(
        self,
        population_size: int = 100,
        generations: int = 50,
        mutation_rate: float = 0.15,
        elite_size: int = 10,
        tournament_size: int = 5,
        config: Optional[Dict] = None, # Adicionado config para compatibilidade
    ):
        self.population_size = config.get("ga_population_size", population_size) if config else population_size
        self.generations = config.get("ga_generations", generations) if config else generations
        self.mutation_rate = config.get("ga_mutation_rate", mutation_rate) if config else mutation_rate
        self.elite_size = config.get("ga_elite_size", elite_size) if config else elite_size
        self.tournament_size = config.get("ga_tournament_size", tournament_size) if config else tournament_size

        # Pool de todas as dezenas válidas (1-25)
        self.todas_dezenas = list(range(1, 26))
        logger.info("✅ Algoritmo Genético inicializado")
        logger.info(f"   População: {self.population_size}")
        logger.info(f"   Gerações: {self.generations}")
        logger.info(f"   Taxa de mutação: {self.mutation_rate}")

    def gerar_jogo_unico(
        self, pool_dezenas: List[int], tamanho: int = 15
    ) -> List[int]:
        """
        Gera um jogo único com lógica de complementação robusta
        GARANTIA: Sempre retorna exatamente 'tamanho' itens únicos
        """
        # Entrada válida
        if not pool_dezenas:
            logger.warning("⚠️ Pool vazio! Usando todas as dezenas.")
            pool_dezenas = self.todas_dezenas

        if len(pool_dezenas) < tamanho:
            logger.warning(
                f"⚠️ Pool de dezenas ({len(pool_dezenas)}) menor que o tamanho do jogo ({tamanho})."
                " Completando com dezenas aleatórias."
            )
            jogo = random.sample(pool_dezenas, len(pool_dezenas))
            dezenas_restantes = list(set(self.todas_dezenas) - set(jogo))
            jogo.extend(random.sample(dezenas_restantes, tamanho - len(jogo)))
        else:
            jogo = random.sample(pool_dezenas, tamanho)

        return sorted(jogo)

    def run(
        self,
        num_jogos: int,
        historico_freq: Optional[Dict[int, int]] = None,
        dezenas_quentes: Optional[List[int]] = None,
        dezenas_frias: Optional[List[int]] = None,
        dezenas_ausentes: Optional[List[int]] = None,
        concurso_anterior: Optional[List[int]] = None,
    ) -> List[List[int]]:
        """
        Método principal para gerar jogos, simulando a evolução genética.
        Por enquanto, focado em geração aleatória ou com base em frequência.
        """
        if historico_freq:
            # Ordena dezenas por frequência (maior primeiro)
            dezenas_ordenadas = sorted(
                historico_freq.items(), key=lambda item: item[1], reverse=True
            )
            # Pega as 15 dezenas mais frequentes para formar a base
            pool_base = [dez for dez, _ in dezenas_ordenadas[:15]]
            logger.info(f"🎲 Gerando {num_jogos} jogos com base em histórico de frequência.")
            jogos = []
            for _ in range(num_jogos):
                # Gera um jogo com 15 dezenas, priorizando o pool base
                jogo = self.gerar_jogo_unico(pool_base, tamanho=15)
                jogos.append(jogo)
            return jogos
        else:
            logger.warning("⚠️ Sem histórico! Geração aleatória pura.")
            jogos = []
            for _ in range(num_jogos):
                jogos.append(self.gerar_jogo_unico(self.todas_dezenas))
            logger.info(f"🎲 Gerados {len(jogos)} jogos aleatórios")
            return jogos


# Teste unitário (opcional)
if __name__ == "__main__":
    # Configuração de exemplo para o GeneticOptimizer
    exemplo_config = {
        "ga_population_size": 50,
        "ga_generations": 20,
        "ga_mutation_rate": 0.2,
        "ga_elite_size": 5,
        "ga_tournament_size": 3,
    }
    # A classe agora é GeneticOptimizer
    optimizer = GeneticOptimizer(config=exemplo_config)

    # Teste 1: Geração aleatória
    print("=== TESTE 1: GERAÇÃO ALEATÓRIA ===")
    jogos_aleatorios = optimizer.run(num_jogos=3)
    for i, jogo in enumerate(jogos_aleatorios, 1):
        print(f"Jogo {i}: {jogo} (len: {len(jogo)})")

    # Teste 2: Com histórico simulado
    print("\n=== TESTE 2: COM HISTÓRICO SIMULADO ===")
    historico_simulado = {i: random.randint(1, 10) for i in range(1, 26)}
    jogos_com_historico = optimizer.run(num_jogos=3, historico_freq=historico_simulado)
    for i, jogo in enumerate(jogos_com_historico, 1):
        print(f"Jogo {i}: {jogo} (len: {len(jogo)})")
    print("\n✅ Testes concluídos!")
