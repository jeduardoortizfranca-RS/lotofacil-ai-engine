"""
Conferidor de jogos da Lotofácil
Calcula acertos, distribuição, custo, prêmio e lucro
"""

from typing import List, Dict, Any


class ConferidorJogos:
    def __init__(self, valor_aposta_por_jogo: float = 3.0, premios_estimados: Dict[int, float] = None):
        if premios_estimados is None:
            premios_estimados = {11: 6.0, 12: 12.0, 13: 30.0, 14: 2000.0, 15: 1800000.0}
        self.valor_aposta_por_jogo = valor_aposta_por_jogo
        self.premios_estimados = premios_estimados

    def conferir_jogos(self, resultado: List[int], jogos: List[List[int]]) -> Dict[str, Any]:
        resultado_set = set(resultado)
        acertos_por_jogo = [len(resultado_set.intersection(set(jogo))) for jogo in jogos]
        distribuicao = {"15": 0, "14": 0, "13": 0, "12": 0, "11": 0, "0-10": 0}
        premio_total = 0.0
        for acertos in acertos_por_jogo:
            if acertos >= 15:
                distribuicao["15"] += 1
                premio_total += self.premios_estimados.get(15, 0.0)
            elif acertos == 14:
                distribuicao["14"] += 1
                premio_total += self.premios_estimados.get(14, 0.0)
            elif acertos == 13:
                distribuicao["13"] += 1
                premio_total += self.premios_estimados.get(13, 0.0)
            elif acertos == 12:
                distribuicao["12"] += 1
                premio_total += self.premios_estimados.get(12, 0.0)
            elif acertos == 11:
                distribuicao["11"] += 1
                premio_total += self.premios_estimados.get(11, 0.0)
            else:
                distribuicao["0-10"] += 1
        total_gasto = len(jogos) * self.valor_aposta_por_jogo
        lucro = premio_total - total_gasto
        return {
            "acertos_por_jogo": acertos_por_jogo,
            "distribuicao_acertos": distribuicao,
            "total_gasto": round(total_gasto, 2),
            "premio_total": round(premio_total, 2),
            "lucro": round(lucro, 2),
        }
