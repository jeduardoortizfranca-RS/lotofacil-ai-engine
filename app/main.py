from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import sys

# Garantir que o diretório 'backend' esteja no sys.path para importações como 'core' e 'app.services'
# O caminho do backend é o diretório pai do diretório atual (app)
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.abspath(os.path.join(current_dir, "..")) # Sobe um nível para chegar em 'backend'
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Importações corrigidas com base na estrutura da documentação e imagens
from core.lotofacil_ai_v3 import LotofacilAIv3 # Motor IA está em backend/core/lotofacil_ai_v3.py
from app.services.supabase_client import SupabaseClient # SupabaseClient está em backend/app/services/supabase_client.py

app = FastAPI(
    title="Lotofácil AI API",
    description="API para gerar e conferir jogos da Lotofácil com inteligência artificial.",
    version="3.0.0",
)

supabase_client = SupabaseClient()
# Instanciar o motor de IA globalmente ou em um gerenciador de dependências,
# mas para simplificar e seguir o fluxo, vamos instanciar aqui.
# O LotofacilAIv3 não deve precisar de concursos_base ou pesos_ia no seu __init__
# se ele os recebe nos métodos de geração.
# Se o __init__ do LotofacilAIv3 realmente precisar de argumentos,
# precisaremos ajustar aqui ou criar um wrapper.
# Pela descrição do erro anterior, a LotofacilGenerator era o problema.
# Vamos assumir que LotofacilAIv3 pode ser instanciado sem argumentos iniciais complexos,
# e que os dados de base e pesos são passados para o método de geração.
lotofacil_engine = LotofacilAIv3(
    modo_offline=True,
    mazusoft_data_path=os.path.join(backend_path, "data", "mazusoft_data.json"), # Caminho ajustado
) # Assumindo que o construtor não precisa de argumentos iniciais complexos.

# ==========================
# MODELOS Pydantic
# ==========================
class GerarJogosRequest(BaseModel):
    concurso_alvo: int = Field(..., description="Número do concurso para o qual os jogos serão gerados.")
    quantidade_jogos: int = Field(30, gt=0, description="Quantidade de jogos a serem gerados.")
    concursos_base_analise: int = Field(10, gt=0, description="Quantidade de concursos anteriores usados na análise.")
    valor_aposta_por_jogo: float = Field(3.0, gt=0, description="Valor da aposta por jogo (para cálculo do custo).")

class GerarJogosResponse(BaseModel):
    concurso_alvo: int
    quantidade_jogos: int
    jogos: List[List[int]] # Ajustado para List[List[int]] conforme a saída do motor
    id_lote_jogos: str
    custo_total: float

class ConferirRequest(BaseModel):
    concurso: int = Field(..., description="Número do concurso a ser conferido.")
    valor_aposta_por_jogo: float = Field(3.0, gt=0, description="Valor da aposta por jogo (para cálculo de custo e lucro).")

class ConferirResponse(BaseModel):
    concurso: int
    dezenas_sorteadas: List[int]
    jogos_gerados: Optional[List[Dict[str, Any]]]
    total_jogos: int
    distribuicao_acertos: Dict[str, int]
    total_gasto: float
    premio_total: float
    lucro: float
    id_lote_jogos: Optional[str]

# ==========================
# EVENTOS DE CICLO DE VIDA
# ==========================
@app.on_event("startup")
async def startup_event():
    await supabase_client.get_pool()

@app.on_event("shutdown")
async def shutdown_event():
    await supabase_client.close()

# ==========================
# ENDPOINT: GERAR JOGOS
# ==========================
@app.post("/gerar-jogos", response_model=GerarJogosResponse)
async def gerar_jogos(request: GerarJogosRequest):
    """
    Gera jogos da Lotofácil utilizando a IA e salva no banco.
    """
    print(
        f"🤖 Gerando {request.quantidade_jogos} jogos para o concurso {request.concurso_alvo} "
        f"usando os últimos {request.concursos_base_analise} concursos como base."
    )
    try:
        # 1) Pesos da IA
        # Para a API Offline, podemos usar os pesos padrão ou buscar do Supabase se necessário.
        # Se a intenção é que esta API seja puramente offline, os pesos podem ser definidos aqui.
        # Pela documentação, a API Offline usa o motor com arquivos Mazusoft (offline).
        # Vamos buscar os pesos do Supabase para manter a consistência, mas o motor pode ter seus próprios.
        pesos_ia_data = await supabase_client.get_pesos_ia_atuais()
        if not pesos_ia_data:
            # Se não conseguir do Supabase, usa um padrão interno para a API Offline
            pesos_ia = {
                "repetidas": 0.25, "ausentes": 0.15, "frequencia_10": 0.20,
                "soma": 0.15, "pares": 0.10, "duques": 0.10, "primos_fib_mult3": 0.05
            }
            pesos_ia_versao = 0 # Versão 0 para pesos padrão/offline
            print("⚠️ Não foi possível obter pesos da IA do Supabase. Usando pesos padrão offline.")
        else:
            pesos_ia = pesos_ia_data["pesos"]
            pesos_ia_versao = pesos_ia_data["versao"]
        print(f"🧠 Pesos da IA utilizados (versão {pesos_ia_versao}): {pesos_ia}")

        # 2) Concursos base
        concursos_base = await supabase_client.get_ultimos_concursos(request.concursos_base_analise)
        if not concursos_base:
            print("⚠️ Não foi possível obter concursos base para análise do Supabase. O motor usará seus próprios dados offline.")
            concursos_base = [] # Passa uma lista vazia se não houver dados do Supabase

        # 3) Geração de jogos usando o LotofacilAIv3
        # A chamada deve ser para o método gerar_jogos_inteligentes do LotofacilAIv3
        # e deve receber os concursos_base e pesos_ia como argumentos.
        jogos_gerados = lotofacil_engine.gerar_jogos_inteligentes(
            concursos_base=concursos_base,
            pesos_ia=pesos_ia,
            quantidade_jogos=request.quantidade_jogos,
            concurso_alvo=request.concurso_alvo # Adicionado conforme a assinatura do método
        )
        if not jogos_gerados:
            raise HTTPException(status_code=500, detail="A IA não conseguiu gerar jogos.")

        custo_total = request.quantidade_jogos * request.valor_aposta_por_jogo
        parametros_geracao = {
            "quantidade_jogos": request.quantidade_jogos,
            "concursos_base_analise": request.concursos_base_analise,
            "valor_aposta_por_jogo": request.valor_aposta_por_jogo,
            "pesos_ia_versao": pesos_ia_versao,
        }

        # 4) Salvar lote de jogos (apenas se houver concursos base para referência)
        id_lote_jogos = None
        if concursos_base:
            id_lote_jogos = await supabase_client.salvar_jogos_gerados(
                concurso_base=concursos_base[0]["numero"], # Assumindo que o primeiro é o mais recente
                concurso_alvo=request.concurso_alvo,
                parametros=parametros_geracao,
                jogos=[{"dezenas": j} for j in jogos_gerados], # Supabase espera lista de dicts com 'dezenas'
                custo_total=custo_total,
            )
            if not id_lote_jogos:
                print("❌ Erro ao salvar os jogos gerados no Supabase. Prosseguindo sem ID de lote.")
        else:
            print("⚠️ Nenhum concurso base disponível para salvar o lote de jogos no Supabase.")

        print(f"✅ {len(jogos_gerados)} jogos gerados com sucesso pela IA.")
        return GerarJogosResponse(
            concurso_alvo=request.concurso_alvo,
            quantidade_jogos=request.quantidade_jogos,
            jogos=jogos_gerados,
            id_lote_jogos=id_lote_jogos if id_lote_jogos else "N/A", # Retorna N/A se não salvou
            custo_total=custo_total,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao gerar jogos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar jogos: {str(e)}")

# ==========================
# ENDPOINT: CONFERIR JOGOS
# ==========================
@app.post("/conferir", response_model=ConferirResponse)
async def conferir_jogos(request: ConferirRequest):
    """
    Confere os jogos gerados pela IA para um concurso específico.
    """
    try:
        # 1) Resultado oficial
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
                premio_total += 1000000.00 # Valor simbólico, ajustar conforme prêmio real

        lucro = premio_total - total_gasto

        # 4) Salvar resultado da conferência SOMENTE SE houver jogos gerados
        if id_lote_jogos: # Verifica se há um ID de lote de jogos
            # Criando um resumo simples para a memória
            resumo_conferencia = {
                "concurso": request.concurso,
                "total_jogos_gerados": total_jogos,
                "distribuicao_acertos": distribuicao_acertos,
                "premio_total": premio_total,
                "total_gasto": total_gasto,
                "lucro": lucro,
                "data_conferencia": datetime.utcnow().isoformat(),
            }

            # Resultado oficial completo para o JSONB
            resultado_oficial_json = {
                "numero": concurso_oficial["numero"],
                "data": concurso_oficial.get("data"),
                "dezenas": dezenas_sorteadas,
                "soma_dezenas": concurso_oficial.get("soma_dezenas", 0),
                "pares": concurso_oficial.get("pares", 0),
                "repetidas_anterior": concurso_oficial.get("repetidas_anterior", 0),
                "ciclo_custom": concurso_oficial.get("ciclo_custom"),
                "ciclo_qtd": concurso_oficial.get("ciclo_qtd", 0),
                "ausentes": concurso_oficial.get("ausentes", 0),
            }

            salvo = await supabase_client.salvar_resultado_conferencia(
                numero_concurso=request.concurso,
                jogos_gerados_id=id_lote_jogos,
                resultado_oficial=resultado_oficial_json, # Passando o objeto completo
                total_jogos=total_jogos,
                acertos_por_jogo=acertos_por_jogo,
                distribuicao_acertos=distribuicao_acertos,
                premio_total=premio_total,
                lucro=lucro,
                resumo=resumo_conferencia, # Adicionando o parâmetro 'resumo'
            )
            if salvo:
                await supabase_client.atualizar_status_conferencia(id_lote_jogos, "conferido") # Atualizado para usar id_lote_jogos
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
            jogos_gerados=jogos_ia,
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
