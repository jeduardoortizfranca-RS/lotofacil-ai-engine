# backend/core/lotofacil_ai_v3.py

import logging
import numpy as np
import random
import uuid # Para gerar UUIDs
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# Importações de serviços e modelos do seu projeto
from app.services.supabase_client import SupabaseClient
from app.services.config_service import ConfigService
from core.event_detector import EventDetector, EventType
from core.models import Concurso, Frequencia, PesoIA, Premio # Importa os modelos de dados

logger = logging.getLogger(__name__)

class LotofacilAIv3:
    def __init__(self):
        self.historico_concursos: List[Concurso] = [] # Usando o modelo Concurso
        self.frequencias: Dict[int, int] = {}
        self.pesos_ia: Dict[str, float] = {}
        self.event_detector: Optional[EventDetector] = None
        self.concurso_anterior: Optional[Concurso] = None # Usando o modelo Concurso
        self.ultimo_concurso_numero: int = 0
        self.supabase_client: Optional[SupabaseClient] = None # Adicionado para acesso direto
        self.config_service: Optional[ConfigService] = None # Adicionado para acesso direto

    @classmethod
    async def create(cls, modo_offline: bool, mazusoft_data_path: str, db_client: SupabaseClient):
        """Método de fábrica assíncrono para inicializar a IA."""
        instance = cls()
        instance.supabase_client = db_client # Atribui o cliente Supabase
        instance.config_service = ConfigService() # Obtém a instância singleton do ConfigService
        await instance._carregar_dados_iniciais()
        await instance._inicializar_componentes(mazusoft_data_path) # Passa o path aqui
        return instance

    async def _carregar_dados_iniciais(self):
        logger.info("Carregando dados iniciais do Supabase...")
        if not self.supabase_client:
            raise RuntimeError("SupabaseClient não inicializado no LotofacilAIv3.")

        # Carregar histórico de concursos
        historico_raw = await self.supabase_client.get_historico_concursos()
        if not historico_raw:
            raise RuntimeError("Nenhum histórico de concursos encontrado. Por favor, importe os dados.")

        # Converte os dicionários brutos em objetos Concurso
        self.historico_concursos = [Concurso(**c) for c in historico_raw]

        # Ordenar por número de concurso para garantir a sequência
        self.historico_concursos.sort(key=lambda x: x.numero)
        self.concurso_anterior = self.historico_concursos[-1]
        self.ultimo_concurso_numero = self.concurso_anterior.numero

        # Carregar frequências
        frequencias_db = await self.supabase_client.get_frequencias()
        self.frequencias = {f['dezena']: f['ocorrencias'] for f in frequencias_db}

        # Carregar pesos da IA
        if not self.config_service:
            raise RuntimeError("ConfigService não inicializado no LotofacilAIv3.")
        self.pesos_ia = await self.config_service.get_pesos_ia_atuais()
        if not self.pesos_ia:
            logger.warning("Pesos da IA não encontrados. Usando pesos padrão e registrando.")
            default_pesos = self.config_service._pesos_default() # Pega os pesos default do ConfigService
            await self.config_service.registrar_nova_versao_pesos(default_pesos, "Pesos padrão iniciais (gerados automaticamente)")
            self.pesos_ia = default_pesos # Atualiza com os pesos default registrados

        logger.info(f"✅ Dados iniciais carregados. Último concurso: {self.ultimo_concurso_numero}")
        logger.info(f"   Pesos da IA: {self.pesos_ia}")

    async def _inicializar_componentes(self, mazusoft_data_path: str):
        logger.info("Inicializando componentes do motor de IA...")

        # Carrega o histórico de dezenas sorteadas para o EventDetector
        dezenas_historicas = [c.dezenas_sorteadas for c in self.historico_concursos]

        # Inicializa o EventDetector
        self.event_detector = EventDetector(
            historico_file="eventos_raros.json",
            historico_dezenas_sorteadas=dezenas_historicas
        )
        logger.info("✅ EventDetector inicializado.")

        # Outros componentes podem ser inicializados aqui (Mazusoft, GeneticOptimizer, etc.)
        # Por enquanto, mantemos o foco no que é essencial para o erro atual.
        logger.info("✅ Componentes do motor de IA inicializados.")

    def _calcular_metricas_jogo(self, jogo: List[int]) -> Dict[str, Any]:
        """Calcula as métricas de um jogo para avaliação."""
        jogo_ordenado = sorted(jogo)

        # Métricas básicas
        soma = sum(jogo_ordenado)
        pares = sum(1 for d in jogo_ordenado if d % 2 == 0)
        impares = 15 - pares

        # Frequência
        frequencia_total = sum(self.frequencias.get(d, 0) for d in jogo_ordenado)

        # Repetidas do concurso anterior
        repetidas = 0
        if self.concurso_anterior and self.concurso_anterior.dezenas_sorteadas:
            repetidas = len(set(jogo_ordenado).intersection(self.concurso_anterior.dezenas_sorteadas))

        # Ciclo (simplificado: quantas dezenas do jogo estão no ciclo atual)
        ciclo_count = 0
        if self.concurso_anterior and self.concurso_anterior.ausentes:
            ciclo_count = len(set(jogo_ordenado).intersection(self.concurso_anterior.ausentes))

        # Outras métricas (primos, fibonacci, moldura, centro, multiplos_3, sequências, etc.)
        primos = len([d for d in jogo_ordenado if d in [2, 3, 5, 7, 11, 13, 17, 19, 23]])
        fibonacci = len([d for d in jogo_ordenado if d in [1, 2, 3, 5, 8, 13, 21]])
        multiplos_3 = len([d for d in jogo_ordenado if d % 3 == 0])
        moldura = len([d for d in jogo_ordenado if d in [1,2,3,4,5, 6,10,11,15,16,20,21,22,23,24,25]])
        centro = len([d for d in jogo_ordenado if d in [7,8,9,12,13,14,17,18,19]])

        # Análise de sequências (usando EventDetector ou lógica própria)
        # Para esta versão, vamos usar as implementações básicas do EventDetector
        grupos_sequencia, max_consecutivo, blocos = self.event_detector._analisar_sequencias(jogo_ordenado)
        densidade_espacial = self.event_detector._calcular_densidade_espacial(jogo_ordenado)

        return {
            "soma": soma,
            "pares": pares,
            "impares": impares,
            "frequencia": frequencia_total,
            "repetidas": repetidas,
            "ciclo": ciclo_count,
            "primos": primos,
            "fibonacci": fibonacci,
            "multiplos_3": multiplos_3,
            "moldura": moldura,
            "centro": centro,
            "grupos_sequencia": grupos_sequencia,
            "max_consecutivo": max_consecutivo,
            "densidade_espacial": densidade_espacial,
        }

    def _calcular_fitness(self, jogo: List[int], metricas: Dict[str, Any]) -> float:
        """Calcula o fitness (pontuação) de um jogo com base nos pesos da IA."""
        fitness_score = 0.0

        # Normalização e aplicação de pesos
        # Usando os pesos carregados de pesos_ia

        # Soma (ideal 205, desvio 30)
        soma_norm = 1 - abs(metricas['soma'] - 205) / 60
        fitness_score += self.pesos_ia.get("soma", 0.0) * soma_norm

        # Pares (ideal 7-8)
        pares_norm = 1 - abs(metricas['pares'] - 7.5) / 7.5
        fitness_score += self.pesos_ia.get("pares", 0.0) * pares_norm

        # Frequência (quanto maior, melhor)
        max_freq_historica = max(self.frequencias.values()) * 15 if self.frequencias else 1
        freq_norm = metricas['frequencia'] / max_freq_historica
        fitness_score += self.pesos_ia.get("frequencia", 0.0) * freq_norm

        # Repetidas (ideal 8-10)
        repetidas_norm = 1 - abs(metricas['repetidas'] - 9) / 9
        fitness_score += self.pesos_ia.get("repetidas", 0.0) * repetidas_norm

        # Ausentes (ideal 5-7)
        ausentes_norm = 1 - abs(metricas['ciclo'] - 6) / 6
        fitness_score += self.pesos_ia.get("ausentes", 0.0) * ausentes_norm

        # Outras métricas...
        primos_norm = 1 - abs(metricas['primos'] - 5) / 5
        fitness_score += self.pesos_ia.get("primos", 0.0) * primos_norm

        fibonacci_norm = 1 - abs(metricas['fibonacci'] - 4) / 4
        fitness_score += self.pesos_ia.get("fibonacci", 0.0) * fibonacci_norm

        multiplos_3_norm = 1 - abs(metricas['multiplos_3'] - 5) / 5
        fitness_score += self.pesos_ia.get("multiplos_3", 0.0) * multiplos_3_norm

        moldura_norm = 1 - abs(metricas['moldura'] - 10) / 10
        fitness_score += self.pesos_ia.get("moldura", 0.0) * moldura_norm

        centro_norm = 1 - abs(metricas['centro'] - 5) / 5
        fitness_score += self.pesos_ia.get("centro", 0.0) * centro_norm

        # Adicione outras métricas conforme seus pesos_ia
        # Exemplo para 'sequencia_longa' e 'densidade'
        # if "sequencia_longa" in self.pesos_ia:
        #     seq_longa_norm = metricas['max_consecutivo'] / 15 # Normaliza
        #     fitness_score += self.pesos_ia.get("sequencia_longa", 0.0) * seq_longa_norm

        # if "densidade" in self.pesos_ia:
        #     fitness_score += self.pesos_ia.get("densidade", 0.0) * metricas['densidade_espacial']

        return fitness_score

    def _gerar_jogo_aleatorio(self) -> List[int]:
        """Gera um jogo aleatório de 15 dezenas."""
        return sorted(random.sample(range(1, 26), 15))

    async def gerar_jogos(self, quantidade_jogos: int = 30, concurso_alvo: Optional[int] = None) -> Dict[str, Any]:
        """
        Gera um lote de jogos otimizados pela IA.
        Salva o lote na tabela jogos_gerados e retorna os detalhes.
        """
        if concurso_alvo is None:
            concurso_alvo = self.ultimo_concurso_numero + 1

        logger.info(f"Gerando {quantidade_jogos} jogos para o concurso {concurso_alvo}...")

        jogos_candidatos = []
        num_candidatos = quantidade_jogos * 100 # Gerar mais candidatos para seleção

        for _ in range(num_candidatos):
            jogo = self._gerar_jogo_aleatorio()
            metricas = self._calcular_metricas_jogo(jogo)
            fitness = self._calcular_fitness(jogo, metricas)
            jogos_candidatos.append({"jogo": jogo, "fitness": fitness, "metricas": metricas})

        # Selecionar os jogos com maior fitness
        jogos_candidatos.sort(key=lambda x: x["fitness"], reverse=True)
        jogos_selecionados_raw = jogos_candidatos[:quantidade_jogos]

        # Formatar para a resposta e salvar no banco
        jogos_para_db = []
        jogos_para_resposta = []
        for jogo_data in jogos_selecionados_raw:
            # Aqui você pode formatar o jogo para o modelo JogoGerado se quiser mais detalhes no DB
            # Por enquanto, vamos salvar apenas as dezenas na lista 'jogos' da tabela jogos_gerados
            jogos_para_db.append(jogo_data["jogo"])
            jogos_para_resposta.append(jogo_data["jogo"]) # Para a resposta do endpoint

        # Obter custo do jogo do ConfigService
        if not self.config_service:
            raise RuntimeError("ConfigService não inicializado no LotofacilAIv3.")
        config = await self.config_service.get_config_lotofacil()
        custo_jogo = float(config.get("custo_jogo", 3.50))
        custo_total = quantidade_jogos * custo_jogo

        # Salvar jogos gerados no Supabase
        id_lote = str(uuid.uuid4())
        registro_salvo = await self.supabase_client.salvar_jogos_gerados(
            id=id_lote,
            concurso_alvo=concurso_alvo,
            quantidade_jogos=quantidade_jogos,
            jogos=jogos_para_db, # Salva apenas as dezenas
            data_geracao=datetime.now().isoformat(),
            custo_total=custo_total,
            status_conferencia="pendente"
        )

        logger.info(f"✅ {quantidade_jogos} jogos gerados e salvos para o concurso {concurso_alvo}.")
        logger.info(f"   ID do lote: {registro_salvo['id']}")
        logger.info(f"   Custo total: R$ {custo_total:.2f}")

        return {
            "jogos_gerados_id": registro_salvo['id'],
            "concurso_alvo": concurso_alvo,
            "quantidade_jogos": quantidade_jogos,
            "jogos": jogos_para_resposta,
            "custo_total": custo_total,
            "data_geracao": datetime.now().isoformat() # Retorna como string ISO para o endpoint
        }

    # Métodos para o módulo de aprendizado da IA (futuro)
    async def _analisar_desempenho_lote(self, resultados_conferencia_id: int):
        """Analisa o desempenho de um lote de jogos e retorna insights para ajuste de pesos."""
        pass

    async def _ajustar_pesos_ia(self, insights: Dict[str, Any]):
        """Ajusta os pesos da IA com base nos insights de desempenho."""
        pass

    async def _registrar_historico_treinamento(self, episodio_data: Dict[str, Any]):
        """Registra um episódio de treinamento na tabela historico_treinamento."""
        pass
