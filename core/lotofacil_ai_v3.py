"""
Lotofacil AI Engine v3.0 - Sistema Completo
Combina Algoritmo Genético + Análise Mazusoft + Aprendizado por Reforço
Autor: Inner AI + Jose Eduardo França
Data: Novembro 2025
"""

import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import Counter
import random
import itertools
import json
from datetime import datetime
import sys
import os

# Adicionar diretório pai ao path para imports absolutos
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Importar módulos auxiliares com fallback
try:
    from core.genetic_algorithm import GeneticOptimizer
    from core.fitness_modules import FitnessCalculator
    from core.mazusoft_integration import MazusoftAnalyzer
    from core.event_detector import EventDetector
    from core.reinforcement_learning import QLearningAgent
    from database.supabase_manager import SupabaseManager
    from utils.validators import GameValidator
    MODO_COMPLETO = True
except ImportError as e:
    logging.warning(f"Módulos auxiliares não encontrados: {e}. Usando modo simplificado.")
    MODO_COMPLETO = False
    
    # Criar classes stub para evitar NameError
    class GeneticOptimizer:
        def __init__(self, config=None): pass
        def gerar_populacao_inicial(self, **kwargs): return []
        def evoluir(self, **kwargs): return kwargs.get('populacao', [])
    
    class FitnessCalculator:
        def __init__(self): pass
        def calcular(self, jogo, pesos=None): return 0.75
        def calcular_confianca(self, jogo, validacao, contexto): return 0.75
    
    class MazusoftAnalyzer:
        def __init__(self, data_path): pass
        def load_all_stats(self): return {}
        def get_probabilidades_frequencia(self): return {n: 0.5 for n in range(1, 26)}
        def get_probabilidades_ciclo(self): return {n: 0.5 for n in range(1, 26)}
        def get_probabilidades_gap(self): return {n: 0.5 for n in range(1, 26)}
        def calcular_temperatura_atual(self): return 'normal'
        def atualizar_com_resultado(self, resultado): pass
    
    class EventDetector:
        def __init__(self, **kwargs): pass
        def classificar(self, jogo, concurso=None, historico=None):
            from enum import Enum
            class EventType(Enum):
                NORMAL = "normal"
            class EventoRaro:
                def __init__(self):
                    self.tipo = EventType.NORMAL
                    self.probabilidade = 0.0
                    self.impacto = 0.0
            return False, EventType.NORMAL, EventoRaro()
        def detectar_precursor_salto(self, historico): return False
    
    class QLearningAgent:
        def __init__(self, **kwargs):
            self.epsilon = 0.15
            self.episode_count = 0
        def load_q_table(self): return False
        def load_weights(self): return {}
        def choose_action(self, state): return {}
        def apply_action(self, action, weights): return weights
        def calculate_reward(self, acertos): return 0.0
        def update(self, state, action, reward, next_state): pass
        def save_weights(self, weights): pass
        def reset_episode(self): pass
        def ajustar_para_anti_salto(self, pesos): return pesos
        def register_rare_event(self, tipo, state, impacto): pass
        def get_performance_metrics(self): return {}
    
    class SupabaseManager:
        def __init__(self, url, key): pass
        def get_ultimos_concursos(self, limite): return {}
        def salvar_jogo_gerado(self, **kwargs): pass
        def salvar_concurso(self, concurso, resultado): pass
        def get_jogos_por_concurso(self, concurso): return []
        def atualizar_acertos(self, jogo_id, acertos): pass
        def salvar_evento_raro(self, concurso, tipo, resultado): pass
    
    class GameValidator:
        def __init__(self): pass
        def validar_completo(self, jogo, constraints):
            soma = sum(jogo)
            pares = sum(1 for n in jogo if n % 2 == 0)
            return True, {'soma': soma, 'pares': pares, 'impares': 15-pares}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LotofacilAIv3:
    """Motor de IA Completo v3.0 com Aprendizado por Reforço"""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        mazusoft_data_path: str = "data/mazusoft_data.json",
        config: Optional[Dict] = None,
        modo_offline: bool = True
    ):
        """Inicializa o Motor de IA v3.0"""
        logger.info("="*70)
        logger.info(" "*20 + "LOTOFACIL AI ENGINE v3.0")
        logger.info(" "*15 + "Sistema Completo com Q-Learning")
        logger.info("="*70)
        
        if not MODO_COMPLETO:
            logger.warning("⚠️ Rodando em MODO SIMPLIFICADO (módulos auxiliares não carregados)")
        
        self.modo_offline = modo_offline
        self.config = config or {}
        
        # Componentes principais
        if not modo_offline and supabase_url and supabase_key:
            try:
                self.db = SupabaseManager(supabase_url, supabase_key)
                logger.info("✅ Conexão Supabase estabelecida")
            except Exception as e:
                logger.warning(f"⚠️ Falha ao conectar Supabase: {e}. Usando modo offline.")
                self.modo_offline = True
                self.db = None
        else:
            self.db = None
            logger.info("📴 Modo offline ativado")
        
        # Inicializar componentes de análise
        try:
            self.mazusoft = MazusoftAnalyzer(mazusoft_data_path)
            logger.info("✅ Analisador Mazusoft carregado")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar Mazusoft: {e}")
            self.mazusoft = MazusoftAnalyzer(mazusoft_data_path)
        
        try:
            self.genetic = GeneticOptimizer(config)
            logger.info("✅ Otimizador Genético inicializado")
        except Exception as e:
            logger.warning(f"⚠️ Otimizador Genético não disponível: {e}")
            self.genetic = GeneticOptimizer(config)
        
        try:
            self.fitness_calc = FitnessCalculator()
            logger.info("✅ Calculador de Fitness carregado")
        except Exception as e:
            logger.warning(f"⚠️ Calculador de Fitness não disponível: {e}")
            self.fitness_calc = FitnessCalculator()
        
        # Inicializar Detector de Eventos Raros
        try:
            self.event_detector = EventDetector(
                historico_file="data/eventos_raros.json",
                threshold_anomalia=0.95,
                min_ocorrencias=3,
                window_analise=5
            )
            logger.info("✅ Detector de Eventos Raros inicializado")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Event Detector: {e}")
            self.event_detector = EventDetector()
        
        # Integração Q-Learning
        try:
            self.q_agent = QLearningAgent(
                learning_rate=0.1,
                discount_factor=0.95,
                epsilon=0.15,
                epsilon_decay=0.995,
                min_epsilon=0.01,
                weights_file="data/lotofacil_weights.json",
                q_table_file="data/lotofacil_q_table.json"
            )
            
            if self.q_agent.load_q_table():
                logger.info("✅ Q-table carregada do histórico")
            else:
                logger.info("📝 Q-table nova inicializada")
            
            logger.info("🤖 Agente Q-Learning integrado ao motor principal")
            logger.info(f"   Epsilon inicial: {self.q_agent.epsilon:.3f}")
            logger.info(f"   Episódios anteriores: {self.q_agent.episode_count}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Q-Learning: {e}")
            self.q_agent = QLearningAgent()
        
        # Inicializar validador
        try:
            self.validator = GameValidator()
            logger.info("✅ Validador de Jogos carregado")
        except Exception as e:
            logger.warning(f"⚠️ Validador não disponível: {e}")
            self.validator = GameValidator()
        
        # Carregar dados históricos
        self.historico = self._carregar_historico()
        self.mazusoft_stats = self._carregar_mazusoft_stats()
        
        # Estado do aprendizado
        self.pesos_atuais = self.q_agent.load_weights() if self.q_agent else {}
        self.eventos_raros = []
        self.contexto_atual = {}
        self.ultima_acao = {}
        
        logger.info("="*70)
        logger.info("✅ Sistema inicializado com sucesso!")
        logger.info(f"   Modo: {'Offline' if self.modo_offline else 'Online (Supabase)'}")
        logger.info(f"   Histórico: {len(self.historico)} concursos")
        logger.info(f"   Pesos ativos: {len(self.pesos_atuais)} critérios")
        logger.info("="*70)

    def _carregar_historico(self) -> Dict[int, List[int]]:
        """Carrega histórico de concursos"""
        if not self.modo_offline and self.db:
            try:
                return self.db.get_ultimos_concursos(500)
            except Exception as e:
                logger.warning(f"Erro ao carregar histórico do Supabase: {e}")
        
        try:
            with open("data/concursos_historico.json", 'r') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except FileNotFoundError:
            logger.warning("Arquivo de histórico não encontrado. Iniciando vazio.")
            return {}
    
    def _carregar_mazusoft_stats(self) -> Dict:
        """Carrega estatísticas Mazusoft"""
        if self.mazusoft:
            try:
                return self.mazusoft.load_all_stats()
            except Exception as e:
                logger.warning(f"Erro ao carregar stats Mazusoft: {e}")
        return {}

    def gerar_jogos_inteligentes(
        self,
        num_jogos: int = 50,
        concurso_alvo: Optional[int] = None,
        modo: str = "normal"
    ) -> List[Dict]:
        """Gera jogos inteligentes com aprendizado contínuo"""
        logger.info(f"\n{'='*70}")
        logger.info(f" "*15 + f"GERANDO {num_jogos} JOGOS INTELIGENTES")
        logger.info(f" "*20 + f"Modo: {modo.upper()}")
        logger.info(f"{'='*70}\n")
        
        contexto = self._analisar_contexto()
        self.contexto_atual = contexto
        
        logger.info("📊 Contexto Atual:")
        logger.info(f"   Temperatura: {contexto.get('temperatura', 'N/A')}")
        logger.info(f"   Alerta Salto: {'SIM' if contexto.get('alerta_salto') else 'NÃO'}")
        logger.info(f"   Ciclos Quentes: {len(contexto.get('ciclos_quentes', []))}")
        
        if self.q_agent:
            state = {
                'temperatura': contexto.get('temperatura_score', 0.5),
                'alerta_salto': 1 if contexto.get('alerta_salto') else 0,
                'media_acertos': contexto.get('media_acertos', 10.0),
                'recorrencia': contexto.get('recorrencia', 0.5)
            }
            
            action = self.q_agent.choose_action(state)
            self.ultima_acao = action
            self.pesos_atuais = self.q_agent.apply_action(action, self.pesos_atuais)
            
            logger.info(f"🎯 Ação Q-Learning aplicada: {action}")
            logger.info(f"   Epsilon atual: {self.q_agent.epsilon:.3f}")
            logger.info(f"   Episódio: {self.q_agent.episode_count}")
        
        if contexto.get('alerta_salto') and self.q_agent:
            logger.warning("⚠️ ALERTA: Padrão precursor de salto detectado!")
            self.pesos_atuais = self.q_agent.ajustar_para_anti_salto(self.pesos_atuais)
            modo = "anti_salto"
        
        prob_matrix = self._calcular_probabilidades(contexto)
        constraints = self._definir_restricoes(modo)
        
        if self.genetic:
            try:
                populacao_inicial = self.genetic.gerar_populacao_inicial(
                    tamanho=700,
                    prob_matrix=prob_matrix
                )
                
                populacao_otimizada = self.genetic.evoluir(
                    populacao=populacao_inicial,
                    fitness_func=self.fitness_calc.calcular if self.fitness_calc else None,
                    geracoes=350,
                    pesos=self.pesos_atuais
                )
            except Exception as e:
                logger.error(f"Erro no GA: {e}. Usando geração simples.")
                populacao_otimizada = self._gerar_jogos_simples(num_jogos * 2, prob_matrix)
        else:
            populacao_otimizada = self._gerar_jogos_simples(num_jogos * 2, prob_matrix)
        
        jogos_validos = []
        for jogo in populacao_otimizada:
            if self.validator:
                valido, validacao = self.validator.validar_completo(jogo, constraints)
            else:
                valido, validacao = self._validar_simples(jogo, constraints)
            
            if valido:
                if self.fitness_calc:
                    confianca = self.fitness_calc.calcular_confianca(
                        jogo, validacao, contexto
                    )
                else:
                    confianca = 0.75
                
                eh_raro = False
                tipo_raro = None
                if self.event_detector:
                    try:
                        eh_raro, tipo_raro, evento = self.event_detector.classificar(
                            jogo, concurso_alvo, 
                            list(self.historico.values())[-5:]
                        )
                    except Exception as e:
                        logger.warning(f"Erro ao classificar evento: {e}")
                
                jogo_data = {
                    'jogo': jogo,
                    'validacao': validacao,
                    'confianca': confianca,
                    'evento_raro': eh_raro,
                    'tipo_raro': tipo_raro.value if tipo_raro and hasattr(tipo_raro, 'value') else None,
                    'contexto': contexto.get('resumo', ''),
                    'q_action': self.ultima_acao,
                    'episode': self.q_agent.episode_count if self.q_agent else 0
                }
                
                jogos_validos.append(jogo_data)
                
                if len(jogos_validos) >= num_jogos:
                    break
        
        if not self.modo_offline and self.db:
            for i, jogo_data in enumerate(jogos_validos, 1):
                try:
                    self.db.salvar_jogo_gerado(
                        concurso_alvo=concurso_alvo or (max(self.historico.keys()) + 1 if self.historico else 3500),
                        jogo=jogo_data['jogo'],
                        metadata=jogo_data,
                        algoritmo="LotofacilAI_v3.0"
                    )
                except Exception as e:
                    logger.warning(f"Erro ao salvar jogo {i}: {e}")
        else:
            self._salvar_jogos_local(jogos_validos, concurso_alvo)
        
        logger.info(f"\n{'='*70}")
        logger.info(f" "*15 + f"✅ {len(jogos_validos)} JOGOS GERADOS!")
        logger.info(f"{'='*70}\n")
        
        return jogos_validos

    def registrar_resultado(
        self,
        concurso: int,
        resultado: List[int],
        acertos_por_jogo: List[int]
    ):
        """Registra resultado e aprende com feedback"""
        logger.info(f"\n{'='*70}")
        logger.info(f" "*15 + f"REGISTRANDO RESULTADO - Concurso {concurso}")
        logger.info(f"{'='*70}\n")
        
        if not self.modo_offline and self.db:
            try:
                self.db.salvar_concurso(concurso, resultado)
            except Exception as e:
                logger.warning(f"Erro ao salvar concurso: {e}")
        
        self.historico[concurso] = resultado
        
        if not self.modo_offline and self.db:
            try:
                jogos_gerados = self.db.get_jogos_por_concurso(concurso)
                for jogo, acertos in zip(jogos_gerados, acertos_por_jogo):
                    self.db.atualizar_acertos(jogo['id'], acertos)
            except Exception as e:
                logger.warning(f"Erro ao atualizar acertos: {e}")
        
        if self.q_agent:
            recompensa = self.q_agent.calculate_reward(acertos_por_jogo)
            
            logger.info(f"📊 Análise de Performance:")
            logger.info(f"   Acertos: {acertos_por_jogo}")
            logger.info(f"   Média: {sum(acertos_por_jogo)/len(acertos_por_jogo) if acertos_por_jogo else 0:.2f}")
            logger.info(f"   Recompensa: {recompensa:.2f}")
            
            novo_contexto = self._analisar_contexto()
            next_state = {
                'temperatura': novo_contexto.get('temperatura_score', 0.5),
                'alerta_salto': 1 if novo_contexto.get('alerta_salto') else 0,
                'media_acertos': sum(acertos_por_jogo)/len(acertos_por_jogo) if acertos_por_jogo else 10.0,
                'recorrencia': novo_contexto.get('recorrencia', 0.5)
            }
            
            state_anterior = {
                'temperatura': self.contexto_atual.get('temperatura_score', 0.5),
                'alerta_salto': 1 if self.contexto_atual.get('alerta_salto') else 0,
                'media_acertos': self.contexto_atual.get('media_acertos', 10.0),
                'recorrencia': self.contexto_atual.get('recorrencia', 0.5)
            }
            
            self.q_agent.update(state_anterior, self.ultima_acao, recompensa, next_state)
            self.q_agent.save_weights(self.pesos_atuais)
            self.q_agent.reset_episode()
            
            logger.info(f"🎓 Aprendizado concluído - Recompensa: {recompensa:.2f}")
            logger.info(f"   Novo Epsilon: {self.q_agent.epsilon:.3f}")
        
        if self.event_detector:
            try:
                eh_raro, tipo, evento = self.event_detector.classificar(
                    resultado, concurso,
                    list(self.historico.values())[-5:]
                )
                
                if eh_raro:
                    self.eventos_raros.append({
                        'concurso': concurso,
                        'tipo': tipo.value if hasattr(tipo, 'value') else str(tipo),
                        'resultado': resultado,
                        'data': datetime.now().isoformat(),
                        'probabilidade': evento.probabilidade,
                        'impacto': evento.impacto
                    })
                    
                    logger.warning(f"🚨 EVENTO RARO DETECTADO: {tipo.value if hasattr(tipo, 'value') else tipo}")
                    logger.warning(f"   Probabilidade: {evento.probabilidade:.3f}")
                    logger.warning(f"   Impacto: {evento.impacto:+.3f}")
                    
                    if self.q_agent:
                        self.q_agent.register_rare_event(
                            tipo.value if hasattr(tipo, 'value') else str(tipo),
                            state_anterior,
                            evento.impacto
                        )
                    
                    if not self.modo_offline and self.db:
                        try:
                            self.db.salvar_evento_raro(concurso, tipo.value if hasattr(tipo, 'value') else str(tipo), resultado)
                        except Exception as e:
                            logger.warning(f"Erro ao salvar evento raro: {e}")
            except Exception as e:
                logger.warning(f"Erro ao detectar evento raro: {e}")
        
        if self.mazusoft:
            try:
                self.mazusoft.atualizar_com_resultado(resultado)
            except Exception as e:
                logger.warning(f"Erro ao atualizar Mazusoft: {e}")
        
        logger.info(f"\n{'='*70}")
        logger.info(f" "*15 + "✅ RESULTADO REGISTRADO COM SUCESSO!")
        logger.info(f"{'='*70}\n")

    def _analisar_contexto(self) -> Dict:
        """Analisa contexto atual para ajustar estratégia"""
        if not self.historico:
            return {
                'alerta_salto': False,
                'temperatura': 'normal',
                'temperatura_score': 0.5,
                'ciclos_quentes': [],
                'media_acertos': 10.0,
                'recorrencia': 0.5,
                'resumo': 'Sem histórico disponível'
            }
        
        ultimos_5 = list(self.historico.values())[-5:]
        
        alerta_salto = False
        if self.event_detector:
            try:
                alerta_salto = self.event_detector.detectar_precursor_salto(ultimos_5)
            except Exception as e:
                logger.warning(f"Erro ao detectar precursor: {e}")
        
        temperatura = 'normal'
        temperatura_score = 0.5
        if self.mazusoft:
            try:
                temperatura = self.mazusoft.calcular_temperatura_atual()
                temperatura_score = {'fria': 0.2, 'normal': 0.5, 'quente': 0.8}.get(temperatura, 0.5)
            except Exception as e:
                logger.warning(f"Erro ao calcular temperatura: {e}")
        
        ciclos_quentes = []
        if self.mazusoft_stats and 'ciclo_dezenas' in self.mazusoft_stats:
            ciclos_quentes = [
                d for d, info in self.mazusoft_stats['ciclo_dezenas'].items()
                if info.get('status') == 'quente'
            ]
        
        if len(ultimos_5) >= 2:
            recorrencia = len(set(ultimos_5[-1]) & set(ultimos_5[-2])) / 15
        else:
            recorrencia = 0.5
        
        return {
            'alerta_salto': alerta_salto,
            'temperatura': temperatura,
            'temperatura_score': temperatura_score,
            'ciclos_quentes': ciclos_quentes,
            'media_acertos': 10.0,
            'recorrencia': recorrencia,
            'resumo': f"Temp: {temperatura}, Salto: {alerta_salto}, Recorr: {recorrencia:.2f}"
        }

    def _calcular_probabilidades(self, contexto: Dict) -> Dict[int, float]:
        """Calcula matriz de probabilidade ajustada"""
        prob_matrix = {}
        
        if self.mazusoft:
            try:
                prob_frequencia = self.mazusoft.get_probabilidades_frequencia()
                prob_ciclo = self.mazusoft.get_probabilidades_ciclo()
                prob_gap = self.mazusoft.get_probabilidades_gap()
                
                w_freq = 0.4 if contexto['temperatura'] == 'quente' else 0.3
                w_ciclo = 0.4
                w_gap = 0.2
                
                for n in range(1, 26):
                    prob_matrix[n] = (
                        w_freq * prob_frequencia.get(n, 0.5) +
                        w_ciclo * prob_ciclo.get(n, 0.5) +
                        w_gap * prob_gap.get(n, 0.5)
                    )
            except Exception as e:
                logger.warning(f"Erro ao calcular probabilidades: {e}")
        
        if not prob_matrix:
            prob_matrix = {n: 0.5 for n in range(1, 26)}
        
        return prob_matrix

    def _definir_restricoes(self, modo: str) -> Dict:
        """Define restrições baseadas no modo"""
        base = {
            'soma': (175, 235),
            'pares': (6, 9),
            'fibonacci': (3, 5),
            'multiplos_3': (4, 6),
            'primos': (4, 7),
            'moldura': (10, 12),
            'centro': (3, 5),
            'max_consecutivo': 7
        }
        
        if modo == "anti_salto":
            base['max_consecutivo'] = 5
            base['densidade_max'] = 0.6
        elif modo == "agressivo":
            base['soma'] = (180, 230)
            base['max_consecutivo'] = 6
        
        return base

    def _gerar_jogos_simples(self, num: int, prob_matrix: Dict[int, float]) -> List[List[int]]:
        """Geração simples de jogos (fallback)"""
        jogos = []
        for _ in range(num):
            jogo = sorted(random.sample(range(1, 26), 15))
            jogos.append(jogo)
        return jogos

    def _validar_simples(self, jogo: List[int], constraints: Dict) -> Tuple[bool, Dict]:
        """Validação simples (fallback)"""
        soma = sum(jogo)
        pares = sum(1 for n in jogo if n % 2 == 0)
        
        valido = (
            constraints['soma'][0] <= soma <= constraints['soma'][1] and
            constraints['pares'][0] <= pares <= constraints['pares'][1]
        )
        
        validacao = {
            'soma': soma,
            'pares': pares,
            'impares': 15 - pares
        }
        
        return valido, validacao

    def _salvar_jogos_local(self, jogos: List[Dict], concurso: Optional[int]):
        """Salva jogos em arquivo local"""
        try:
            # Criar diretório data se não existir
            os.makedirs("data", exist_ok=True)
            
            filename = f"data/jogos_gerados_c{concurso or 'XXXX'}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'concurso_alvo': concurso,
                    'data_geracao': datetime.now().isoformat(),
                    'total_jogos': len(jogos),
                    'jogos': jogos
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Jogos salvos em: {filename}")
        except Exception as e:
            logger.error(f"Erro ao salvar jogos localmente: {e}")


if __name__ == "__main__":
    print("\n🧠 TESTE DO MOTOR LOTOFACIL AI v3.0")
    print("="*70)
    
    engine = LotofacilAIv3(
        modo_offline=True,
        mazusoft_data_path="data/mazusoft_data.json"
    )
    
    jogos = engine.gerar_jogos_inteligentes(
        num_jogos=5,
        concurso_alvo=3500,
        modo="normal"
    )
    
    print(f"\n📊 JOGOS GERADOS:")
    for i, jogo_data in enumerate(jogos, 1):
        print(f"\nJogo {i}:")
        print(f"   Dezenas: {jogo_data['jogo']}")
        print(f"   Confiança: {jogo_data['confianca']*100:.0f}%")
        print(f"   Evento Raro: {jogo_data['evento_raro']}")
        if jogo_data['evento_raro']:
            print(f"   Tipo: {jogo_data['tipo_raro']}")
    
    print(f"\n{'='*70}")
    print("SIMULANDO REGISTRO DE RESULTADO...")
    print(f"{'='*70}")
    
    resultado_simulado = [1, 2, 3, 5, 8, 11, 13, 15, 17, 19, 21, 23, 24, 25, 6]
    acertos_simulados = [11, 10, 12, 11, 13]
    
    engine.registrar_resultado(
        concurso=3500,
        resultado=resultado_simulado,
        acertos_por_jogo=acertos_simulados
    )
    
    print(f"\n{'='*70}")
    print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    print(f"{'='*70}\n")
