"""
Endpoint para conferência de jogos gerados contra resultado oficial
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import json
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

from app.services.supabase_client import SupabaseClient

router = APIRouter(prefix="", tags=["Conferência"])


class ConferirRequest(BaseModel):
    concurso: int = Field(..., description="Número do concurso a conferir")
    valor_aposta_por_jogo: float = Field(3.0, description="Valor da aposta por jogo (padrão: R$ 3,00)")


class ConferirResponse(BaseModel):
    concurso: int
    resultado_oficial: List[int]
    total_jogos: int
    acertos_por_jogo: List[int]
    distribuicao_acertos: Dict[str, int]
    total_gasto: float
    premio_total: float
    lucro: float
    concurso_base: int
    data_geracao: str


@router.post("/conferir", response_model=ConferirResponse)
async def conferir_jogos(request: ConferirRequest):
    """
    Confere jogos gerados para um concurso contra o resultado oficial.
    Calcula acertos, prêmios e lucro.
    """
    client = SupabaseClient()
    try:
        # 1. Buscar resultado oficial do concurso
        concurso_oficial = await client.get_concurso_por_numero(request.concurso)
        if not concurso_oficial:
            raise HTTPException(
                status_code=404,
                detail=f"Concurso {request.concurso} não encontrado (ainda não sorteado ou não cadastrado)"
            )

        resultado_oficial = set(concurso_oficial["dezenas"])

        # 2. Buscar jogos gerados para este concurso
        jogos_reg = await client.get_jogos_gerados_para_concurso(concurso_alvo=request.concurso)
        if not jogos_reg:
            raise HTTPException(
                status_code=404,
                detail=f"Não existem jogos gerados para o concurso {request.concurso}. Gere jogos primeiro com POST /jogos/gerar"
            )

        # 3. ← CORREÇÃO: Parse JSON se vier como string
        jogos_data = jogos_reg["jogos"]
        if isinstance(jogos_data, str):
            try:
                jogos_list_raw = json.loads(jogos_data)
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Erro ao parsear JSON dos jogos: {e}"
                )
        else:
            jogos_list_raw = jogos_data

        # Extrair apenas as dezenas de cada jogo
        jogos_list = [j["jogo"] for j in jogos_list_raw]

        # 4. Conferir cada jogo
        acertos_por_jogo = []
        for jogo in jogos_list:
            acertos = len(set(jogo) & resultado_oficial)
            acertos_por_jogo.append(acertos)

        # 5. Calcular distribuição de acertos
        distribuicao = {
            "15": acertos_por_jogo.count(15),
            "14": acertos_por_jogo.count(14),
            "13": acertos_por_jogo.count(13),
            "12": acertos_por_jogo.count(12),
            "11": acertos_por_jogo.count(11),
            "0-10": sum(1 for a in acertos_por_jogo if a <= 10)
        }

        # 6. Calcular prêmios (tabela Lotofácil simplificada)
        tabela_premios = {
            15: 1900000.0,  # Prêmio médio 15 acertos
            14: 1200.0,     # Prêmio médio 14 acertos
            13: 30.0,       # Prêmio médio 13 acertos
            12: 12.0,       # Prêmio médio 12 acertos
            11: 6.0         # Prêmio médio 11 acertos
        }

        premio_total = sum(
            tabela_premios.get(acertos, 0.0) 
            for acertos in acertos_por_jogo
        )

        total_gasto = len(jogos_list) * request.valor_aposta_por_jogo
        lucro = premio_total - total_gasto

        # 7. Salvar resultado da conferência
        await client.salvar_resultado_conferencia(
            numero_concurso=request.concurso,
            total_jogos=len(jogos_list),
            acertos_por_jogo=acertos_por_jogo,
            distribuicao_acertos=distribuicao,
            total_gasto=total_gasto,
            premio_total=premio_total,
            lucro=lucro
        )

        # 8. Atualizar status do lote de jogos para 'conferido'
        await client.atualizar_status_conferencia(
            concurso_alvo=request.concurso,
            status="conferido"
        )

        print(f"✅ Conferência concluída para concurso {request.concurso}")
        print(f"   Total de jogos: {len(jogos_list)}")
        print(f"   Distribuição: 15pts={distribuicao['15']}, 14pts={distribuicao['14']}, 13pts={distribuicao['13']}, 12pts={distribuicao['12']}, 11pts={distribuicao['11']}")
        print(f"   Lucro: R$ {lucro:.2f}")

        return ConferirResponse(
            concurso=request.concurso,
            resultado_oficial=sorted(list(resultado_oficial)),
            total_jogos=len(jogos_list),
            acertos_por_jogo=acertos_por_jogo,
            distribuicao_acertos=distribuicao,
            total_gasto=total_gasto,
            premio_total=premio_total,
            lucro=lucro,
            concurso_base=jogos_reg["concurso_base"],
            data_geracao=jogos_reg["data_geracao"].isoformat() if jogos_reg.get("data_geracao") else ""
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao conferir jogos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno ao conferir jogos: {str(e)}")

    finally:
        await client.close()
