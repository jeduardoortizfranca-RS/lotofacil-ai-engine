# backend/core/event_detector.py

"""
Lotofacil AI Engine v3.0 - Detector de Eventos Raros
Identifica padrões anômalos e precursor de eventos estatisticamente raros
"""
import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter, defaultdict
from datetime import datetime
import json
import os
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Tipos de eventos raros detectáveis"""
    SALTO_CLUSTERIZADO = "salto_clusterizado"
    BLOCO_MASSIVO = "bloco_massivo"
    QUEBRA_EXTREMA = "quebra_extrema"
    DENSIDADE_ANOMALA = "densidade_anomala"
    FRONTEIRA_SOMA = "fronteira_soma"
    SEQUENCIA_FRIA = "sequencia_fria"
    PRECURSOR_SALTO = "precursor_salto"
    NORMAL = "normal"

@dataclass
class EventoRaro:
    """Estrutura para representar um evento raro"""
    tipo: EventType
    concurso: Optional[int] = None
    jogo: Optional[List[int]] = None
    metadados: Dict[str, Any] = None
    probabilidade: float = 0.0
    impacto: float = 0.0
    timestamp: str = None
    precursor: bool = False

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Converte para dicionário serializável"""
        return {
            **asdict(self),
            'tipo': self.tipo.value
        }

class EventDetector:
    """
    Detector inteligente de eventos raros e padrões preditivos
    Funcionalidades:
    - Classificação de jogos como normais ou anômalos
    - Detecção de precursores de eventos raros (saltos, quebras)
    - Análise de densidade espacial e temporal
    - Registro histórico para aprendizado contínuo
    """
    def __init__(
        self,
        historico_file: str = "eventos_raros.json",
        threshold_anomalia: float = 0.95,
        min_ocorrencias: int = 3,
        window_analise: int = 5,
        historico_dezenas_sorteadas: Optional[List[List[int]]] = None
    ):
        """
        Inicializa o detector de eventos
        Args:
            historico_file: Arquivo para persistir eventos raros
            threshold_anomalia: Limite para classificar como anômalo (percentil)
            min_ocorrencias: Mínimo de ocorrências para detectar padrão
            window_analise: Janela de concursos para análise de precursores
            historico_dezenas_sorteadas: Opcional. Histórico de dezenas para calcular baseline.
        """
        logger.info("Inicializando Detector de Eventos Raros...")
        self.historico_file = historico_file
        self.threshold_anomalia = threshold_anomalia
        self.min_ocorrencias = min_ocorrencias
        self.window_analise = window_analise

        # Constantes estatísticas (baseadas em análise Mazusoft)
        self.ESTATISTICAS_NORMAIS = {
            'soma': (175, 235),
            'pares': (6, 9),
            'impares': (6, 9),
            'fibonacci': (3, 5),
            'primos': (4, 7),
            'multiplos_3': (4, 6),
            'moldura': (10, 12),
            'centro': (3, 5),
            'grupos_sequencia': (3, 8),
            'max_consecutivo': (1, 7),
            'densidade_espacial': (0.3, 0.7)
        }
        # Padrões de eventos raros
        self.PADROES_RAROS = {
            EventType.SALTO_CLUSTERIZADO: {
                'descricao': 'Sequências longas com saltos curtos entre blocos',
                'criterios': {
                    'num_blocos': (3, 5),
                    'total_consecutivas': (8, 12),
                    'saltos_medio': (1.5, 3.5),
                    'soma': (220, 245)
                },
                'probabilidade_base': 0.008,
                'impacto': -0.25
            },
            EventType.BLOCO_MASSIVO: {
                'descricao': 'Bloco consecutivo de 6+ números',
                'criterios': {
                    'max_consecutivo': (6, 8),
                    'posicao_bloco': ['centro', 'final'],
                    'densidade_local': (0.8, 1.0)
                },
                'probabilidade_base': 0.015,
                'impacto': -0.15
            },
            EventType.QUEBRA_EXTREMA: {
                'descricao': 'Quebra total de padrão (menos de 6 repetidas)',
                'criterios': {
                    'repetidas': (0, 5),
                    'mudanca_soma': (20, 50),
                    'mudanca_paridade': True
                },
                'probabilidade_base': 0.012,
                'impacto': -0.30
            },
            EventType.FRONTEIRA_SOMA: {
                'descricao': 'Soma fora do intervalo normal (150-260)',
                'criterios': {
                    'soma': [(140, 170), (240, 270)],
                    'desvio_padrao': (1.5, 3.0)
                },
                'probabilidade_base': 0.020,
                'impacto': -0.10
            },
            EventType.SEQUENCIA_FRIA: {
                'descricao': 'Múltiplas dezenas com alto atraso (>15 concursos)',
                'criterios': {
                    'dezenas_frias': (5, 8),
                    'atraso_medio': (15, 25),
                    'regiao_fria': ['inicial', 'final']
                },
                'probabilidade_base': 0.018,
                'impacto': 0.20
            }
        }
        # Histórico de eventos
        self.historico_eventos = self._carregar_historico()
        self.padroes_detectados = defaultdict(list)
        self.precursores_mapeados = defaultdict(list)

        # Métricas de baseline (calculadas dinamicamente)
        self.baseline_stats = {}
        if historico_dezenas_sorteadas:
            logger.info("Calculando baseline stats a partir do histórico de dezenas fornecido...")
            self.baseline_stats = self._calcular_baseline_stats(historico_dezenas_sorteadas)
            logger.info(f"✅ Baseline stats calculadas: {self.baseline_stats}")
        else:
            logger.warning("Nenhum histórico de dezenas fornecido para calcular baseline stats. Usando defaults.")

        logger.info(f"✅ Detector inicializado")
        logger.info(f"   Threshold anomalia: {threshold_anomalia}")
        logger.info(f"   Eventos históricos: {len(self.historico_eventos)}")

    def _carregar_historico(self) -> List[EventoRaro]:
        """Carrega histórico de eventos raros"""
        if os.path.exists(self.historico_file):
            try:
                with open(self.historico_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                eventos = []
                for item in data:
                    try:
                        evento = EventoRaro(
                            tipo=EventType(item['tipo']),
                            concurso=item.get('concurso'),
                            jogo=item.get('jogo'),
                            metadados=item.get('metadados', {}),
                            probabilidade=item.get('probabilidade', 0.0),
                            impacto=item.get('impacto', 0.0),
                            timestamp=item.get('timestamp'),
                            precursor=item.get('precursor', False)
                        )
                        eventos.append(evento)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Evento inválido no histórico: {e}")
                logger.info(f"✅ {len(eventos)} eventos carregados do histórico")
                return eventos
            except Exception as e:
                logger.error(f"Erro ao carregar histórico: {e}")
        logger.info("📝 Histórico vazio - iniciando novo")
        return []

    def _salvar_historico(self):
        """Salva histórico de eventos"""
        try:
            data = [evento.to_dict() for evento in self.historico_eventos]
            with open(self.historico_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Histórico salvo: {len(data)} eventos")
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")

    def _calcular_desvios(self, analise: Dict) -> Dict[str, float]:
        """Calcula desvios em relação à norma"""
        basico = analise['basico']
        sequencias = analise['sequencias']
        espacial = analise['espacial']
        desvios = {}
        # Desvios para métricas contínuas
        # Usar baseline_stats se disponível, senão usar valores fixos
        soma_media = self.baseline_stats.get('soma_media', 205)
        soma_std = self.baseline_stats.get('soma_std', 30.0)
        pares_media = self.baseline_stats.get('pares_media', 7.5)
        pares_std = self.baseline_stats.get('pares_std', 1.5)
        fibonacci_media = self.baseline_stats.get('fibonacci_media', 4)
        fibonacci_std = self.baseline_stats.get('fibonacci_std', 1.0)
        primos_media = self.baseline_stats.get('primos_media', 5.5)
        primos_std = self.baseline_stats.get('primos_std', 1.5)
        multiplos_3_media = self.baseline_stats.get('multiplos_3_media', 5)
        multiplos_3_std = self.baseline_stats.get('multiplos_3_std', 1.0)
        moldura_media = self.baseline_stats.get('moldura_media', 11)
        moldura_std = self.baseline_stats.get('moldura_std', 1.0)
        grupos_sequencia_media = self.baseline_stats.get('grupos_sequencia_media', 5.5)
        grupos_sequencia_std = self.baseline_stats.get('grupos_sequencia_std', 1.5)
        max_consecutivo_media = self.baseline_stats.get('max_consecutivo_media', 3)
        max_consecutivo_std = self.baseline_stats.get('max_consecutivo_std', 2.0)
        densidade_espacial_media = self.baseline_stats.get('densidade_espacial_media', 0.5)
        densidade_espacial_std = self.baseline_stats.get('densidade_espacial_std', 0.2)


        desvios['soma'] = abs(basico['soma'] - soma_media) / (soma_std if soma_std else 1.0)
        desvios['pares'] = abs(basico['pares'] - pares_media) / (pares_std if pares_std else 1.0)
        desvios['fibonacci'] = abs(basico['fibonacci'] - fibonacci_media) / (fibonacci_std if fibonacci_std else 1.0)
        desvios['primos'] = abs(basico['primos'] - primos_media) / (primos_std if primos_std else 1.0)
        desvios['multiplos_3'] = abs(basico['multiplos_3'] - multiplos_3_media) / (multiplos_3_std if multiplos_3_std else 1.0)
        desvios['moldura'] = abs(basico['moldura'] - moldura_media) / (moldura_std if moldura_std else 1.0)
        desvios['grupos_sequencia'] = abs(sequencias['grupos_sequencia'] - grupos_sequencia_media) / (grupos_sequencia_std if grupos_sequencia_std else 1.0)
        desvios['max_consecutivo'] = abs(sequencias['max_consecutivo'] - max_consecutivo_media) / (max_consecutivo_std if max_consecutivo_std else 1.0)
        desvios['densidade_espacial'] = abs(espacial['densidade_espacial'] - densidade_espacial_media) / (densidade_espacial_std if densidade_espacial_std else 1.0)
        return desvios

    def _classificar_tipo_anomalia(self, analise: Dict, 
                                   historico_recente: Optional[List[List[int]]] = None) -> Tuple[EventType, Dict]:
        """Classifica o tipo específico de anomalia"""
        basico = analise['basico']
        sequencias = analise['sequencias']
        espacial = analise['espacial']
        # Verificar cada tipo de evento raro
        for tipo, criterios in self.PADROES_RAROS.items():
            if self._verificar_criterios(tipo, criterios['criterios'], analise):
                metadados = self._extrair_metadados(tipo, analise)
                return tipo, metadados
        # Se não encaixa em nenhum padrão específico, classificar como densidade anômala
        return EventType.DENSIDADE_ANOMALA, {
            'motivo': 'Distribuição espacial atípica',
            'densidade': espacial['densidade_espacial'],
            'entropia': espacial['entropia']
        }

    def _verificar_criterios(self, tipo: EventType, criterios: Dict, 
                             analise: Dict) -> bool:
        """Verifica se um jogo atende aos critérios de um tipo de evento"""
        basico = analise['basico']
        sequencias = analise['sequencias']
        espacial = analise['espacial']
        for criterio, valor in criterios.items():
            if isinstance(valor, tuple):
                # Intervalo numérico
                if criterio == 'soma':
                    if not (valor[0] <= basico['soma'] <= valor[1]):
                        return False
                elif criterio == 'num_blocos':
                    if not (valor[0] <= sequencias['grupos_sequencia'] <= valor[1]):
                        return False
                elif criterio == 'total_consecutivas':
                    total_cons = sum(1 for b in sequencias['blocos'] if len(b) >= 2)
                    if not (valor[0] <= total_cons <= valor[1]):
                        return False
                elif criterio == 'saltos_medio':
                    if 'saltos' not in sequencias or 'saltos_medio' not in sequencias['saltos'] or \
                       not (valor[0] <= sequencias['saltos']['saltos_medio'] <= valor[1]):
                        return False
                elif criterio == 'max_consecutivo':
                    if not (valor[0] <= sequencias['max_consecutivo'] <= valor[1]):
                        return False
                elif criterio == 'dezenas_frias':
                    continue
            elif isinstance(valor, list):
                # Lista de valores aceitáveis ou lista de intervalos
                if criterio == 'posicao_bloco':
                    blocos = sequencias['blocos']
                    posicao_identificada = self._identificar_posicao_bloco(blocos)
                    if not any(pos in valor for pos in [posicao_identificada]):
                        return False
                elif criterio == 'soma':
                    soma_atual = basico['soma']
                    if not any(intervalo[0] <= soma_atual <= intervalo[1] for intervalo in valor):
                        return False
            elif isinstance(valor, bool):
                # Critério booleano
                if criterio == 'mudanca_paridade':
                    continue
                elif criterio == 'mudanca_soma':
                    continue
        return True

    def _calcular_percentil_soma(self, soma: int) -> float:
        """Calcula percentil da soma baseado no histórico"""
        soma_media = self.baseline_stats.get('soma_media', 205)
        soma_std = self.baseline_stats.get('soma_std', 30.0)

        if soma_std == 0:
            return 0.5

        z_score = (soma - soma_media) / soma_std
        if z_score < -3:
            return 0.001
        elif z_score > 3:
            return 0.999
        else:
            percentil = 0.5 + (z_score / 6.0)
            return max(0.0, min(1.0, percentil))

    def _jogos_similares(self, jogo1: Optional[List[int]], jogo2_basico_analise: Dict) -> bool:
        """Verifica se dois jogos são similares"""
        if jogo1 is None:
            return False
        soma1 = sum(jogo1)
        soma2 = jogo2_basico_analise.get('soma', 0)
        diff_soma = abs(soma1 - soma2) / soma1 if soma1 > 0 else 1.0
        return diff_soma < 0.1

    def _calcular_probabilidade_evento(self, tipo: EventType, 
                                       analise: Dict) -> float:
        """Calcula probabilidade específica do evento baseado no histórico"""
        if tipo == EventType.NORMAL:
            return 1.0
        base_prob = self.PADROES_RAROS[tipo]['probabilidade_base']
        eventos_similares = sum(1 for e in self.historico_eventos 
                                if e.tipo == tipo and self._jogos_similares(e.jogo, analise['basico']))
        if eventos_similares >= self.min_ocorrencias:
            ajuste_historico = min(0.3, eventos_similares * 0.05)
            base_prob += ajuste_historico
        score_anomalia = analise['estatisticas']['score_anomalia']
        ajuste_intensidade = (score_anomalia - self.threshold_anomalia) * 0.5
        return min(base_prob + ajuste_intensidade, 1.0)

    def detectar_precursor_salto(self, historico_recente: List[List[int]]) -> bool:
        """
        Detecta padrão precursor de evento de salto
        Args:
            historico_recente: Últimos 3-5 jogos
        Returns:
            True se detectar padrão precursor
        """
        if len(historico_recente) < 3:
            return False
        jogos_recentes = historico_recente[-3:]
        count = 0
        for jogo in jogos_recentes:
            analise = self.analisar_jogo(jogo)
            if (analise['basico']['soma'] > 180 and 
                analise['sequencias']['max_consecutivo'] >= 4 and 
                3 <= analise['sequencias']['grupos_sequencia'] <= 4):
                count += 1
        return count >= 3

    # Métodos auxiliares (implementações completas)
    def analisar_jogo(self, jogo: List[int], concurso: Optional[int] = None) -> Dict[str, Any]:
        """Análise completa do jogo."""
        jogo_ordenado = sorted(jogo)
        soma = sum(jogo_ordenado)
        pares = sum(1 for d in jogo_ordenado if d % 2 == 0)
        impares = 15 - pares

        grupos_seq, max_cons, blocos = self._analisar_sequencias(jogo_ordenado)

        densidade_espacial = self._calcular_densidade_espacial(jogo_ordenado)
        entropia = self._calcular_entropia(jogo_ordenado)

        # Placeholder para score_anomalia, você pode implementar uma lógica mais complexa
        score_anomalia = self._calcular_score_anomalia({'basico': {'soma': soma, 'pares': pares, 'impares': impares},
                                                         'sequencias': {'grupos_sequencia': grupos_seq, 'max_consecutivo': max_cons, 'blocos': blocos, 'saltos': {}},
                                                         'espacial': {'densidade_espacial': densidade_espacial, 'entropia': entropia}})

        return {
            'basico': {'soma': soma, 'pares': pares, 'impares': impares},
            'sequencias': {'grupos_sequencia': grupos_seq, 'max_consecutivo': max_cons, 'blocos': blocos, 'saltos': {}},
            'espacial': {'densidade_espacial': densidade_espacial, 'entropia': entropia},
            'estatisticas': {'score_anomalia': score_anomalia}
        }

    def _analisar_sequencias(self, jogo_ordenado: List[int]) -> Tuple[int, int, List[List[int]]]:
        """Análise de sequências."""
        blocos = []
        if jogo_ordenado:
            current_block = [jogo_ordenado[0]]
            for i in range(1, len(jogo_ordenado)):
                if jogo_ordenado[i] == jogo_ordenado[i-1] + 1:
                    current_block.append(jogo_ordenado[i])
                else:
                    blocos.append(current_block)
                    current_block = [jogo_ordenado[i]]
            blocos.append(current_block)

        grupos_sequencia = len([b for b in blocos if len(b) >= 2])
        max_consecutivo = max([len(b) for b in blocos]) if blocos else 0
        return grupos_sequencia, max_consecutivo, blocos

    def _dividir_em_blocos(self, jogo_ordenado: List[int]) -> List[List[int]]:
        """Divide em blocos."""
        blocos = []
        if not jogo_ordenado:
            return blocos

        current_block = [jogo_ordenado[0]]
        for i in range(1, len(jogo_ordenado)):
            if jogo_ordenado[i] == jogo_ordenado[i-1] + 1:
                current_block.append(jogo_ordenado[i])
            else:
                blocos.append(current_block)
                current_block = [jogo_ordenado[i]]
        blocos.append(current_block)
        return blocos

    def _calcular_entropia(self, jogo_ordenado: List[int]) -> float:
        """Calcula entropia."""
        if not jogo_ordenado:
            return 0.0
        counts = Counter(jogo_ordenado)
        probabilities = [count / len(jogo_ordenado) for count in counts.values()]
        entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)
        return entropy

    def _calcular_regularidade(self, diferencas: np.ndarray) -> float:
        """Calcula regularidade."""
        if len(diferencas) < 2:
            return 0.0
        return np.std(diferencas)

    def _verificar_norma(self, analise: Dict) -> Dict[str, bool]:
        """Verifica norma."""
        norma = {}
        for key, (min_val, max_val) in self.ESTATISTICAS_NORMAIS.items():
            if key == 'soma':
                norma[key] = min_val <= analise['basico'].get('soma', 0) <= max_val
            elif key == 'pares':
                norma[key] = min_val <= analise['basico'].get('pares', 0) <= max_val
            else:
                norma[key] = True
        return norma

    def _calcular_score_anomalia(self, analise: Dict) -> float:
        """Calcula score de anomalia."""
        desvios = self._calcular_desvios(analise)
        return sum(desvios.values()) / len(desvios) if desvios else 0.0

    def classificar(self, jogo: List[int], concurso: Optional[int] = None,
                    historico_recente: Optional[List[List[int]]] = None) -> Tuple[bool, EventType, EventoRaro]:
        """Classifica jogo."""
        analise = self.analisar_jogo(jogo, concurso)
        is_anomalo = self._calcular_score_anomalia(analise) > self.threshold_anomalia

        tipo_evento, metadados = EventType.NORMAL, {}
        if is_anomalo:
            tipo_evento, metadados = self._classificar_tipo_anomalia(analise, historico_recente)

        evento = EventoRaro(
            tipo=tipo_evento,
            concurso=concurso,
            jogo=jogo,
            metadados=metadados,
            probabilidade=self._calcular_probabilidade_evento(tipo_evento, analise),
            impacto=self.PADROES_RAROS.get(tipo_evento, {}).get('impacto', 0.0),
            precursor=self.detectar_precursor_salto(historico_recente) if historico_recente else False
        )

        if is_anomalo:
            self.historico_eventos.append(evento)
            self._salvar_historico()

        return is_anomalo, tipo_evento, evento

    def _identificar_posicao_bloco(self, blocos: List[List[int]]) -> str:
        """Identifica posição do bloco."""
        if not blocos:
            return 'nenhum'

        maior_bloco = max(blocos, key=len)
        if not maior_bloco:
            return 'nenhum'

        primeira_dezena = maior_bloco[0]
        ultima_dezena = maior_bloco[-1]

        if primeira_dezena <= 5:
            return 'inicial'
        elif ultima_dezena >= 21:
            return 'final'
        else:
            return 'centro'

    def _extrair_metadados(self, tipo: EventType, analise: Dict) -> Dict:
        """Extrai metadados."""
        metadados = {'tipo_anomalia': tipo.value}
        if tipo == EventType.SALTO_CLUSTERIZADO:
            metadados['soma'] = analise['basico']['soma']
            metadados['grupos_sequencia'] = analise['sequencias']['grupos_sequencia']
        elif tipo == EventType.BLOCO_MASSIVO:
            metadados['max_consecutivo'] = analise['sequencias']['max_consecutivo']
        return metadados

    def _calcular_densidade_espacial(self, jogo_ordenado: List[int]) -> float:
        """Calcula a densidade espacial do jogo."""
        if not jogo_ordenado:
            return 0.0

        diferencas = np.diff(jogo_ordenado)
        if len(diferencas) == 0:
            return 0.0

        media_diferencas = np.mean(diferencas)

        densidade = 1.0 - (media_diferencas - 1.0) / (2.5 - 1.0)
        return max(0.0, min(1.0, densidade))

    def _calcular_baseline_stats(self, historico_dezenas: List[List[int]]) -> Dict[str, Any]:
        """
        Calcula estatísticas de baseline (médias, desvios) a partir do histórico de dezenas.
        """
        if not historico_dezenas:
            return {}

        somas = []
        pares = []
        impares = []
        fibonacci_counts = []
        primos_counts = []
        multiplos_3_counts = []
        moldura_counts = []
        centro_counts = []
        grupos_sequencia_counts = []
        max_consecutivo_counts = []
        densidade_espacial_values = []

        for dezenas in historico_dezenas:
            jogo_ordenado = sorted(dezenas)

            somas.append(sum(jogo_ordenado))
            pares.append(sum(1 for d in jogo_ordenado if d % 2 == 0))
            impares.append(15 - pares[-1])

            fibonacci_counts.append(len([d for d in jogo_ordenado if d in [1, 2, 3, 5, 8, 13, 21]]))
            primos_counts.append(len([d for d in jogo_ordenado if d in [2, 3, 5, 7, 11, 13, 17, 19, 23]]))
            multiplos_3_counts.append(len([d for d in jogo_ordenado if d % 3 == 0]))

            moldura_counts.append(len([d for d in jogo_ordenado if d in [1,2,3,4,5, 6,10,11,15,16,20,21,22,23,24,25]]))
            centro_counts.append(len([d for d in jogo_ordenado if d in [7,8,9,12,13,14,17,18,19]]))

            grupos_seq, max_cons, _ = self._analisar_sequencias(jogo_ordenado)
            grupos_sequencia_counts.append(grupos_seq)
            max_consecutivo_counts.append(max_cons)

            densidade_espacial_values.append(self._calcular_densidade_espacial(jogo_ordenado))

        baseline = {
            'soma_media': np.mean(somas), 'soma_std': np.std(somas),
            'pares_media': np.mean(pares), 'pares_std': np.std(pares),
            'impares_media': np.mean(impares), 'impares_std': np.std(impares),
            'fibonacci_media': np.mean(fibonacci_counts), 'fibonacci_std': np.std(fibonacci_counts),
            'primos_media': np.mean(primos_counts), 'primos_std': np.std(primos_counts),
            'multiplos_3_media': np.mean(multiplos_3_counts), 'multiplos_3_std': np.std(multiplos_3_counts),
            'moldura_media': np.mean(moldura_counts), 'moldura_std': np.std(moldura_counts),
            'centro_media': np.mean(centro_counts), 'centro_std': np.std(centro_counts),
            'grupos_sequencia_media': np.mean(grupos_sequencia_counts), 'grupos_sequencia_std': np.std(grupos_sequencia_counts),
            'max_consecutivo_media': np.mean(max_consecutivo_counts), 'max_consecutivo_std': np.std(max_consecutivo_counts),
            'densidade_espacial_media': np.mean(densidade_espacial_values), 'densidade_espacial_std': np.std(densidade_espacial_values),
        }
        return baseline
