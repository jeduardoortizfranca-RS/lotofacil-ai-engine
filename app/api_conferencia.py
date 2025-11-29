# backend/app/api_conferencia.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

import os
import sys
from datetime import datetime, date # Importar date também

# Garante que possamos importar SupabaseClient do caminho correto
# Assumindo que supabase_client.py está na mesma pasta 'app' ou na raiz 'backend'
# Ajuste o sys.path para que o import funcione, dependendo da estrutura exata
# Se supabase_client.py estiver em backend/app/, o import direto funciona.
# Se estiver em backend/, precisa de um ajuste como:
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# from supabase_client import SupabaseClient
# Para a estrutura atual (supabase_client.py na raiz do backend), o import abaixo é o correto:
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from supabase_client import SupabaseClient

app = FastAPI(
    title="Lotofacil Conferência API",
    description="API conectada ao Supabase para gerar e conferir jogos",
    version="1.0.0",
)

supabase_client = SupabaseClient()


# ==========================
# MODELOS Pydantic
# ==========================

class GerarJogosRequest(BaseModel):
    concurso_alvo: int = Field(..., description="Número do concurso alvo (ainda não sorteado).")
    quantidade_jogos: int = Field(30, gt=0, description="Quantidade de jogos a gerar.")
    concursos_base_analise: int = Field(10, gt=0, description="Quantos concursos anteriores usar de base.")
    valor_aposta_por_jogo: float = Field(3.0, gt=0, description="Valor unitário da aposta.")


class GerarJogosResponse(BaseModel):
    concurso_alvo: int
    quantidade_jogos: int
    jogos: List[Dict[str, Any]]
    id_lote_jogos: str
    custo_total: float


class ConferirRequest(BaseModel):
    concurso: int = Field(..., description="Número do concurso já sorteado a conferir.")


class ConferirResponse(BaseModel):
    concurso: int
    dezenas_sorteadas: List[int]
    total_jogos: int
    distribuicao_acertos: Dict[str, int]
    total_gasto: float
    premio_total: float
    lucro: float
    id_lote_jogos: Optional[str]


# ==========================
# CICLO DE VIDA
# ==========================

@app.on_event("startup")
async def startup_event():
    await supabase_client.get_pool()


@app.on_event("shutdown")
async def shutdown_event():
    await supabase_client.close()


# ==========================
# ROTAS
# ==========================

@app.get("/")
async def root():
    return {
        "nome": "Lotofacil Conferência API",
        "status": "online",
        "rotas": [
            "POST /gerar-jogos",
            "POST /conferir",
        ],
    }


@app.post("/gerar-jogos", response_model=GerarJogosResponse)
async def gerar_jogos(request: GerarJogosRequest):
    """
    Gera jogos fictícios (placeholder) e salva em jogos_gerados no Supabase.
    Aqui não uso sua engine de IA, apenas gero combinações simples,
    porque o foco é provar o fluxo Supabase -> conferência.
    Depois podemos plugar sua IA.
    """
    try:
        # 1) Buscar concurso oficial (para ter um ID de concurso real)
        concurso_oficial = await supabase_client.get_concurso_por_numero(request.concurso_alvo)
        if not concurso_oficial:
            raise HTTPException(
                status_code=404,
                detail=f"Concurso {request.concurso_alvo} não encontrado no banco de dados para gerar jogos.",
            )

        # 2) Gerar jogos fictícios (substituir pela sua IA depois)
        jogos_gerados_list: List[Dict[str, Any]] = []
        for i in range(request.quantidade_jogos):
            # Exemplo simples: 15 dezenas aleatórias e ordenadas
            dezenas = sorted(list(set(os.urandom(15).hex() for _ in range(15))))[:15] # Gera 15 strings hex aleatórias
            dezenas_int = [int(d, 16) % 25 + 1 for d in dezenas] # Converte para int entre 1 e 25
            jogos_gerados_list.append({"jogo_id": i + 1, "dezenas": sorted(list(set(dezenas_int)))[:15]}) # Garante 15 únicas e ordenadas

        custo_total = request.quantidade_jogos * request.valor_aposta_por_jogo

        # 3) Salvar lote de jogos gerados
        id_lote_jogos = await supabase_client.salvar_jogos_gerados(
            concurso_alvo=request.concurso_alvo,
            quantidade_jogos=request.quantidade_jogos,
            parametros_geracao={
                "concursos_base_analise": request.concursos_base_analise,
                "valor_aposta_por_jogo": request.valor_aposta_por_jogo,
            },
            jogos=jogos_gerados_list,
            custo_total=custo_total,
        )

        if not id_lote_jogos:
            raise HTTPException(status_code=500, detail="Erro ao salvar jogos gerados no Supabase.")

        return GerarJogosResponse(
            concurso_alvo=request.concurso_alvo,
            quantidade_jogos=request.quantidade_jogos,
            jogos=jogos_gerados_list,
            id_lote_jogos=id_lote_jogos,
            custo_total=custo_total,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro inesperado ao gerar jogos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar jogos: {str(e)}")


@app.post("/conferir", response_model=ConferirResponse)
async def conferir_jogos(request: ConferirRequest):
    """
    Confere os jogos gerados para um concurso específico com o resultado oficial.
    Salva o resultado da conferência no Supabase.
    """
    try:
        # 1) Buscar resultado oficial do concurso
        concurso_oficial = await supabase_client.get_concurso_por_numero(request.concurso)
        if not concurso_oficial:
            raise HTTPException(
                status_code=404,
                detail=f"Concurso {request.concurso} não encontrado no banco de dados.",
            )

        dezenas_sorteadas = concurso_oficial["dezenas"]

        # 2) Lote de jogos gerados para esse concurso
        lote = await supabase_client.get_jogos_gerados_para_concurso(request.concurso)

        jogos_ia: List[Dict[str, Any]] = []
        id_lote_jogos: Optional[str] = None
        total_jogos = 0
        total_gasto = 0.0

        if lote:
            jogos_ia = lote["jogos"]
            id_lote_jogos = str(lote["id"])
            total_jogos = len(jogos_ia)
            total_gasto = float(lote["custo_total"]) if lote["custo_total"] is not None else 0.0
        else:
            print(f"⚠️ Nenhum lote de jogos gerados encontrado para o concurso {request.concurso}. A conferência será apenas do resultado oficial.")
            # Se não há jogos gerados, não podemos salvar a conferência no resultados_conferencia
            # pois 'jogos_gerados_id' é NOT NULL. Apenas retornamos a resposta da API.

        # 3) Conferência
        acertos_por_jogo: List[int] = []
        distribuicao_acertos = {"0-10": 0, "11": 0, "12": 0, "13": 0, "14": 0, "15": 0}
        premio_total = 0.0

        for jogo in jogos_ia:
            dezenas_jogo = set(jogo["dezenas"])
            acertos = len(dezenas_jogo.intersection(dezenas_sorteadas))
            acertos_por_jogo.append(acertos)

            if acertos >= 11:
                distribuicao_acertos[str(acertos)] += 1
            else:
                distribuicao_acertos["0-10"] += 1

            if acertos == 11:
                premio_total += 6.00
            elif acertos == 12:
                premio_total += 12.00
            elif acertos == 13:
                premio_total += 30.00
            elif acertos == 14:
                premio_total += 1500.00
            elif acertos == 15:
                premio_total += 1000000.00

        lucro = premio_total - total_gasto

        # Calcular o resumo da conferência
        resumo_conferencia = {
            "total_jogos": total_jogos,
            "total_acertos_11": distribuicao_acertos.get("11", 0),
            "total_acertos_12": distribuicao_acertos.get("12", 0),
            "total_acertos_13": distribuicao_acertos.get("13", 0),
            "total_acertos_14": distribuicao_acertos.get("14", 0),
            "total_acertos_15": distribuicao_acertos.get("15", 0),
            "total_gasto": total_gasto,
            "premio_total": premio_total,
            "lucro": lucro,
            "data_conferencia": datetime.now().isoformat()
        }


        # 4) Salvar resultado da conferência SOMENTE SE houver jogos gerados
        if id_lote_jogos: # Verifica se há um ID de lote de jogos
            salvo = await supabase_client.salvar_resultado_conferencia(
                numero_concurso=request.concurso,
                jogos_gerados_id=id_lote_jogos,
                resultado_oficial=concurso_oficial, # Passando o resultado oficial completo
                resumo=resumo_conferencia, # Passando o resumo da conferência
                total_jogos=total_jogos,
                acertos_por_jogo=acertos_por_jogo,
                distribuicao_acertos=distribuicao_acertos,
                total_gasto=total_gasto,
                premio_total=premio_total,
                lucro=lucro,
            )

            if salvo:
                await supabase_client.atualizar_status_conferencia(request.concurso, "conferido")
                print(f"✅ Conferência concluída e salva para concurso {request.concurso}")
                print(f"   Total de jogos: {total_jogos}")
                print(f"   Distribuição: {distribuicao_acertos}")
                print(f"   Lucro: R$ {lucro:.2f}")
            else:
                print(f"❌ Erro ao salvar resultado da conferência para concurso {request.concurso}")
        else:
            print("⚠️ Conferência não salva em resultados_conferencia pois não há jogos_gerados_id associado.")


        return ConferirResponse(
            concurso=request.concurso,
            dezenas_sorteadas=dezenas_sorteadas,
            total_jogos=total_jogos,
            distribuicao_acertos=distribuicao_acertos,
            total_gasto=total_gasto,
            premio_total=premio_total,
            lucro=lucro,
            id_lote_jogos=id_lote_jogos,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro inesperado ao conferir jogos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno ao conferir jogos: {str(e)}")
