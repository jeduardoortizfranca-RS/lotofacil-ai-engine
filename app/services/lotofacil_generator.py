import random
from typing import List, Dict, Any, Set
from collections import Counter
from app.services.supabase_client import SupabaseClient

class LotofacilGenerator:
    def __init__(self, supabase_client: SupabaseClient):
        self.supabase_client = supabase_client
        self.dezenas_lotofacil = list(range(1, 26))

    async def gerar_jogos_ia(self, concurso_alvo: int, quantidade_jogos: int, concursos_base_analise: int) -> List[Dict[str, Any]]:
        print(f"🤖 Gerando {quantidade_jogos} jogos para o concurso {concurso_alvo} usando os últimos {concursos_base_analise} concursos como base.")

        pesos_ia = await self.supabase_client.get_pesos_ia_atuais()
        pesos = pesos_ia.get("pesos", {})
        print(f"🧠 Pesos da IA utilizados: {pesos}")

        ultimos_concursos = await self.supabase_client.get_ultimos_concursos(n=concursos_base_analise)
        if not ultimos_concursos:
            print("⚠️ Não há concursos históricos suficientes para análise. Gerando jogos aleatórios.")
            return self._gerar_jogos_aleatorios(quantidade_jogos)

        estatisticas = self._calcular_estatisticas_tendencias(ultimos_concursos)
        print(f"📊 Estatísticas calculadas: {estatisticas}")

        jogos_gerados = []
        for _ in range(quantidade_jogos):
            jogo = self._gerar_jogo_inteligente(pesos, estatisticas)
            score = self._calcular_score_jogo(jogo, pesos, estatisticas)
            # LINHA 30 CORRIGIDA AQUI:
            jogos_gerados.append({"dezenas": sorted(list(jogo)), "score_ia": score})

        print(f"✅ {len(jogos_gerados)} jogos gerados com sucesso pela IA.")
        return jogos_gerados

    def _gerar_jogos_aleatorios(self, quantidade: int) -> List[Dict[str, Any]]:
        jogos = []
        for _ in range(quantidade):
            dezenas = random.sample(self.dezenas_lotofacil, 15)
            jogos.append({"dezenas": sorted(dezenas), "score_ia": 0.0})
        return jogos

    def _calcular_estatisticas_tendencias(self, concursos: List[Dict[str, Any]]) -> Dict[str, Any]:
        estatisticas = {
            "frequencia_dezenas": Counter(),
            "dezenas_ausentes_recentes": set(),
            "somas": [],
            "pares": [],
            "repetidas_anterior": [],
            "duques_fortes": Counter()
        }

        todas_dezenas_sorteadas = []
        for concurso in concursos:
            dezenas = concurso.get("dezenas", [])
            if not dezenas:
                continue

            todas_dezenas_sorteadas.extend(dezenas)
            estatisticas["somas"].append(concurso.get("soma_dezenas", 0))
            estatisticas["pares"].append(concurso.get("pares", 0))
            estatisticas["repetidas_anterior"].append(concurso.get("repetidas_anterior", 0))

            for i in range(len(dezenas)):
                for j in range(i + 1, len(dezenas)):
                    par = tuple(sorted([dezenas[i], dezenas[j]]))
                    estatisticas["duques_fortes"][par] += 1

        estatisticas["frequencia_dezenas"] = Counter(todas_dezenas_sorteadas)

        dezenas_presentes_recentes = set(todas_dezenas_sorteadas)
        estatisticas["dezenas_ausentes_recentes"] = set(self.dezenas_lotofacil) - dezenas_presentes_recentes

        estatisticas["media_soma"] = sum(estatisticas["somas"]) / len(estatisticas["somas"]) if estatisticas["somas"] else 0
        estatisticas["media_pares"] = sum(estatisticas["pares"]) / len(estatisticas["pares"]) if estatisticas["pares"] else 0
        estatisticas["media_repetidas"] = sum(estatisticas["repetidas_anterior"]) / len(estatisticas["repetidas_anterior"]) if estatisticas["repetidas_anterior"] else 0

        estatisticas["top_duques"] = [par for par, freq in estatisticas["duques_fortes"].most_common(10)]

        return estatisticas

    def _gerar_jogo_inteligente(self, pesos: Dict[str, float], estatisticas: Dict[str, Any]) -> Set[int]:
        jogo = set()
        candidatas = list(self.dezenas_lotofacil)
        random.shuffle(candidatas)

        dezena_scores = {}
        for dezena in candidatas:
            score = 0.0
            score += estatisticas["frequencia_dezenas"].get(dezena, 0) * pesos.get("frequencia_10", 0)

            if dezena in estatisticas["dezenas_ausentes_recentes"]:
                score += pesos.get("ausentes", 0) * 5

            dezena_scores[dezena] = score

        dezenas_ordenadas = sorted(dezena_scores.items(), key=lambda item: item[1], reverse=True)

        while len(jogo) < 15:
            if not dezenas_ordenadas:
                dezena = random.choice(list(set(self.dezenas_lotofacil) - jogo))
                jogo.add(dezena)
                continue

            dezena_escolhida = dezenas_ordenadas.pop(0)[0]

            if dezena_escolhida not in jogo:
                jogo.add(dezena_escolhida)

        while len(jogo) < 15:
            dezena = random.choice(list(set(self.dezenas_lotofacil) - jogo))
            jogo.add(dezena)

        return jogo

    def _calcular_score_jogo(self, jogo: Set[int], pesos: Dict[str, float], estatisticas: Dict[str, Any]) -> float:
        score_total = 0.0

        num_impares = len([d for d in jogo if d % 2 != 0])
        num_pares = 15 - num_impares
        soma_dezenas = sum(jogo)

        frequencia_score = sum(estatisticas["frequencia_dezenas"].get(d, 0) for d in jogo)
        score_total += frequencia_score * pesos.get("frequencia_10", 0)

        ausentes_no_jogo = len([d for d in jogo if d in estatisticas["dezenas_ausentes_recentes"]])
        score_total += ausentes_no_jogo * pesos.get("ausentes", 0) * 5

        if 180 <= soma_dezenas <= 235:
            score_total += pesos.get("soma", 0) * 1.0
        elif 170 <= soma_dezenas < 180 or 235 < soma_dezenas <= 245:
            score_total += pesos.get("soma", 0) * 0.5

        if (num_pares == 7 and num_impares == 8) or (num_pares == 8 and num_impares == 7):
            score_total += pesos.get("pares", 0) * 1.0
        elif (num_pares == 6 and num_impares == 9) or (num_pares == 9 and num_impares == 6):
            score_total += pesos.get("pares", 0) * 0.5

        duques_no_jogo = 0
        dezenas_list = list(jogo)
        for i in range(len(dezenas_list)):
            for j in range(i + 1, len(dezenas_list)):
                par = tuple(sorted([dezenas_list[i], dezenas_list[j]]))
                if par in estatisticas["top_duques"]:
                    duques_no_jogo += 1
        score_total += duques_no_jogo * pesos.get("duques", 0) * 0.1

        return score_total
