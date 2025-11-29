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
from .services.supabase_client import SupabaseClient # SupabaseClient está em backend/app/services/supabase_client.py (importação relativa)

app = FastAPI(
    title="Lotofacil Supabase API",
    description="Gera e confere jogos com Supabase",
    version="1.0.0",
)

engine: Optional[LotofacilAIv3] = None
supabase: Optional[SupabaseClient] = None

class GerarJogosRequest(BaseModel):
    concurso_alvo: int = Field(..., description="Número do concurso para o qual os jogos serão gerados.")
    quantidade_jogos: int = Field(30, gt=0, description="Quantidade de jogos a serem gerados.")
    concursos_base_analise: int = Field(10, gt=0, description="Quantidade de concursos anteriores usados na análise.")
    valor_aposta_por_jogo: float = Field(3.0, gt=0, description="Valor da aposta por jogo (para cálculo do custo).")

class GerarJogosResponse(BaseModel):
    sucesso: bool
    id_lote_jogos: str
    concurso_alvo: int
    quantidade_jogos: int
    custo_total: float
    jogos: List[List[int]] # A resposta do motor é uma lista de listas de inteiros

class ConferirRequest(BaseModel):
    concurso: int = Field(..., description="Número do concurso a ser conferido.")
    valor_aposta_por_jogo: float = Field(3.0, gt=0, description="Valor da aposta por jogo (para cálculo de custo e lucro).") # Adicionado para cálculo de lucro

class ConferirResponse(BaseModel):
    concurso: int
    dezenas_sorteadas: List[int]
    total_jogos: int
    distribuicao_acertos: Dict[str, int]
    total_gasto: float
    premio_total: float
    lucro: float
    id_lote_jogos: Optional[str]

@app.on_event("startup")
async def startup():
    global engine, supabase
    print("\n🚀 Iniciando Lotofacil Supabase API...")
    # A documentação diz que LotofacilAIv3 está em backend/core/lotofacil_ai_v3.py
    # e que a API Offline (main.py) usa modo_offline=True e mazusoft_data_path.
    # Vamos manter essa inicialização para o motor de IA.
    engine = LotofacilAIv3(
        modo_offline=True,
        mazusoft_data_path=os.path.join(backend_path, "data", "mazusoft_data.json"), # Caminho ajustado
    )
    supabase = SupabaseClient()
    await supabase.get_pool()
    print("✅ Motor IA e Supabase inicializados.")

@app.on_event("shutdown")
async def shutdown():
    global supabase
    if supabase:
        await supabase.close()
        print("🛑 Pool Supabase fechado.")

@app.get("/")
async def root():
    return {
        "nome": "Lotofacil Supabase API",
        "rotas": ["/gerar-jogos", "/conferir"],
        "timestamp": datetime.now().isoformat(),
    }

@app.post("/gerar-jogos", response_model=GerarJogosResponse) # Adicionado response_model
async def gerar_jogos(req: GerarJogosRequest):
    global engine, supabase
    try:
        # 1) pesos (poderia ser usado pelo motor, por enquanto só log)
        pesos_ia_data = await supabase.get_pesos_ia_atuais()
        if not pesos_ia_data:
            raise HTTPException(status_code=404, detail="Não foi possível obter os pesos da IA.")
        pesos_ia = pesos_ia_data["pesos"]
        pesos_ia_versao = pesos_ia_data["versao"]
        print(f"🧠 Pesos IA (versão {pesos_ia_versao}): {pesos_ia}")

        # 2) concursos base (apenas para futura análise, não quebra se vazio)
        concursos_base = await supabase.get_ultimos_concursos(req.concursos_base_analise)
        if not concursos_base:
            print("⚠️ Nenhum concurso base retornado; motor usará dados próprios ou padrão.")
            # Se o motor LotofacilAIv3 precisa de concursos_base, isso pode ser um problema.
            # A documentação diz que o motor usa "concursos_base_analise" como parâmetro.
            # Vamos garantir que ele receba uma lista vazia se não houver dados, ou um valor padrão.
            # A função gerar_jogos_inteligentes do LotofacilAIv3 deve ser robusta para isso.

        # 3) gera jogos pelo motor existente
        # A chamada deve ser para o método gerar_jogos_inteligentes do LotofacilAIv3
        # e deve receber os concursos_base e pesos_ia como argumentos, além da quantidade.
        # A documentação do LotofacilAIv3 diz: engine.gerar_jogos_inteligentes(concurso_alvo, 30, 10, pesos["pesos"])
        # Vamos ajustar para os parâmetros nomeados que o método provavelmente espera.
        jogos = engine.gerar_jogos_inteligentes(
            concursos_base=concursos_base, # Passando os concursos base
            pesos_ia=pesos_ia, # Passando os pesos da IA
            quantidade_jogos=req.quantidade_jogos,
            concurso_alvo=req.concurso_alvo, # Adicionado conforme documentação
            # modo="normal", # Removido, pois não está na documentação de parâmetros de geração
        )
        if not jogos:
            raise HTTPException(status_code=500, detail="Motor não gerou jogos")

        custo_total = req.quantidade_jogos * req.valor_aposta_por_jogo
        parametros = {
            "quantidade_jogos": req.quantidade_jogos,
            "concursos_base_analise": req.concursos_base_analise,
            "valor_aposta_por_jogo": req.valor_aposta_por_jogo,
            "pesos_ia_versao": pesos_ia_versao,
        }

        # A documentação diz que concurso_base é o numero do primeiro concurso base.
        # Se concursos_base estiver vazio, precisamos de um valor padrão ou tratar.
        concurso_base_num = concursos_base[0]["numero"] if concursos_base else None # Alterado para None se vazio

        id_lote = await supabase.salvar_jogos_gerados(
            concurso_base=concurso_base_num,
            concurso_alvo=req.concurso_alvo,
            parametros=parametros,
            jogos=[{"dezenas": j} for j in jogos], # Supabase espera lista de dicts com 'dezenas'
            custo_total=custo_total,
        )

        if not id_lote:
            raise HTTPException(status_code=500, detail="Erro ao salvar os jogos gerados no Supabase.")

        print(f"✅ {len(jogos)} jogos gerados com sucesso pela IA e salvos com ID de lote: {id_lote}.")
        return GerarJogosResponse(
            sucesso=True,
            id_lote_jogos=id_lote,
            concurso_alvo=req.concurso_alvo,
            quantidade_jogos=req.quantidade_jogos,
            custo_total=custo_total,
            jogos=jogos,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao gerar jogos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar jogos: {str(e)}")

@app.post("/conferir", response_model=ConferirResponse)
async def conferir(req: ConferirRequest):
    global supabase
    try:
        # 1) resultado oficial
        concurso_oficial = await supabase.get_concurso_por_numero(req.concurso)
        if not concurso_oficial:
            raise HTTPException(status_code=404, detail=f"Concurso {req.concurso} não encontrado em concursos")
        dezenas_sorteadas = concurso_oficial["dezenas"]

        # 2) jogos gerados
        lote = await supabase.get_jogos_gerados_para_concurso(req.concurso)
        if not lote:
            raise HTTPException(status_code=404, detail=f"Nenhum lote de jogos gerados encontrado para o concurso {req.concurso}")

        jogos_reg = lote["jogos"]  # lista de dicts {"dezenas":[...]}
        jogos = [j["dezenas"] for j in jogos_reg]
        id_lote = str(lote["id"])
        total_jogos = len(jogos)
        total_gasto = float(lote["custo_total"] or 0) # Usando o custo_total do lote salvo

        # 3) conferência
        distribuicao = {"0-10": 0, "11": 0, "12": 0, "13": 0, "14": 0, "15": 0}
        acertos_por_jogo: List[int] = []
        premio_total = 0.0
        for dezenas in jogos:
            acertos = len(set(dezenas) & set(dezenas_sorteadas))
            acertos_por_jogo.append(acertos)
            if acertos >= 11:
                distribuicao[str(acertos)] += 1
            else:
                distribuicao["0-10"] += 1
            if acertos == 11:
                premio_total += 6.0
            elif acertos == 12:
                premio_total += 12.0
            elif acertos == 13:
                premio_total += 30.0
            elif acertos == 14:
                premio_total += 1500.0
            elif acertos == 15:
                premio_total += 1000000.0 # Valor simbólico, ajustar conforme prêmio real

        lucro = premio_total - total_gasto

        # 4) resumo + resultado_oficial para NOT NULL (conforme documentação e memórias)
        resultado_oficial_json = { # Renomeado para evitar conflito com a variável concurso_oficial
            "numero": concurso_oficial["numero"],
            "data": concurso_oficial.get("data"), # Usar .get para evitar KeyError se a chave não existir
            "dezenas": dezenas_sorteadas,
            "soma_dezenas": concurso_oficial.get("soma_dezenas", 0),
            "pares": concurso_oficial.get("pares", 0),
            "repetidas_anterior": concurso_oficial.get("repetidas_anterior", 0),
            "ciclo_custom": concurso_oficial.get("ciclo_custom"),
            "ciclo_qtd": concurso_oficial.get("ciclo_qtd", 0),
            "ausentes": concurso_oficial.get("ausentes", 0),
        }

        # Correção do erro de sintaxe: atribuição da variável 'resumo'
        resumo_conferencia = {
            "numero_concurso": req.concurso,
            "total_jogos": total_jogos,
            "distribuicao_acertos": distribuicao,
            "total_gasto": total_gasto, # Adicionado ao resumo, mas não na tabela resultados_conferencia
            "premio_total": premio_total,
            "lucro": lucro,
            "data_conferencia": datetime.utcnow().isoformat(),
        }

        # Salvar resultado da conferência
        salvo = await supabase.salvar_resultado_conferencia(
            numero_concurso=req.concurso,
            jogos_gerados_id=id_lote,
            resultado_oficial=resultado_oficial_json, # Passando o JSON completo do resultado oficial
            resumo=resumo_conferencia, # Passando o JSON do resumo
            total_jogos=total_jogos,
            acertos_por_jogo=acertos_por_jogo,
            distribuicao_acertos=distribuicao,
            premio_total=premio_total,
            lucro=lucro,
            # total_gasto não deve ser passado para salvar_resultado_conferencia, conforme documentação
        )

        if salvo:
            # Atualizar status_conferencia para o ID do lote de jogos, não para o número do concurso
            await supabase.atualizar_status_conferencia(id_lote, "conferido")
            print(f"✅ Conferência concluída e salva para concurso {req.concurso} (lote {id_lote}).")
            print(f"   Total de jogos: {total_jogos}")
            print(f"   Distribuição: {distribuicao}")
            print(f"   Lucro: R$ {lucro:.2f}")
        else:
            print(f"❌ Erro ao salvar resultado da conferência para concurso {req.concurso}")

        return ConferirResponse(
            concurso=req.concurso,
            dezenas_sorteadas=dezenas_sorteadas,
            total_jogos=total_jogos,
            distribuicao_acertos=distribuicao,
            total_gasto=total_gasto,
            premio_total=premio_total,
            lucro=lucro,
            id_lote_jogos=id_lote,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao conferir jogos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno ao conferir jogos: {str(e)}")
