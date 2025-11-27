"""
Gerador de jogos Lotofácil v1.1 - Bugfix

Critérios principais (baseados em insights do usuário):
1. Repetidas do último concurso (7-12, peso 0.25)
2. Ciclo/Ausentes (3-5 ausentes com potencial, peso 0.15)
3. Frequência nos últimos 10 (mix quente/frio/equilibrado, peso 0.20)
4. Soma (180-235, miolo 190-215, peso 0.15)
5. Pares/Ímpares (6-9 pares, peso 0.10)
6. Duques fortes (2-3 duques frequentes, peso 0.10)
7. Primos/Fibonacci/Múltiplos de 3 (distribuição saudável, peso 0.05)

Score total = soma ponderada (0-1). Jogos ranqueados pelos top 30.
"""

from typing import List, Dict, Any, Set, Tuple
import random
from collections import Counter


class GeradorJogos:
    def __init__(
        self,
        dezenas_ultimo: List[int],
        ausentes_ultimos: List[int],
        ultimos_concursos: List[Dict[str, Any]] = None,
        duques_fortes: List[Tuple[int, int, int]] = None,
        soma_min: int = 180,
        soma_max: int = 235,
        repetidas_min: int = 7,
        repetidas_max: int = 12,
        pares_min: int = 6,
        pares_max: int = 9,
        janela_historica: int = 10,
    ):
        self.dezenas_ultimo: Set[int] = set(dezenas_ultimo)
        self.ausentes_ultimos: Set[int] = set(ausentes_ultimos)
        self.ultimos_concursos = ultimos_concursos or []
        self.duques_fortes = duques_fortes or []

        self.SOMA_MIN = soma_min
        self.SOMA_MAX = soma_max
        self.SOMA_MIOLO_MIN = 190
        self.SOMA_MIOLO_MAX = 215

        self.REPETIDAS_MIN = repetidas_min
        self.REPETIDAS_MAX = repetidas_max

        self.PARES_MIN = pares_min
        self.PARES_MAX = pares_max

        self.TODAS_DEZENAS = list(range(1, 26))
        self.PARES = {d for d in self.TODAS_DEZENAS if d % 2 == 0}
        self.IMPARES = {d for d in self.TODAS_DEZENAS if d % 2 != 0}

        # Constantes para critérios secundários
        self.PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
        self.FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
        self.MULTIPLOS_3 = {3, 6, 9, 12, 15, 18, 21, 24}

        # Calcular frequência nos últimos N (quentes/frias)
        self.frequencia_dezenas = self._calcular_frequencia(ultimos_concursos)
        self.dezenas_quentes = self._classificar_quentes(self.frequencia_dezenas)
        self.dezenas_frias = self._classificar_frias(self.frequencia_dezenas)

    def _calcular_frequencia(self, ultimos: List[Dict[str, Any]]) -> Counter:
        """Calcula frequência de cada dezena nos últimos N concursos."""
        freq = Counter()
        for concurso in ultimos:
            for dezena in concurso["dezenas"]:
                freq[dezena] += 1
        return freq

    def _classificar_quentes(self, freq: Counter) -> Set[int]:
        """Classifica dezenas quentes (top 30% em frequência)."""
        if not freq:
            return set()
        # Top 8 dezenas mais frequentes (30% de 25)
        top_dezenas = [d for d, _ in freq.most_common(8)]
        return set(top_dezenas)

    def _classificar_frias(self, freq: Counter) -> Set[int]:
        """Classifica dezenas frias (bottom 30% em frequência)."""
        if not freq:
            return set()
        # Bottom 8 dezenas menos frequentes
        todas_ordenadas = sorted(freq.items(), key=lambda x: x[1])
        bottom_dezenas = [d for d, _ in todas_ordenadas[:8]]
        return set(bottom_dezenas)

    def gerar_jogo_candidato(self) -> List[int]:
        """Gera candidato com mix: repetidas + ausentes + frequência equilibrada."""
        q_repetidas = random.randint(self.REPETIDAS_MIN, self.REPETIDAS_MAX)
        q_novas = 15 - q_repetidas

        # 1. Repetidas do último
        repetidas_list = list(self.dezenas_ultimo)
        if len(repetidas_list) >= q_repetidas:
            repetidas = random.sample(repetidas_list, q_repetidas)
        else:
            repetidas = repetidas_list

        # 2. Novas: prioriza ausentes + equilíbrio quente/frio
        universo_novas = [d for d in self.TODAS_DEZENAS if d not in repetidas]
        ausentes_disp = [d for d in self.ausentes_ultimos if d in universo_novas]
        quentes_disp = [d for d in self.dezenas_quentes if d in universo_novas]
        frias_disp = [d for d in self.dezenas_frias if d in universo_novas]

        novas = []

        # 3-5 ausentes (se houver)
        q_ausentes = min(random.randint(3, 5), len(ausentes_disp), q_novas)
        if q_ausentes > 0:
            novas.extend(random.sample(ausentes_disp, q_ausentes))

        # Equilíbrio quente/frio para o resto
        faltam = q_novas - len(novas)
        if faltam > 0:
            # Tenta 1-2 quentes e 1-2 frias
            q_quentes = min(random.randint(1, 2), len(quentes_disp), faltam)
            q_frias = min(random.randint(1, 2), len(frias_disp), faltam - q_quentes)
            q_neutras = faltam - q_quentes - q_frias

            if q_quentes > 0:
                novas.extend(random.sample(quentes_disp, q_quentes))
            if q_frias > 0:
                novas.extend(random.sample(frias_disp, q_frias))

            # Neutras: dezenas que não são quentes nem frias
            if q_neutras > 0:
                neutras_disp = [
                    d for d in universo_novas 
                    if d not in novas 
                    and d not in self.dezenas_quentes 
                    and d not in self.dezenas_frias
                ]
                # BUGFIX: valida tamanho antes de sample
                q_neutras_real = min(q_neutras, len(neutras_disp))
                if q_neutras_real > 0:
                    novas.extend(random.sample(neutras_disp, q_neutras_real))

        jogo = repetidas + novas
        jogo = sorted(set(jogo))

        # Completa até 15 se necessário (fallback)
        while len(jogo) < 15:
            candidato = random.choice(self.TODAS_DEZENAS)
            if candidato not in jogo:
                jogo.append(candidato)

        return sorted(jogo[:15])

    def _calcular_score_repetidas(self, repetidas: int) -> float:
        """Score para repetidas (0-1, ideal 9-10)."""
        if self.REPETIDAS_MIN <= repetidas <= self.REPETIDAS_MAX:
            return 1.0 - abs(repetidas - 9.5) / (self.REPETIDAS_MAX - self.REPETIDAS_MIN)
        return 0.0

    def _calcular_score_ausentes(self, q_ausentes: int) -> float:
        """Score para ausentes (ideal 3-5)."""
        if 3 <= q_ausentes <= 5:
            return 1.0
        elif 2 <= q_ausentes <= 6:
            return 0.7
        return 0.0

    def _calcular_score_frequencia(self, jogo: List[int]) -> float:
        """Score para mix quente/frio (ideal: 3-5 frias, 2-4 quentes)."""
        q_frias = len(set(jogo) & self.dezenas_frias)
        q_quentes = len(set(jogo) & self.dezenas_quentes)
        if 3 <= q_frias <= 5 and 2 <= q_quentes <= 4:
            return 1.0
        elif 2 <= q_frias <= 6 and 1 <= q_quentes <= 5:
            return 0.8
        return 0.5

    def _calcular_score_soma(self, soma: int) -> float:
        """Score para soma (ideal miolo 190-215)."""
        if self.SOMA_MIN <= soma <= self.SOMA_MAX:
            if self.SOMA_MIOLO_MIN <= soma <= self.SOMA_MIOLO_MAX:
                return 1.0
            return 0.8
        return 0.0

    def _calcular_score_pares(self, pares: int) -> float:
        """Score para pares (ideal 6-9)."""
        if self.PARES_MIN <= pares <= self.PARES_MAX:
            return 1.0 - abs(pares - 7.5) / (self.PARES_MAX - self.PARES_MIN)
        return 0.0

    def _calcular_score_duques(self, jogo: List[int]) -> float:
        """Score para duques fortes (ideal 2-3)."""
        jogo_set = set(jogo)
        q_duques = sum(1 for d1, d2, _ in self.duques_fortes if d1 in jogo_set and d2 in jogo_set)
        if 2 <= q_duques <= 3:
            return 1.0
        elif 1 <= q_duques <= 4:
            return 0.7
        return 0.0

    def _calcular_score_secundarios(self, jogo: List[int]) -> float:
        """Score para primos/Fibonacci/múltiplos de 3 (ideal: 5-7 primos, 3-4 Fib, 4-6 mult3)."""
        q_primos = len(set(jogo) & self.PRIMOS)
        q_fib = len(set(jogo) & self.FIBONACCI)
        q_mult3 = len(set(jogo) & self.MULTIPLOS_3)

        score_primos = 1.0 if 5 <= q_primos <= 7 else 0.5 if 4 <= q_primos <= 8 else 0.0
        score_fib = 1.0 if 3 <= q_fib <= 4 else 0.5 if 2 <= q_fib <= 5 else 0.0
        score_mult3 = 1.0 if 4 <= q_mult3 <= 6 else 0.5 if 3 <= q_mult3 <= 7 else 0.0

        return (score_primos + score_fib + score_mult3) / 3

    def avaliar_jogo(self, jogo: List[int]) -> Dict[str, Any]:
        """Avalia jogo com score ponderado expandido."""
        soma = sum(jogo)
        repetidas = len(set(jogo) & self.dezenas_ultimo)
        pares = len([d for d in jogo if d % 2 == 0])
        impares = 15 - pares
        q_ausentes = len(set(jogo) & self.ausentes_ultimos)

        # Moldura (mantida para compatibilidade)
        moldura_set = {1, 2, 3, 4, 5, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
        moldura = len([d for d in jogo if d in moldura_set])
        centro = 15 - moldura

        # Scores individuais (0-1)
        s_repetidas = self._calcular_score_repetidas(repetidas)
        s_ausentes = self._calcular_score_ausentes(q_ausentes)
        s_frequencia = self._calcular_score_frequencia(jogo)
        s_soma = self._calcular_score_soma(soma)
        s_pares = self._calcular_score_pares(pares)
        s_duques = self._calcular_score_duques(jogo)
        s_secundarios = self._calcular_score_secundarios(jogo)

        # Score total ponderado
        score_total = (
            0.25 * s_repetidas +
            0.15 * s_ausentes +
            0.20 * s_frequencia +
            0.15 * s_soma +
            0.10 * s_pares +
            0.10 * s_duques +
            0.05 * s_secundarios
        )

        # Breakdown para resposta
        breakdown = {
            "repetidas": round(s_repetidas, 2),
            "ausentes": round(s_ausentes, 2),
            "frequencia_10": round(s_frequencia, 2),
            "soma": round(s_soma, 2),
            "pares": round(s_pares, 2),
            "duques": round(s_duques, 2),
            "primos_fib_mult3": round(s_secundarios, 2)
        }

        return {
            "jogo": jogo,
            "soma": soma,
            "repetidas": repetidas,
            "pares": pares,
            "impares": impares,
            "moldura": moldura,
            "centro": centro,
            "q_ausentes": q_ausentes,
            "score_total": round(score_total, 2),
            "breakdown_score": breakdown,
        }

    def gerar_jogos(self, quantidade: int = 30, max_tentativas: int = 10000) -> List[Dict[str, Any]]:
        """Gera quantidade jogos (default 30), ranqueados por score_total."""
        candidatos: List[Dict[str, Any]] = []

        tentativas = 0
        while tentativas < max_tentativas and len(candidatos) < quantidade * 2:
            tentativas += 1
            jogo = self.gerar_jogo_candidato()
            aval = self.avaliar_jogo(jogo)

            # Filtra só jogos com score_total >= 0.70 (qualidade mínima)
            if aval["score_total"] >= 0.70:
                candidatos.append(aval)

        # Ranqueia: score_total desc, soma próxima de 202.5 (centro miolo)
        alvo_soma = (self.SOMA_MIOLO_MIN + self.SOMA_MIOLO_MAX) / 2
        candidatos.sort(key=lambda x: (-x["score_total"], abs(x["soma"] - alvo_soma)))

        return candidatos[:quantidade]
