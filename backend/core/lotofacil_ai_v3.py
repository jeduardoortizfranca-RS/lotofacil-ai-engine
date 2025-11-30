# backend/core/lotofacil_ai_v3.py
import logging
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

# Importa o SupabaseClient para interagir com o banco de dados
from app.services.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class LotofacilAIv3:
    def __init__(self, db_client: SupabaseClient, modo_offline: bool = False, mazusoft_data_path: str = None):
        self.supabase_client = db_client
        self.modo_offline = modo_offline
        self.mazusoft_data_path = mazusoft_data_path
        self.historico_concursos: List[Dict[str, Any]] = []
        self.ultimo_concurso_sorteado: Optional[Dict[str, Any]] = None
        self.tabela_premios: Dict[str, float] = {}
        self.config_lotofacil: Dict[str, Any] = {}
        self.fitness_weights: Dict[str, float] = {
            "repetidas": 0.25,
            "ausentes": 0.15,
            "frequencia": 0.20,
            "ciclo": 0.20, # Novo peso para o ciclo das dezenas
            "primos": 0.10,
            "fibonacci": 0.10
        }
        self.dezenas_primos = [2, 3, 5, 7, 11, 13, 17, 19, 23]
        self.dezenas_fibonacci = [1, 2, 3, 5, 8, 13, 21]

    @classmethod
    async def create(cls, db_client: SupabaseClient, modo_offline: bool = False, mazusoft_data_path: str = None):
        """
        Método de fábrica assíncrono para inicializar a IA e carregar dados.
        """
        instance = cls(db_client, modo_offline, mazusoft_data_path)
        await instance._carregar_dados_iniciais()
        return instance

    async def _carregar_dados_iniciais(self):
        """
        Carrega dados iniciais do Supabase ou de arquivos locais.
        """
        logger.info("Carregando dados iniciais para a IA...")
        if self.modo_offline:
            # Implementar carregamento de dados de arquivos locais se necessário
            logger.warning("Modo offline não totalmente implementado para carregamento de dados.")
            pass
        else:
            # Carregar histórico de concursos do Supabase
            historico_raw = await self.supabase_client.get_todos_concursos() # CORREÇÃO AQUI
            if historico_raw:
                # Ordenar pelo número do concurso para garantir a sequência
                self.historico_concursos = sorted(historico_raw, key=lambda x: x['numero'])
                logger.info(f"✅ {len(self.historico_concursos)} concursos históricos carregados do Supabase.")

                # Definir o último concurso sorteado
                if self.historico_concursos:
                    self.ultimo_concurso_sorteado = self.historico_concursos[-1]
                    logger.info(f"✅ Último concurso sorteado identificado: {self.ultimo_concurso_sorteado['numero']}.")
            else:
                logger.warning("⚠️ Nenhum concurso histórico encontrado no Supabase.")

            # Carregar tabela de prêmios
            self.tabela_premios = await self.supabase_client.get_tabela_premios()
            if self.tabela_premios:
                logger.info("✅ Tabela de prêmios carregada.")
            else:
                logger.warning("⚠️ Tabela de prêmios não carregada. Usando valores padrão (0).")
                self.tabela_premios = {"11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0} # Valores padrão

            # Carregar configurações da Lotofácil (ex: custo do jogo)
            self.config_lotofacil = await self.supabase_client.get_config_lotofacil()
            if self.config_lotofacil:
                logger.info("✅ Configurações da Lotofácil carregadas.")
            else:
                logger.warning("⚠️ Configurações da Lotofácil não carregadas. Usando valores padrão.")
                self.config_lotofacil = {"custo_jogo": 3.50} # Valor padrão

        logger.info("Dados iniciais da IA carregados com sucesso.")

    def _get_dezenas_sorteadas(self, concurso: Dict[str, Any]) -> List[int]:
        """Extrai as dezenas sorteadas de um registro de concurso."""
        dezenas = []
        for i in range(1, 16):
            dezena = concurso.get(f'bola{i}')
            if dezena is not None:
                dezenas.append(dezena)
        return sorted(dezenas)

    def _calcular_repetidas_do_anterior(self, jogo: List[int], concurso_anterior_dezenas: List[int]) -> int:
        """Calcula quantas dezenas do jogo se repetem do concurso anterior."""
        return len(set(jogo).intersection(concurso_anterior_dezenas))

    def _calcular_ausentes(self, jogo: List[int], concurso_anterior_dezenas: List[int]) -> int:
        """Calcula quantas dezenas do jogo estavam ausentes no concurso anterior."""
        return len(set(jogo) - set(concurso_anterior_dezenas))

    def _calcular_frequencia(self, jogo: List[int]) -> float:
        """Calcula a frequência média das dezenas no histórico."""
        if not self.historico_concursos:
            return 0.0

        contagem_dezenas = {dezena: 0 for dezena in range(1, 26)}
        for concurso in self.historico_concursos:
            dezenas_sorteadas = self._get_dezenas_sorteadas(concurso)
            for dezena in dezenas_sorteadas:
                contagem_dezenas[dezena] += 1

        frequencia_total = sum(contagem_dezenas.get(dezena, 0) for dezena in jogo)
        return frequencia_total / len(jogo) if jogo else 0.0

    def _calcular_ciclo_dezenas(self, jogo: List[int]) -> float:
        """
        Calcula a pontuação baseada no ciclo das dezenas.
        Dezenas que estão "em ciclo" (não saem há algumas rodadas, mas devem sair logo)
        ou que acabaram de sair e tendem a repetir.
        Isso requer uma análise mais profunda do histórico. Por enquanto, um placeholder.
        """
        # Implementação mais sofisticada aqui, buscando dados de ciclo do Supabase
        # ou calculando com base no historico_concursos.
        # Por simplicidade, vamos usar um placeholder que favorece dezenas que não saíram
        # no último concurso, mas que têm alta frequência geral.
        if not self.historico_concursos or not self.ultimo_concurso_sorteado:
            return 0.0

        dezenas_ultimo = set(self._get_dezenas_sorteadas(self.ultimo_concurso_sorteado))
        dezenas_ausentes_ultimo = set(range(1, 26)) - dezenas_ultimo

        score_ciclo = 0
        for dezena in jogo:
            if dezena in dezenas_ausentes_ultimo:
                # Dá um peso maior para dezenas ausentes que têm boa frequência histórica
                # (isso é uma simplificação do conceito de "ciclo")
                frequencia_dezena = self._calcular_frequencia([dezena])
                score_ciclo += frequencia_dezena * 0.5 # Exemplo de ponderação
            else:
                # Dá um peso menor para dezenas que acabaram de sair e podem repetir
                score_ciclo += 0.1 # Exemplo
        return score_ciclo / len(jogo) if jogo else 0.0


    def _calcular_dezenas_primos(self, jogo: List[int]) -> int:
        """Calcula quantas dezenas do jogo são números primos."""
        return len(set(jogo).intersection(self.dezenas_primos))

    def _calcular_dezenas_fibonacci(self, jogo: List[int]) -> int:
        """Calcula quantas dezenas do jogo são números de Fibonacci."""
        return len(set(jogo).intersection(self.dezenas_fibonacci))

    def _calcular_fitness(self, jogo: List[int], concurso_anterior_dezenas: List[int]) -> float:
        """
        Calcula a pontuação de "fitness" de um jogo com base em vários critérios.
        Quanto maior o fitness, melhor o jogo é considerado.
        """
        if not concurso_anterior_dezenas:
            logger.warning("Concurso anterior não disponível para cálculo de fitness. Retornando 0.")
            return 0.0

        repetidas = self._calcular_repetidas_do_anterior(jogo, concurso_anterior_dezenas)
        ausentes = self._calcular_ausentes(jogo, concurso_anterior_dezenas)
        frequencia = self._calcular_frequencia(jogo)
        ciclo = self._calcular_ciclo_dezenas(jogo) # Novo critério
        primos = self._calcular_dezenas_primos(jogo)
        fibonacci = self._calcular_dezenas_fibonacci(jogo)

        # Normalização e ponderação dos critérios
        # Repetidas: idealmente entre 8 e 9 (7-10)
        score_repetidas = 1 - abs(repetidas - 8.5) / 8.5 # Max 1.0 para 8.5, min 0 para 0 ou 17

        # Ausentes: idealmente entre 6 e 7 (5-8)
        score_ausentes = 1 - abs(ausentes - 6.5) / 6.5 # Max 1.0 para 6.5

        # Frequência: já é uma média, pode ser usada diretamente ou normalizada
        score_frequencia = frequencia / (len(self.historico_concursos) * 15) # Normaliza pela freq máxima possível

        # Ciclo: já é uma média, pode ser usada diretamente
        score_ciclo = ciclo

        # Primos: idealmente entre 4 e 5
        score_primos = 1 - abs(primos - 4.5) / 4.5

        # Fibonacci: idealmente entre 4 e 5
        score_fibonacci = 1 - abs(fibonacci - 4.5) / 4.5

        # Combina os scores com os pesos definidos
        fitness = (
            self.fitness_weights["repetidas"] * score_repetidas +
            self.fitness_weights["ausentes"] * score_ausentes +
            self.fitness_weights["frequencia"] * score_frequencia +
            self.fitness_weights["ciclo"] * score_ciclo + # Adicionado
            self.fitness_weights["primos"] * score_primos +
            self.fitness_weights["fibonacci"] * score_fibonacci
        )
        return fitness

    async def gerar_jogos(self, quantidade_jogos: int) -> List[List[int]]:
        """
        Gera uma lista de jogos da Lotofácil usando a IA.
        """
        if not self.historico_concursos:
            logger.error("Histórico de concursos não carregado. Não é possível gerar jogos.")
            return []

        # Pega as dezenas do último concurso sorteado para cálculo de fitness
        if not self.ultimo_concurso_sorteado:
            logger.warning("Último concurso sorteado não disponível. Tentando buscar o mais recente.")
            self.ultimo_concurso_sorteado = await self.supabase_client.get_ultimo_concurso()
            if not self.ultimo_concurso_sorteado:
                logger.error("Não foi possível obter o último concurso sorteado para gerar jogos.")
                return []

        concurso_anterior_dezenas = self._get_dezenas_sorteadas(self.ultimo_concurso_sorteado)

        jogos_gerados: List[List[int]] = []
        tentativas = 0
        max_tentativas_por_jogo = 1000 # Limite para evitar loop infinito

        while len(jogos_gerados) < quantidade_jogos and tentativas < quantidade_jogos * max_tentativas_por_jogo:
            tentativas += 1
            # Gera um jogo aleatório inicial
            jogo_candidato = sorted(random.sample(range(1, 26), 15))

            # Calcula o fitness do jogo candidato
            fitness_candidato = self._calcular_fitness(jogo_candidato, concurso_anterior_dezenas)

            # Critério de aceitação (pode ser ajustado)
            # Por exemplo, aceitar jogos com fitness acima de um certo limiar
            # Ou usar um algoritmo genético mais complexo para "evoluir" os jogos
            # Por simplicidade, vamos aceitar jogos com fitness razoável e garantir diversidade

            # Para esta versão, vamos usar um critério simples:
            # Se o fitness for acima de um limiar, ou se for um dos primeiros jogos
            # para garantir que a quantidade seja atingida.
            # Um fitness de 0.5 é um bom ponto de partida para jogos "medianos"
            if fitness_candidato > 0.4 or len(jogos_gerados) < quantidade_jogos / 2: # Aceita mais facilmente os primeiros jogos
                if jogo_candidato not in jogos_gerados: # Evita jogos duplicados
                    jogos_gerados.append(jogo_candidato)
                    logger.debug(f"Jogo gerado com fitness {fitness_candidato:.4f}: {jogo_candidato}")

        if len(jogos_gerados) < quantidade_jogos:
            logger.warning(f"Não foi possível gerar a quantidade desejada de jogos ({quantidade_jogos}). Gerados {len(jogos_gerados)}.")
        else:
            logger.info(f"✅ {len(jogos_gerados)} jogos gerados com sucesso.")

        return jogos_gerados

    def conferir_jogos(self, jogos: List[List[int]], dezenas_sorteadas: List[int]) -> Dict[str, Any]:
        """
        Confere um lote de jogos contra as dezenas sorteadas.
        Retorna a distribuição de acertos, prêmios e lucro.
        """
        distribuicao_acertos = {"0-10": 0, "11": 0, "12": 0, "13": 0, "14": 0, "15": 0}
        acertos_por_jogo: List[int] = []
        premio_total = 0.0
        custo_jogo = self.config_lotofacil.get("custo_jogo", 3.50) # Pega o custo do jogo da config

        for jogo in jogos:
            acertos = len(set(jogo).intersection(dezenas_sorteadas))
            acertos_por_jogo.append(acertos)

            if acertos >= 11:
                distribuicao_acertos[str(acertos)] += 1
                premio_total += self.tabela_premios.get(str(acertos), 0.0)
            else:
                distribuicao_acertos["0-10"] += 1

        total_gasto = len(jogos) * custo_jogo
        lucro = premio_total - total_gasto

        return {
            "total_jogos": len(jogos),
            "distribuicao_acertos": distribuicao_acertos,
            "acertos_por_jogo": acertos_por_jogo,
            "premio_total": premio_total,
            "total_gasto": total_gasto,
            "lucro": lucro
        }

    async def ajustar_pesos_fitness(self, resultados_anteriores: List[Dict[str, Any]]):
        """
        Ajusta os pesos de fitness da IA com base nos resultados de conferências anteriores.
        Esta é uma implementação simplificada para demonstração.
        """
        logger.info("Ajustando pesos de fitness da IA com base em resultados anteriores...")

        if not resultados_anteriores:
            logger.warning("Nenhum resultado anterior para ajustar os pesos de fitness.")
            return

        # Exemplo simplificado: se o lucro médio foi positivo, aumenta um pouco os pesos.
        # Se foi negativo, tenta ajustar para buscar mais jogos com 11+ acertos.

        total_lucro = sum(r.get("lucro", 0) for r in resultados_anteriores)
        media_lucro = total_lucro / len(resultados_anteriores)

        if media_lucro > 0:
            logger.info("Lucro médio positivo. Reforçando pesos atuais ligeiramente.")
            for key in self.fitness_weights:
                self.fitness_weights[key] *= 1.01 # Aumenta 1%
        else:
            logger.info("Lucro médio negativo. Tentando ajustar pesos para buscar mais acertos.")
            # Exemplo: Aumentar peso de frequência e ciclo, diminuir de repetidas/ausentes
            self.fitness_weights["frequencia"] = min(self.fitness_weights["frequencia"] * 1.05, 0.5) # Max 0.5
            self.fitness_weights["ciclo"] = min(self.fitness_weights["ciclo"] * 1.05, 0.5)
            self.fitness_weights["repetidas"] = max(self.fitness_weights["repetidas"] * 0.95, 0.1) # Min 0.1
            self.fitness_weights["ausentes"] = max(self.fitness_weights["ausentes"] * 0.95, 0.1)

        # Normalizar pesos para que a soma seja 1.0
        soma_pesos = sum(self.fitness_weights.values())
        for key in self.fitness_weights:
            self.fitness_weights[key] /= soma_pesos

        logger.info(f"✅ Pesos de fitness ajustados: {self.fitness_weights}")

