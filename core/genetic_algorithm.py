"""
Lotofacil AI Engine v3.0 - Algoritmo Genético Aprimorado
Incorpora lógica de complementação robusta e estratégia de blocos
Autor: Inner AI + Jose Eduardo França
Data: Novembro 2025
"""

import random
import logging
from typing import List, Dict, Tuple, Set, Callable, Any, Optional # Optional já está aqui!
import numpy as np

logger = logging.getLogger(__name__)

class GeneticAlgorithm:
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
        tournament_size: int = 5
    ):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite_size = elite_size
        self.tournament_size = tournament_size
        
        # Pool de todas as dezenas válidas (1-25)
        self.todas_dezenas = list(range(1, 26))
        
        logger.info("✅ Algoritmo Genético inicializado")
        logger.info(f"   População: {population_size}")
        logger.info(f"   Gerações: {generations}")
        logger.info(f"   Taxa de mutação: {mutation_rate}")
    
    def gerar_jogo_unico(
        self, 
        pool_dezenas: List[int], 
        tamanho: int = 15
    ) -> List[int]:
        """
        Gera um jogo único com lógica de complementação robusta
        GARANTIA: Sempre retorna exatamente 'tamanho' itens únicos
        """
        # Entrada válida
        if not pool_dezenas:
            logger.warning("⚠️ Pool vazio! Usando todas as dezenas.")
            pool_dezenas = self.todas_dezenas.copy()
        
        # Remove duplicados
        pool_unico = list(set(pool_dezenas))
        
        # LÓGICA DE COMPLEMENTAÇÃO ROBUSTA
        if len(pool_unico) < tamanho:
            logger.warning(f"⚠️ Pool insuficiente ({len(pool_unico)} < {tamanho})")
            # Complementa com dezenas restantes
            dezenas_faltantes = [d for d in self.todas_dezenas if d not in pool_unico]
            pool_complementado = pool_unico + random.sample(dezenas_faltantes, tamanho - len(pool_unico))
            pool_unico = pool_complementado
            logger.info(f"   Complementado com {tamanho - len(pool_unico)} dezenas")
        
        # Seleciona exatamente 'tamanho' dezenas únicas
        jogo = random.sample(pool_unico, tamanho)
        jogo.sort()  # Ordena para padronização
        
        # VALIDAÇÃO FINAL
        if len(jogo) != tamanho:
            logger.error(f"❌ Erro crítico: jogo tem {len(jogo)} != {tamanho}")
            # Fallback final
            jogo = sorted(random.sample(self.todas_dezenas, tamanho))
        
        return jogo
    
    def gerar_populacao_estratificada(
        self,
        historico_freq: Optional[Dict[int, int]] = None,
        tamanho_populacao: int = 100
    ) -> List[List[int]]:
        """
        Gera população inicial usando estratégia de blocos por probabilidade
        """
        logger.info("🎯 Gerando população estratificada...")
        
        if not historico_freq:
            logger.warning("⚠️ Sem histórico! Geração aleatória pura.")
            return [
                self.gerar_jogo_unico(self.todas_dezenas, 15)
                for _ in range(tamanho_populacao)
            ]
        
        # Ordena dezenas por frequência (quentes e frias)
        dezenas_ordenadas = sorted(historico_freq.items(), key=lambda item: item[1], reverse=True)
        dezenas_quentes = [d for d, _ in dezenas_ordenadas[:15]] # Top 15
        dezenas_mornas = [d for d, _ in dezenas_ordenadas[15:20]] # Próximas 5
        dezenas_frias = [d for d, _ in dezenas_ordenadas[20:]] # Últimas 5
        
        populacao = []
        
        # Bloco 1: Alta Probabilidade (50% da população)
        # Foca em dezenas quentes, complementa com mornas/frias
        num_alta_prob = int(tamanho_populacao * 0.5)
        for _ in range(num_alta_prob):
            pool = list(dezenas_quentes)
            if len(pool) < 15:
                pool.extend(random.sample(dezenas_mornas + dezenas_frias, 15 - len(pool)))
            populacao.append(self.gerar_jogo_unico(pool, 15))
            
        # Bloco 2: Média Probabilidade (30% da população)
        # Mistura dezenas quentes e mornas, com alguma fria
        num_media_prob = int(tamanho_populacao * 0.3)
        for _ in range(num_media_prob):
            pool = random.sample(dezenas_quentes, min(10, len(dezenas_quentes)))
            pool.extend(random.sample(dezenas_mornas, min(5, len(dezenas_mornas))))
            if len(pool) < 15:
                pool.extend(random.sample(dezenas_frias, 15 - len(pool)))
            populacao.append(self.gerar_jogo_unico(pool, 15))
            
        # Bloco 3: Cobertura/Diversidade (20% da população)
        # Inclui mais dezenas frias para cobrir o espectro
        num_cobertura = tamanho_populacao - num_alta_prob - num_media_prob
        for _ in range(num_cobertura):
            pool = random.sample(dezenas_frias, min(5, len(dezenas_frias)))
            pool.extend(random.sample(dezenas_mornas, min(5, len(dezenas_mornas))))
            if len(pool) < 15:
                pool.extend(random.sample(dezenas_quentes, 15 - len(pool)))
            populacao.append(self.gerar_jogo_unico(pool, 15))
            
        random.shuffle(populacao) # Embaralha a população
        logger.info(f"   População inicial de {len(populacao)} jogos gerada.")
        return populacao

    def calcular_fitness_populacao(
        self, 
        populacao: List[List[int]], 
        fitness_function: Callable, 
        **kwargs: Any
    ) -> List[float]:
        """Calcula o fitness para cada indivíduo na população."""
        return [fitness_function(individuo, **kwargs) for individuo in populacao]

    def selecionar_elite(
        self, 
        populacao: List[List[int]], 
        fitness_scores: List[float]
    ) -> List[List[int]]:
        """Seleciona os indivíduos de elite (melhores fitness)."""
        elite_indices = sorted(range(len(fitness_scores)), key=lambda i: fitness_scores[i], reverse=True)[:self.elite_size]
        return [populacao[i] for i in elite_indices]

    def selecao_por_torneio(
        self, 
        populacao: List[List[int]], 
        fitness_scores: List[float]
    ) -> List[int]:
        """Seleciona um indivíduo usando seleção por torneio."""
        competitors = random.sample(list(zip(populacao, fitness_scores)), self.tournament_size)
        winner = max(competitors, key=lambda x: x[1])
        return winner[0]

    def crossover(self, pai1: List[int], pai2: List[int]) -> Tuple[List[int], List[int]]:
        """Realiza o crossover de dois pontos."""
        ponto1 = random.randint(1, 13)
        ponto2 = random.randint(ponto1 + 1, 14)
        
        filho1_set = set(pai1[:ponto1] + pai2[ponto1:ponto2] + pai1[ponto2:])
        filho2_set = set(pai2[:ponto1] + pai1[ponto1:ponto2] + pai2[ponto2:])
        
        # Garante 15 dezenas únicas para cada filho
        filho1 = list(filho1_set)
        filho2 = list(filho2_set)
        
        # Complementa se necessário
        if len(filho1) < 15:
            complemento = [d for d in self.todas_dezenas if d not in filho1]
            filho1.extend(random.sample(complemento, 15 - len(filho1)))
        if len(filho2) < 15:
            complemento = [d for d in self.todas_dezenas if d not in filho2]
            filho2.extend(random.sample(complemento, 15 - len(filho2)))
            
        # Trunca se necessário (pode acontecer se o pool de dezenas for pequeno e o crossover gerar muitos duplicados)
        filho1 = sorted(random.sample(filho1, 15))
        filho2 = sorted(random.sample(filho2, 15))
        
        return filho1, filho2

    def mutacao(self, individuo: List[int]) -> List[int]:
        """Aplica mutação a um indivíduo."""
        mutated_individuo = list(individuo)
        if random.random() < self.mutation_rate:
            idx_to_change = random.randint(0, 14)
            
            # Tenta trocar por uma dezena que não está no jogo
            available_dezenas = [d for d in self.todas_dezenas if d not in mutated_individuo]
            if available_dezenas:
                mutated_individuo[idx_to_change] = random.choice(available_dezenas)
            else:
                # Se todas as dezenas estão no jogo (improvável), troca por outra do próprio jogo
                idx_swap = random.randint(0, 14)
                mutated_individuo[idx_to_change], mutated_individuo[idx_swap] = \
                    mutated_individuo[idx_swap], mutated_individuo[idx_to_change]
        
        return sorted(list(set(mutated_individuo))) # Garante unicidade e 15 dezenas
    
    def evolve(
        self, 
        initial_population: List[List[int]], 
        fitness_function: Callable, 
        **fitness_kwargs: Any
    ) -> Tuple[List[List[int]], List[float]]:
        """Evolui a população ao longo das gerações."""
        population = initial_population
        
        for generation in range(self.generations):
            fitness_scores = self.calcular_fitness_populacao(population, fitness_function, **fitness_kwargs)
            
            # Validação de fitness_scores
            if not fitness_scores or any(s is None for s in fitness_scores):
                logger.error(f"❌ Erro: Fitness scores inválidos na geração {generation}. Interrompendo evolução.")
                break

            new_population = self.selecionar_elite(population, fitness_scores)
            
            while len(new_population) < self.population_size:
                pai1 = self.selecao_por_torneio(population, fitness_scores)
                pai2 = self.selecao_por_torneio(population, fitness_scores)
                
                filho1, filho2 = self.crossover(pai1, pai2)
                
                new_population.append(self.mutacao(filho1))
                if len(new_population) < self.population_size:
                    new_population.append(self.mutacao(filho2))
            
            population = new_population
            
            # Opcional: log do melhor fitness da geração
            best_fitness = max(fitness_scores)
            logger.debug(f"Geração {generation+1}/{self.generations}, Melhor Fitness: {best_fitness:.2f}")
            
        final_fitness_scores = self.calcular_fitness_populacao(population, fitness_function, **fitness_kwargs)
        return population, final_fitness_scores


class GeneticOptimizer:
    """
    Otimizador Genético que encapsula o GeneticAlgorithm e a lógica de execução.
    Agora com tratamento robusto para 'config' ser None.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None): # <-- AQUI ESTÁ A MUDANÇA PRINCIPAL!
        # Garante que config seja um dicionário, mesmo que venha como None
        config_safe = config if config is not None else {}
        
        self.ga = GeneticAlgorithm(
            population_size=config_safe.get("ga_population_size", 100),
            generations=config_safe.get("ga_generations", 50),
            mutation_rate=config_safe.get("ga_mutation_rate", 0.15),
            elite_size=config_safe.get("ga_elite_size", 10),
            tournament_size=config_safe.get("ga_tournament_size", 5)
        )
        logger.info("✅ GeneticOptimizer inicializado")

    def run(
        self,
        num_jogos: int,
        historico_freq: Optional[Dict[int, int]] = None,
        fitness_function: Optional[Callable] = None,
        pesos: Optional[Dict[str, float]] = None, # Adicionado pesos aqui
        **fitness_kwargs: Any
    ) -> List[List[int]]:
        """
        Gera jogos otimizados usando algoritmo genético
        
        Args:
            num_jogos: Quantidade de jogos a serem gerados.
            historico_freq: Dicionário de frequência das dezenas (pode ser None).
            fitness_function: Função de fitness para avaliação (pode ser None).
            pesos: Dicionário de pesos para a função de fitness.
            **fitness_kwargs: Argumentos adicionais para a função de fitness.
        
        Returns:
            Uma lista de jogos, onde cada jogo é uma lista de 15 dezenas.
        """
        try:
            # Caso 1: Sem histórico - geração aleatória pura
            if not historico_freq:
                logger.warning("⚠️ Sem histórico! Geração aleatória pura.")
                jogos = [
                    self.ga.gerar_jogo_unico(self.ga.todas_dezenas, 15)
                    for _ in range(num_jogos)
                ]
                return jogos
            
            # Caso 2: Com histórico mas sem fitness - seleção direta
            if not fitness_function:
                logger.info("ℹ️ Sem função de fitness. Usando seleção direta.")
                # Gera população inicial
                populacao_inicial = self.ga.gerar_populacao_estratificada(
                    historico_freq,
                    max(num_jogos * 2, 50)  # População maior que o necessário
                )
                # Seleciona os primeiros N jogos
                jogos = populacao_inicial[:num_jogos]
                return jogos
            
            # Caso 3: Com histórico E fitness - evolução completa
            logger.info("🎯 Modo evolução completa ativado!")
            
            # Gera população inicial estratificada
            populacao_inicial = self.ga.gerar_populacao_estratificada(
                historico_freq,
                max(num_jogos * 2, 50)
            )
            
            # Evolui a população
            populacao_final, fitness_scores = self.ga.evolve(
                populacao_inicial,
                fitness_function,
                pesos=pesos or {}, # Passa os pesos para a função de fitness
                historico=historico_freq,
                **fitness_kwargs
            )
            
            # Seleciona os melhores jogos
            melhores_indices = sorted(
                range(len(fitness_scores)),
                key=lambda i: fitness_scores[i],
                reverse=True
            )[:num_jogos]
            
            jogos = [populacao_final[i] for i in melhores_indices]
            
            # VALIDAÇÃO FINAL
            jogos_validos = [j for j in jogos if len(j) == 15]
            
            if len(jogos_validos) < num_jogos:
                logger.warning(f"⚠️ Apenas {len(jogos_validos)}/{num_jogos} válidos")
                # Complementa com jogos aleatórios
                faltam = num_jogos - len(jogos_validos)
                jogos_extras = [
                    self.ga.gerar_jogo_unico(self.ga.todas_dezenas, 15)
                    for _ in range(faltam)
                ]
                jogos_validos.extend(jogos_extras)
            
            logger.info(f"✅ {len(jogos_validos)} jogos gerados com sucesso!")
            return jogos_validos
        
        except Exception as e:
            logger.error(f"❌ Erro no GeneticOptimizer.run: {e}")
            logger.exception("Detalhes do erro:")
            # Fallback final: geração aleatória
            jogos = [
                self.ga.gerar_jogo_unico(self.ga.todas_dezenas, 15)
                for _ in range(num_jogos)
            ]
            logger.warning(f"⚠️ Fallback ativado: {len(jogos)} jogos aleatórios")
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
    optimizer = GeneticOptimizer(exemplo_config) # Passando a config aqui
    
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
