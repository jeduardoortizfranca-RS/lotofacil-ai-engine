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
        window_analise: int = 5
    ):
        """
        Inicializa o detector de eventos
        
        Args:
            historico_file: Arquivo para persistir eventos raros
            threshold_anomalia: Limite para classificar como anômalo (percentil)
            min_ocorrencias: Mínimo de ocorrências para detectar padrão
            window_analise: Janela de concursos para análise de precursores
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
                    'dezenas_frias': (5, 8),  # CORRIGIDO: era 'deas_frias'
                    'atraso_medio': (15, 25),
                    'regiao_fria': ['inicial', 'final']
                },
                'probabilidade_base': 0.018,
                'impacto': 0.20  # Pode ser positivo
            }
        }
        
        # Histórico de eventos
        self.historico_eventos = self._carregar_historico()
        self.padroes_detectados = defaultdict(list)
        self.precursores_mapeados = defaultdict(list)
        
        # Métricas de baseline (calculadas dinamicamente)
        self.baseline_stats = {}
        
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
        desvios['soma'] = abs(basico['soma'] - 205) / 30.0  # Desvio da média ~205
        desvios['pares'] = abs(basico['pares'] - 7.5) / 1.5  # Desvio da média ~7.5 (CORRIGIDO)
        desvios['fibonacci'] = abs(basico['fibonacci'] - 4) / 1.0
        desvios['primos'] = abs(basico['primos'] - 5.5) / 1.5
        desvios['multiplos_3'] = abs(basico['multiplos_3'] - 5) / 1.0
        desvios['moldura'] = abs(basico['moldura'] - 11) / 1.0
        desvios['grupos_sequencia'] = abs(sequencias['grupos_sequencia'] - 5.5) / 1.5
        desvios['max_consecutivo'] = abs(sequencias['max_consecutivo'] - 3) / 2.0
        desvios['densidade_espacial'] = abs(espacial['densidade_espacial'] - 0.5) / 0.2
        
        return desvios
    
    def _classificar_tipo_anomalia(self, analise: Dict, 
                                   historico_recente: Optional[List[List[int]]] = None) -> Tuple[EventType, Dict]:
        """Classifica o tipo específico de anomalia"""
        basico = analise['basico']  # CORRIGIDO: era 'ico'
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
                           analise: Dict) -> bool:  # CORRIGIDO: era 'anal'
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
                    if 'saltos_medio' not in sequencias['saltos'] or not (valor[0] <= sequencias['saltos']['saltos_medio'] <= valor[1]):
                        return False
                elif criterio == 'max_consecutivo':
                    if not (valor[0] <= sequencias['max_consecutivo'] <= valor[1]):
                        return False
                elif criterio == 'dezenas_frias':
                    # Implementar lógica de dezenas frias
                    continue
            elif isinstance(valor, list):
                # Lista de valores aceitáveis
                if criterio == 'posicao_bloco':
                    blocos = sequencias['blocos']
                    posicoes = ['inicial', 'centro', 'final']
                    if not any(pos in valor for pos in posicoes if self._identificar_posicao_bloco(blocos)):
                        return False
                elif criterio == 'soma':
                    # CORRIGIDO: verificação de soma em lista de intervalos
                    soma_atual = basico['soma']
                    if not any(intervalo[0] <= soma_atual <= intervalo[1] for intervalo in valor):
                        return False
            elif isinstance(valor, bool):
                # Critério booleano
                if criterio == 'mudanca_paridade':
                    # Implementar verificação de mudança de paridade
                    continue
                elif criterio == 'mudanca_soma':
                    # Implementar verificação de mudança de soma
                    continue
        
        return True
    
    def _calcular_percentil_soma(self, soma: int) -> float:
        """Calcula percentil da soma baseado no histórico"""
        # Implementação simplificada
        # Percentil baseado em distribuição normal (média=205, desvio=30)
        z_score = (soma - 205) / 30.0
        
        # Aproximação do percentil usando z-score
        if z_score < -3:
            return 0.001
        elif z_score > 3:
            return 0.999
        else:
            # Aproximação linear simples
            percentil = 0.5 + (z_score / 6.0)
            return max(0.0, min(1.0, percentil))
    
    def _jogos_similares(self, jogo1: Optional[List[int]], jogo2: Dict) -> bool:
        """Verifica se dois jogos são similares"""
        if jogo1 is None:
            return False
        
        # Comparar métricas básicas
        soma1 = sum(jogo1)
        soma2 = jogo2.get('soma', 0)
        
        # Considerar similar se soma difere menos de 10%
        diff_soma = abs(soma1 - soma2) / soma1 if soma1 > 0 else 1.0
        
        return diff_soma < 0.1
    
    def _calcular_probabilidade_evento(self, tipo: EventType, 
                                      analise: Dict) -> float:
        """Calcula probabilidade específica do evento baseado no histórico"""
        if tipo == EventType.NORMAL:
            return 1.0
        
        base_prob = self.PADROES_RAROS[tipo]['probabilidade_base']
        
        # Ajustar baseado no histórico
        eventos_similares = sum(1 for e in self.historico_eventos 
                               if e.tipo == tipo and self._jogos_similares(e.jogo, analise['basico']))
        
        if eventos_similares >= self.min_ocorrencias:
            # Padrão recorrente - aumentar probabilidade
            ajuste_historico = min(0.3, eventos_similares * 0.05)
            base_prob += ajuste_historico
        
        # Ajustar baseado na intensidade da anomalia
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
        
        # Analisar últimos 3 jogos
        jogos_recentes = historico_recente[-3:]
        
        count = 0
        for jogo in jogos_recentes:
            analise = self.analisar_jogo(jogo)
            
            # Verificar critérios de precursor
            if (analise['basico']['soma'] > 180 and 
                analise['sequencias']['max_consecutivo'] >= 4 and 
                3 <= analise['sequencias']['grupos_sequencia'] <= 4):
                count += 1
        
        # Se 3/3 jogos atenderem, dispara alerta
        return count >= 3
    
    # Métodos auxiliares necessários (stubs para completar depois)
    def analisar_jogo(self, jogo: List[int], concurso: Optional[int] = None) -> Dict[str, Any]:
        """Análise completa do jogo (implementação completa já fornecida anteriormente)"""
        # Implementação completa já está no código original
        pass
    
    def _analisar_sequencias(self, jogo_ordenado: List[int]) -> Tuple[int, int, Dict]:
        """Análise de sequências (implementação completa já fornecida anteriormente)"""
        pass
    
    def _dividir_em_blocos(self, jogo_ordenado: List[int]) -> List[List[int]]:
        """Divide em blocos (implementação completa já fornecida anteriormente)"""
        pass
    
    def _calcular_entropia(self, jogo_ordenado: List[int]) -> float:
        """Calcula entropia (implementação completa já fornecida anteriormente)"""
        pass
    
    def _calcular_regularidade(self, diferencas: np.ndarray) -> float:
        """Calcula regularidade (implementação completa já fornecida anteriormente)"""
        pass
    
    def _verificar_norma(self, analise: Dict) -> Dict[str, bool]:
        """Verifica norma (implementação completa já fornecida anteriormente)"""
        pass
    
    def _calcular_score_anomalia(self, analise: Dict) -> float:
        """Calcula score de anomalia (implementação completa já fornecida anteriormente)"""
        pass
    
    def classificar(self, jogo: List[int], concurso: Optional[int] = None,
                   historico_recente: Optional[List[List[int]]] = None) -> Tuple[bool, EventType, EventoRaro]:
        """Classifica jogo (implementação completa já fornecida anteriormente)"""
        pass
    
    def _identificar_posicao_bloco(self, blocos: List[List[int]]) -> str:
        """Identifica posição do bloco (implementação completa já fornecida anteriormente)"""
        pass
    
    def _extrair_metadados(self, tipo: EventType, analise: Dict) -> Dict:
        """Extrai metadados (implementação completa já fornecida anteriormente)"""
        pass
