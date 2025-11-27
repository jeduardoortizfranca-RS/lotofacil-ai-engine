"""
Endpoints para geração de jogos da Lotofácil
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

from app.services.supabase_client import SupabaseClient
from app.services.gerador_jogos import GeradorJogos

router = APIRouter(prefix="/jogos", tags=["Jogos"])


class GerarJogosRequest(BaseModel):
    concurso_alvo: int = Field(..., description="Número do concurso para o qual gerar jogos")
    quantidade: int = Field(30, ge=1, le=200, description="Quantidade de jogos a gerar (padrão: 30)")
    soma_min: int = Field(180, ge=150, le=250, description="Soma mínima das dezenas")
    soma_max: int = Field(235, ge=150, le=300, description="Soma máxima das dezenas")
    repetidas_min: int = Field(7, ge=0, le=15, description="Mínimo de repetidas do concurso anterior")
    repetidas_max: int = Field(12, ge=0, le=15, description="Máximo de repetidas do concurso anterior")
    pares_min: int = Field(6, ge=0, le=15, description="Mínimo de números pares")
    pares_max: int = Field(9, ge=0, le=15, description="Máximo de números pares")
    janela_historica: int = Field(10, ge=1, le=100, description="Janela de concursos históricos para análise")


class GerarJogosResponse(BaseModel):
    concurso_base: int
    concurso_alvo: int
    quantidade: int
    jogos: List[Dict[str, Any]]


@router.get("/ultimo")
async def obter_ultimo_concurso():
    """Retorna informações do último concurso cadastrado"""
    client = SupabaseClient()
    try:
        ultimo = await client.get_ultimo_concurso()
        if not ultimo:
            raise HTTPException(status_code=404, detail="Nenhum concurso encontrado no banco")
        return ultimo
    finally:
        await client.close()


@router.get("/estatisticas")
async def obter_estatisticas():
    """Retorna estatísticas gerais dos concursos (médias, percentis)"""
    client = SupabaseClient()
    try:
        stats = await client.get_estatisticas_gerais()
        return stats
    finally:
        await client.close()


@router.post("/gerar", response_model=GerarJogosResponse)
async def gerar_jogos(request: GerarJogosRequest):
    """
    Gera jogos para um concurso futuro baseado em análise histórica.
    Salva os jogos gerados na tabela jogos_gerados.
    """
    client = SupabaseClient()
    try:
        # 1. Buscar último concurso (base histórica)
        ultimo = await client.get_ultimo_concurso()
        if not ultimo:
            raise HTTPException(status_code=404, detail="Nenhum concurso histórico encontrado no banco")

        concurso_base = ultimo["numero"]
        dezenas_ultimo = ultimo["dezenas"]  # ← Extrair dezenas do último concurso

        # 2. Validação: não gerar jogos para concurso já existente
        concurso_alvo_existe = await client.get_concurso_por_numero(request.concurso_alvo)
        if concurso_alvo_existe:
            raise HTTPException(
                status_code=400,
                detail=f"Concurso {request.concurso_alvo} já existe no banco. Gere jogos para um concurso futuro (ex.: {concurso_base + 1})"
            )

        # 3. Buscar últimos N concursos para análise
        ultimos_concursos = await client.get_ultimos_concursos(n=request.janela_historica)

        # 4. Calcular ausentes (dezenas que não saíram nos últimos N concursos)
        todas_dezenas = set(range(1, 26))
        dezenas_saidas = set()
        for c in ultimos_concursos:
            dezenas_saidas.update(c["dezenas"])
        ausentes_ultimos = list(todas_dezenas - dezenas_saidas)

        # 5. Buscar duques fortes
        duques_fortes = await client.calcular_duques_fortes(ultimos_n=50)

        # 6. Buscar pesos atuais da IA
        pesos_ia = await client.get_pesos_ia_atuais()
        pesos = pesos_ia.get("pesos", {})

        # 7. Instanciar GeradorJogos com assinatura correta
        gerador = GeradorJogos(
            dezenas_ultimo=dezenas_ultimo,        # ← Parâmetro obrigatório
            ausentes_ultimos=ausentes_ultimos,    # ← Parâmetro obrigatório
            ultimos_concursos=ultimos_concursos,
            duques_fortes=duques_fortes,
            soma_min=request.soma_min,
            soma_max=request.soma_max,
            repetidas_min=request.repetidas_min,
            repetidas_max=request.repetidas_max,
            pares_min=request.pares_min,
            pares_max=request.pares_max,
            janela_historica=request.janela_historica
        )

        # 8. Gerar jogos
        jogos = gerador.gerar_jogos(quantidade=request.quantidade)

        # 9. Preparar parâmetros de geração (para auditoria)
        parametros_geracao = {
            "soma_min": request.soma_min,
            "soma_max": request.soma_max,
            "repetidas_min": request.repetidas_min,
            "repetidas_max": request.repetidas_max,
            "pares_min": request.pares_min,
            "pares_max": request.pares_max,
            "janela_historica": request.janela_historica,
            "versao_pesos_ia": pesos_ia.get("versao", 1)
        }

        # 10. Salvar no banco
        jogos_id = await client.salvar_jogos_gerados(
            concurso_base=concurso_base,
            concurso_alvo=request.concurso_alvo,
            parametros=parametros_geracao,
            jogos=jogos
        )

        print(f"✅ Jogos salvos com sucesso! ID do lote: {jogos_id}")
        print(f"   Concurso base: {concurso_base}, Concurso alvo: {request.concurso_alvo}")
        print(f"   Quantidade: {len(jogos)} jogos")

        return GerarJogosResponse(
            concurso_base=concurso_base,
            concurso_alvo=request.concurso_alvo,
            quantidade=len(jogos),
            jogos=jogos
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao gerar/salvar jogos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar jogos: {str(e)}")

    finally:
        await client.close()
