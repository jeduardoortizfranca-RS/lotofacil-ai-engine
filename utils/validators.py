"""
Validadores de jogos da Lotofácil
Autor: Inner AI + Jose Eduardo França
Data: Novembro 2025
"""

import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class GameValidator:
    """
    Validador completo de jogos da Lotofácil
    
    Verifica:
    - Estrutura básica (15 dezenas únicas entre 1-25)
    - Soma total
    - Distribuição par/ímpar
    - Números primos
    - Sequência Fibonacci
    - Múltiplos de 3
    - Moldura (bordas do volante)
    - Centro (meio do volante)
    - Números consecutivos
    """
    
    def __init__(self):
        """Inicializa validador com conjuntos de referência"""
        self.primos = {2, 3, 5, 7, 11, 13, 17, 19, 23}
        self.fibonacci = {1, 2, 3, 5, 8, 13, 21}
        self.moldura = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
        self.centro = {7, 8, 9, 12, 13, 14, 17, 18, 19}
        
        logger.info("✅ Validador de Jogos inicializado")
    
    def validar_completo(
        self, 
        jogo: List[int], 
        constraints: Optional[Dict] = None
    ) -> Tuple[bool, Dict]:
        """
        Valida jogo contra todas as restrições
        
        Args:
            jogo: Lista de 15 dezenas
            constraints: Dicionário de restrições (opcional)
                {
                    'soma': (min, max),
                    'pares': (min, max),
                    'primos': (min, max),
                    'fibonacci': (min, max),
                    'multiplos_3': (min, max),
                    'moldura': (min, max),
                    'centro': (min, max),
                    'max_consecutivo': int
                }
        
        Returns:
            (valido: bool, validacao: Dict)
        """
        # Validações estruturais básicas
        if len(jogo) != 15:
            return False, {
                'valido': False,
                'erro': f'Jogo deve ter 15 dezenas (tem {len(jogo)})'
            }
        
        if len(set(jogo)) != 15:
            return False, {
                'valido': False,
                'erro': 'Jogo contém dezenas repetidas'
            }
        
        if not all(1 <= n <= 25 for n in jogo):
            return False, {
                'valido': False,
                'erro': 'Dezenas devem estar entre 1 e 25'
            }
        
        # Calcular métricas do jogo
        jogo_sorted = sorted(jogo)
        
        soma = sum(jogo)
        pares = sum(1 for n in jogo if n % 2 == 0)
        impares = 15 - pares
        primos = sum(1 for n in jogo if n in self.primos)
        fib = sum(1 for n in jogo if n in self.fibonacci)
        mult_3 = sum(1 for n in jogo if n % 3 == 0)
        moldura = sum(1 for n in jogo if n in self.moldura)
        centro = sum(1 for n in jogo if n in self.centro)
        
        # Calcular sequências consecutivas
        max_consecutivo = self._calcular_max_consecutivo(jogo_sorted)
        
        # Montar dicionário de validação
        validacao = {
            'valido': True,
            'soma': soma,
            'pares': pares,
            'impares': impares,
            'primos': primos,
            'fibonacci': fib,
            'multiplos_3': mult_3,
            'moldura': moldura,
            'centro': centro,
            'max_consecutivo': max_consecutivo
        }
        
        # Se não há constraints, retornar válido
        if not constraints:
            return True, validacao
        
        # Validar contra constraints
        if 'soma' in constraints:
            min_soma, max_soma = constraints['soma']
            if not (min_soma <= soma <= max_soma):
                validacao['valido'] = False
                validacao['erro'] = f'Soma {soma} fora do intervalo [{min_soma}, {max_soma}]'
                return False, validacao
        
        if 'pares' in constraints:
            min_pares, max_pares = constraints['pares']
            if not (min_pares <= pares <= max_pares):
                validacao['valido'] = False
                validacao['erro'] = f'Pares {pares} fora do intervalo [{min_pares}, {max_pares}]'
                return False, validacao
        
        if 'primos' in constraints:
            min_primos, max_primos = constraints['primos']
            if not (min_primos <= primos <= max_primos):
                validacao['valido'] = False
                validacao['erro'] = f'Primos {primos} fora do intervalo [{min_primos}, {max_primos}]'
                return False, validacao
        
        if 'fibonacci' in constraints:
            min_fib, max_fib = constraints['fibonacci']
            if not (min_fib <= fib <= max_fib):
                validacao['valido'] = False
                validacao['erro'] = f'Fibonacci {fib} fora do intervalo [{min_fib}, {max_fib}]'
                return False, validacao
        
        if 'multiplos_3' in constraints:
            min_mult, max_mult = constraints['multiplos_3']
            if not (min_mult <= mult_3 <= max_mult):
                validacao['valido'] = False
                validacao['erro'] = f'Múltiplos de 3: {mult_3} fora do intervalo [{min_mult}, {max_mult}]'
                return False, validacao
        
        if 'moldura' in constraints:
            min_mold, max_mold = constraints['moldura']
            if not (min_mold <= moldura <= max_mold):
                validacao['valido'] = False
                validacao['erro'] = f'Moldura {moldura} fora do intervalo [{min_mold}, {max_mold}]'
                return False, validacao
        
        if 'centro' in constraints:
            min_centro, max_centro = constraints['centro']
            if not (min_centro <= centro <= max_centro):
                validacao['valido'] = False
                validacao['erro'] = f'Centro {centro} fora do intervalo [{min_centro}, {max_centro}]'
                return False, validacao
        
        if 'max_consecutivo' in constraints:
            max_consec_permitido = constraints['max_consecutivo']
            if max_consecutivo > max_consec_permitido:
                validacao['valido'] = False
                validacao['erro'] = f'Consecutivos {max_consecutivo} > limite {max_consec_permitido}'
                return False, validacao
        
        # Todas as validações passaram
        return True, validacao
    
    def _calcular_max_consecutivo(self, jogo_sorted: List[int]) -> int:
        """
        Calcula a maior sequência de números consecutivos
        
        Args:
            jogo_sorted: Lista ordenada de dezenas
        
        Returns:
            Tamanho da maior sequência consecutiva
        """
        if not jogo_sorted:
            return 0
        
        max_seq = 1
        seq_atual = 1
        
        for i in range(1, len(jogo_sorted)):
            if jogo_sorted[i] == jogo_sorted[i-1] + 1:
                seq_atual += 1
                max_seq = max(max_seq, seq_atual)
            else:
                seq_atual = 1
        
        return max_seq
    
    def validar_basico(self, jogo: List[int]) -> bool:
        """
        Validação rápida (apenas estrutura)
        
        Args:
            jogo: Lista de dezenas
        
        Returns:
            True se válido estruturalmente
        """
        return (
            len(jogo) == 15 and
            len(set(jogo)) == 15 and
            all(1 <= n <= 25 for n in jogo)
        )
    
    def calcular_score_qualidade(self, jogo: List[int]) -> float:
        """
        Calcula score de qualidade do jogo (0.0 a 1.0)
        
        Baseado em:
        - Soma próxima da média (195)
        - Distribuição equilibrada par/ímpar
        - Presença de primos, fibonacci
        - Não ter muitos consecutivos
        
        Args:
            jogo: Lista de dezenas
        
        Returns:
            Score de qualidade (0.0 a 1.0)
        """
        if not self.validar_basico(jogo):
            return 0.0
        
        score = 0.0
        
        # Soma próxima de 195 (média ideal)
        soma = sum(jogo)
        desvio_soma = abs(soma - 195)
        if desvio_soma <= 20:
            score += 0.25
        elif desvio_soma <= 40:
            score += 0.15
        
        # Pares equilibrados (6-9)
        pares = sum(1 for n in jogo if n % 2 == 0)
        if 6 <= pares <= 9:
            score += 0.25
        elif 5 <= pares <= 10:
            score += 0.15
        
        # Primos (4-7)
        primos = sum(1 for n in jogo if n in self.primos)
        if 4 <= primos <= 7:
            score += 0.25
        elif 3 <= primos <= 8:
            score += 0.15
        
        # Fibonacci (3-5)
        fib = sum(1 for n in jogo if n in self.fibonacci)
        if 3 <= fib <= 5:
            score += 0.25
        elif 2 <= fib <= 6:
            score += 0.15
        
        return min(score, 1.0)
    
    def comparar_com_historico(
        self, 
        jogo: List[int], 
        historico: List[List[int]]
    ) -> Dict:
        """
        Compara jogo com histórico de resultados
        
        Args:
            jogo: Jogo a validar
            historico: Lista de resultados anteriores
        
        Returns:
            Dicionário com análise comparativa
        """
        if not historico:
            return {
                'recorrencia': 0.0,
                'novidade': 1.0,
                'similaridade_media': 0.0
            }
        
        jogo_set = set(jogo)
        
        # Calcular recorrência (quantas dezenas já saíram recentemente)
        ultimos_5 = historico[-5:] if len(historico) >= 5 else historico
        dezenas_recentes = set()
        for resultado in ultimos_5:
            dezenas_recentes.update(resultado)
        
        recorrencia = len(jogo_set & dezenas_recentes) / 15
        
        # Calcular similaridade média
        similaridades = []
        for resultado in ultimos_5:
            resultado_set = set(resultado)
            similaridade = len(jogo_set & resultado_set) / 15
            similaridades.append(similaridade)
        
        similaridade_media = sum(similaridades) / len(similaridades) if similaridades else 0.0
        
        return {
            'recorrencia': recorrencia,
            'novidade': 1.0 - recorrencia,
            'similaridade_media': similaridade_media,
            'dezenas_recorrentes': len(jogo_set & dezenas_recentes)
        }
