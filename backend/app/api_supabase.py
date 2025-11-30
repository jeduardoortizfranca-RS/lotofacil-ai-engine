# backend/app/api_supabase.py
import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Garante que o diretório backend esteja no sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Importa os serviços e o motor da IA
from core.lotofacil_ai_v3 import LotofacilAIv3
from app.services.supabase_client import SupabaseClient
from app.services.config_service import ConfigService

app = FastAPI(
    title="Lotofacil Supabase API",
    description="API para geração e conferência de jogos da Lotofácil integrada ao Supabase.",
    version="1.0.0",
)

# Configuração do CORS para permitir requisições do frontend
origins = [
    "http://localhost",
    "http://localhost:3000",  # Exemplo para um frontend React/Vue/Angular
    # Adicione aqui outros domínios do seu frontend em produção
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variáveis globais para as instâncias dos serviços e do motor da IA
supabase_client: Optional[SupabaseClient] = None
lotofacil_ai_engine: Optional[LotofacilAIv3] = None
config_service_instance: Optional[ConfigService] = None

# ==========================
# Modelos Pydantic
# ==========================
class GerarJogosRequest(BaseModel):
    concurso_alvo: int = Field(..., description="Número do concurso alvo (ainda não sorteado).")
    quantidade_jogos: int = Field(30, gt=0, description="Quantidade de jogos a gerar.")

class GerarJogosResponse(BaseModel):
    concurso_alvo: int
    quantidade_jogos: int
    jogos_gerados: List[List[int]]
    id_lote_gerado: str
    data_geracao: datetime
    custo_total: float

class ConferirRequest(BaseModel):
    concurso: int = Field(..., description="Número do concurso a ser conferido.")
    dezenas_sorteadas: List[int] = Field(..., min_length=15, max_length=15, description="As 15 dezenas sorteadas.")
    id_lote_jogos: str = Field(..., description="ID do lote de jogos gerados a ser conferido.")

class ConferirResponse(BaseModel):
    concurso: int
    dezenas_sorteadas: List[int]
    total_jogos: int
    distribuicao_acertos: Dict[str, int]
    total_gasto: float
    premio_total: float
    lucro: float
    id_lote_jogos: str

# Novos modelos para o relatório inteligente
class JogoDetalheRelatorio(BaseModel):
    numero_jogo: int
    dezenas_jogadas: List[int]
    acertos: int

class ResumoFinanceiro(BaseModel):
    total_jogos: int
    custo_total: float
    premio_total: float
    lucro: float

class AnalisePerformance(BaseModel):
    media_acertos_por_jogo: float
    melhor_jogo_acertos: int
    jogos_proximos_premio: int # Jogos com 9 ou 10 acertos
    diagnostico_geral: str
    recomendacao_ia_proximo_concurso: str

class RelatorioPerformanceResponse(BaseModel):
    concurso: int
    id_lote_jogos: str
    data_conferencia: datetime
    resultado_oficial: List[int]
    resumo_financeiro: ResumoFinanceiro
    distribuicao_acertos: Dict[str, int]
    analise_performance: AnalisePerformance
    detalhes_jogos: List[JogoDetalheRelatorio]

# ==========================
# Eventos de Inicialização e Desligamento
# ==========================
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Iniciando Lotofacil Supabase API... (Versão com Relatório Inteligente)")
    global supabase_client, lotofacil_ai_engine, config_service_instance
    try:
        # 1) Carregar variáveis de ambiente
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("❌ Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não encontradas. Verifique seu arquivo .env.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Configuração do Supabase ausente."
            )
        # 2) Inicializar e conectar o SupabaseClient
        supabase_client = SupabaseClient(supabase_url, supabase_key)
        conectado = await supabase_client.connect()
        if not conectado:
            logger.error("❌ Falha na conexão com Supabase. Verifique as credenciais ou a disponibilidade do serviço.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha na conexão com o Supabase."
            )
        logger.info("✅ Conexão com Supabase estabelecida.")
        # 3) Inicializar o ConfigService com o SupabaseClient
        config_service_instance = ConfigService()
        await config_service_instance.initialize(supabase_client)
        logger.info("✅ ConfigService inicializado com SupabaseClient.")
        # 4) Inicializar o motor da IA
        lotofacil_ai_engine = await LotofacilAIv3.create(
            db_client=supabase_client, # ADICIONADO AQUI!
            modo_offline=False, # Modo online, usando Supabase
            mazusoft_data_path="data/mazusoft_data.json", # Caminho para dados do Mazusoft (se usado)
        )
        logger.info("✅ Motor da IA LotofacilAIv3 inicializado.")

    except HTTPException:
        # Re-raise HTTPExceptions para que o FastAPI as trate
        raise
    except Exception as e:
        logger.error(f"❌ Falha crítica na inicialização da aplicação: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha crítica na inicialização da aplicação: {e}"
        )

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Lotofacil Supabase API...")
    if supabase_client and supabase_client.is_connected():
        await supabase_client.close()
        logger.info("✅ Conexão com Supabase fechada.")
    logger.info("API desligada.")

# ==========================
# Endpoints da API
# ==========================

@app.get("/")
async def read_root():
    return {"message": "Bem-vindo à API da Lotofácil com IA e Supabase!"}

@app.post("/gerar_jogos/", response_model=GerarJogosResponse)
async def gerar_jogos(request: GerarJogosRequest):
    if not lotofacil_ai_engine:
        raise HTTPException(status_code=500, detail="Motor da IA não inicializado.")

    try:
        # Obter o custo do jogo da configuração
        config_lotofacil = await supabase_client.get_config_lotofacil()
        custo_por_jogo = config_lotofacil.get("custo_jogo", 3.50) if config_lotofacil else 3.50 # Default para 3.50

        jogos_gerados = await lotofacil_ai_engine.gerar_jogos(
            quantidade_jogos=request.quantidade_jogos
        )

        custo_total = len(jogos_gerados) * custo_por_jogo

        jogos_data = {
            "concurso_alvo": request.concurso_alvo,
            "quantidade_jogos": len(jogos_gerados),
            "jogos": jogos_gerados,
            "data_geracao": datetime.now().isoformat(),
            "custo_total": custo_total,
            "status_conferencia": "pendente"
        }

        id_lote_gerado = await supabase_client.salvar_jogos_gerados(jogos_data)

        if not id_lote_gerado:
            raise HTTPException(status_code=500, detail="Falha ao salvar jogos gerados no Supabase.")

        return GerarJogosResponse(
            concurso_alvo=request.concurso_alvo,
            quantidade_jogos=len(jogos_gerados),
            jogos_gerados=jogos_gerados,
            id_lote_gerado=id_lote_gerado,
            data_geracao=datetime.now(),
            custo_total=custo_total
        )
    except Exception as e:
        logger.error(f"Erro ao gerar jogos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar jogos: {e}")

@app.post("/conferir_jogos/", response_model=ConferirResponse)
async def conferir_jogos(request: ConferirRequest):
    if not lotofacil_ai_engine:
        raise HTTPException(status_code=500, detail="Motor da IA não inicializado.")
    if not supabase_client:
        raise HTTPException(status_code=500, detail="SupabaseClient não inicializado.")

    try:
        # 1. Buscar os jogos gerados pelo ID do lote
        lote_jogos = await supabase_client.get_jogos_por_lote_id(request.id_lote_jogos)
        if not lote_jogos:
            raise HTTPException(status_code=404, detail=f"Lote de jogos com ID {request.id_lote_jogos} não encontrado.")

        jogos_a_conferir = lote_jogos.get("jogos", [])
        custo_total_lote = lote_jogos.get("custo_total", 0.0)

        # 2. Obter a tabela de prêmios e custo do jogo
        # A tabela de prêmios já é carregada na inicialização da IA
        tabela_premios = lotofacil_ai_engine.tabela_premios
        if not tabela_premios:
            logger.warning("Tabela de prêmios não encontrada na IA. Usando valores padrão.")
            tabela_premios = {"11": 6.0, "12": 12.0, "13": 30.0, "14": 1500.0, "15": 1000000.0} # Valores padrão

        # 3. Conferir os jogos
        resultados_conferencia = lotofacil_ai_engine.conferir_jogos(
            jogos_a_conferir,
            request.dezenas_sorteadas,
            tabela_premios
        )

        # 4. Calcular o prêmio total e lucro
        premio_total = resultados_conferencia["premio_total"]
        lucro = premio_total - custo_total_lote

        # 5. Preparar o resumo para salvar no Supabase
        resumo_conferencia = {
            "concurso": request.concurso,
            "resultado_oficial": request.dezenas_sorteadas, # Usando o nome correto da coluna
            "total_jogos": resultados_conferencia["total_jogos"],
            "distribuicao_acertos": resultados_conferencia["distribuicao_acertos"],
            "premio_total": premio_total,
            "lucro": lucro,
            "total_gasto": custo_total_lote,
            "jogos_gerados_id": request.id_lote_jogos,
            "data_conferencia": datetime.now().isoformat(),
            "acertos_por_jogo": resultados_conferencia["acertos_por_jogo"] # Salva o detalhe de acertos por jogo
        }

        # 6. Salvar o resultado da conferência
        salvo = await supabase_client.salvar_resultado_conferencia(resumo_conferencia)
        if not salvo:
            raise HTTPException(status_code=500, detail="Falha ao salvar resultado da conferência no Supabase.")

        # 7. Atualizar o status do lote de jogos para "conferido"
        await supabase_client.atualizar_status_conferencia(request.id_lote_jogos, "conferido")

        return ConferirResponse(
            concurso=request.concurso,
            dezenas_sorteadas=request.dezenas_sorteadas,
            total_jogos=resultados_conferencia["total_jogos"],
            distribuicao_acertos=resultados_conferencia["distribuicao_acertos"],
            total_gasto=custo_total_lote,
            premio_total=premio_total,
            lucro=lucro,
            id_lote_jogos=request.id_lote_jogos
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao conferir jogos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao conferir jogos: {e}")

@app.get("/relatorio_performance/{id_lote_jogos}", response_model=RelatorioPerformanceResponse)
async def get_relatorio_performance(id_lote_jogos: str):
    if not supabase_client:
        raise HTTPException(status_code=500, detail="SupabaseClient não inicializado.")

    try:
        # 1. Buscar os jogos gerados
        lote_jogos = await supabase_client.get_jogos_por_lote_id(id_lote_jogos)
        if not lote_jogos:
            raise HTTPException(status_code=404, detail=f"Lote de jogos com ID {id_lote_jogos} não encontrado.")

        # 2. Buscar o resultado da conferência
        resultado_conferencia = await supabase_client.get_resultado_conferencia_por_lote(id_lote_jogos)
        if not resultado_conferencia:
            raise HTTPException(status_code=404, detail=f"Resultado da conferência para o lote {id_lote_jogos} não encontrado.")

        # 3. Preparar os detalhes de cada jogo
        detalhes_jogos: List[JogoDetalheRelatorio] = []
        jogos_originais = lote_jogos.get("jogos", [])
        acertos_por_jogo = resultado_conferencia.get("acertos_por_jogo", [])

        for i, jogo_dezenas in enumerate(jogos_originais):
            detalhes_jogos.append(
                JogoDetalheRelatorio(
                    numero_jogo=i + 1,
                    dezenas_jogadas=jogo_dezenas,
                    acertos=acertos_por_jogo[i] if i < len(acertos_por_jogo) else 0
                )
            )

        # 4. Calcular métricas para a análise de performance
        total_acertos = sum(acertos_por_jogo)
        media_acertos = total_acertos / len(acertos_por_jogo) if acertos_por_jogo else 0
        melhor_jogo_acertos = max(acertos_por_jogo) if acertos_por_jogo else 0
        jogos_proximos_premio = sum(1 for acertos in acertos_por_jogo if acertos >= 9 and acertos <= 10)

        # 5. Gerar diagnóstico e recomendação da IA (texto simples por enquanto)
        diagnostico_geral = "Análise da performance da IA para este lote de jogos."
        recomendacao_ia = "A IA irá ajustar seus pesos para otimizar a seleção de dezenas com base nos resultados."

        if resultado_conferencia["lucro"] > 0:
            diagnostico_geral = "Excelente! A IA gerou lucro nesta rodada. Os padrões identificados foram eficazes."
            recomendacao_ia = "A IA continuará a explorar e reforçar os padrões de sucesso, buscando maior consistência nos acertos."
        elif melhor_jogo_acertos >= 13:
            diagnostico_geral = f"Muito bom! Tivemos jogos com {melhor_jogo_acertos} acertos, indicando que a IA está no caminho certo para grandes prêmios."
            recomendacao_ia = "A IA analisará as características dos jogos de maior acerto para replicar e otimizar esses padrões."
        elif jogos_proximos_premio > 0:
            diagnostico_geral = f"Promissor! {jogos_proximos_premio} jogos ficaram a 1 ou 2 acertos do prêmio. A IA está próxima de um avanço."
            recomendacao_ia = "A IA focará em refinar a seleção de dezenas para converter esses jogos próximos em jogos premiados."
        else:
            diagnostico_geral = "Nesta rodada, a IA gerou jogos que, embora não tenham atingido a faixa de premiação, demonstraram uma base sólida. Precisamos de ajustes."
            recomendacao_ia = "A IA irá reavaliar os pesos de fitness e os dados históricos para buscar novas combinações e aumentar a taxa de acertos premiados."


        return RelatorioPerformanceResponse(
            concurso=resultado_conferencia["concurso"],
            id_lote_jogos=id_lote_jogos,
            data_conferencia=datetime.fromisoformat(resultado_conferencia["data_conferencia"]),
            resultado_oficial=resultado_conferencia["resultado_oficial"], # CORREÇÃO AQUI
            resumo_financeiro=ResumoFinanceiro(
                total_jogos=resultado_conferencia["total_jogos"],
                custo_total=lote_jogos.get("custo_total", 0.0),
                premio_total=resultado_conferencia["premio_total"],
                lucro=resultado_conferencia["lucro"]
            ),
            distribuicao_acertos=resultado_conferencia["distribuicao_acertos"],
            analise_performance=AnalisePerformance(
                media_acertos_por_jogo=round(media_acertos, 2),
                melhor_jogo_acertos=melhor_jogo_acertos,
                jogos_proximos_premio=jogos_proximos_premio,
                diagnostico_geral=diagnostico_geral,
                recomendacao_ia_proximo_concurso=recomendacao_ia
            ),
            detalhes_jogos=detalhes_jogos
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar relatório de performance para o lote {id_lote_jogos}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar relatório: {e}")

