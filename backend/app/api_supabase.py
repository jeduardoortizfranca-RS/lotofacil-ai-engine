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

# ==========================
# Eventos de Inicialização e Desligamento
# ==========================
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Iniciando Lotofacil Supabase API...")
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
            modo_offline=False, # Modo online, usando Supabase
            mazusoft_data_path="data/mazusoft_data.json", # Caminho para dados do Mazusoft
            db_client=supabase_client # Passa o cliente Supabase para a IA
        )
        logger.info("✅ Motor de IA LotofacilAIv3 inicializado.")

    except HTTPException:
        # Re-raise HTTPExceptions para que o FastAPI as trate
        raise
    except Exception as e:
        logger.error(f"❌ Falha crítica na inicialização da aplicação: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha na inicialização do servidor: {e}"
        )

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Desligando Lotofacil Supabase API...")
    if supabase_client:
        await supabase_client.close()
        logger.info("✅ Conexão com Supabase fechada.")

# ==========================
# Endpoints de Status e Saúde
# ==========================
@app.get("/status", summary="Verifica o status da API e dos serviços")
async def get_status() -> Dict[str, bool]:
    return {
        "api_online": True,
        "supabase_conectado": supabase_client is not None and supabase_client.is_connected(),
        "config_service_inicializado": config_service_instance is not None and config_service_instance.supabase_client is not None,
        "motor_ia_inicializado": lotofacil_ai_engine is not None,
    }

# ==========================
# Endpoints da IA
# ==========================
@app.post("/gerar_jogos/", response_model=GerarJogosResponse, summary="Gera um lote de jogos da Lotofácil otimizados pela IA.")
async def gerar_jogos_endpoint(request: GerarJogosRequest):
    if not lotofacil_ai_engine:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Motor de IA não inicializado.")

    try:
        # O método gerar_jogos do LotofacilAIv3 já salva no banco e retorna o necessário
        response_data = await lotofacil_ai_engine.gerar_jogos(
            quantidade_jogos=request.quantidade_jogos,
            concurso_alvo=request.concurso_alvo
        )

        return GerarJogosResponse(
            concurso_alvo=response_data["concurso_alvo"],
            quantidade_jogos=response_data["quantidade_jogos"],
            jogos_gerados=response_data["jogos"],
            id_lote_gerado=response_data["jogos_gerados_id"],
            data_geracao=datetime.fromisoformat(response_data["data_geracao"]), # Converte de str para datetime
            custo_total=response_data["custo_total"]
        )
    except Exception as e:
        logger.error(f"❌ Erro ao gerar jogos: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao gerar jogos: {str(e)}")

@app.post("/conferir_jogos/", response_model=ConferirResponse, summary="Confere um lote de jogos gerados pela IA com um resultado oficial.")
async def conferir_jogos_endpoint(request: ConferirRequest):
    if not supabase_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SupabaseClient não inicializado.")
    if not config_service_instance:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ConfigService não inicializado.")

    try:
        # 1. Buscar jogos gerados pelo id_lote_jogos
        lote_jogos_data = await supabase_client.get_jogos_por_lote_id(request.id_lote_jogos)
        if not lote_jogos_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lote de jogos com ID {request.id_lote_jogos} não encontrado.")

        dezenas_jogos = lote_jogos_data.get("jogos", [])
        total_jogos = len(dezenas_jogos)
        if not dezenas_jogos:
            logger.warning(f"Lote {request.id_lote_jogos} não contém jogos. Retornando conferência vazia.")
            return ConferirResponse(
                concurso=request.concurso,
                dezenas_sorteadas=request.dezenas_sorteadas,
                total_jogos=0,
                distribuicao_acertos={},
                total_gasto=0.0,
                premio_total=0.0,
                lucro=0.0,
                id_lote_jogos=request.id_lote_jogos,
            )

        # 2. Calcular acertos por jogo
        distribuicao = {str(k): 0 for k in range(11, 16)}
        acertos_por_jogo: List[int] = []
        for jogo in dezenas_jogos:
            acertos = len(set(jogo) & set(request.dezenas_sorteadas))
            acertos_por_jogo.append(acertos)
            if acertos >= 11:
                distribuicao[str(acertos)] += 1

        # 3. Buscar tabela de prêmios do SupabaseClient (via ConfigService)
        premios = await config_service_instance.get_premios_por_acertos() # Usando o método do ConfigService
        if not premios:
            logger.warning("Tabela de prêmios não encontrada no ConfigService. Usando valores padrão.")
            premios = {11: 6.0, 12: 12.0, 13: 30.0, 14: 1500.0, 15: 1000000.0} # Seus valores padrão

        premio_total = 0.0
        for acertos_str, qtd in distribuicao.items():
            acertos = int(acertos_str)
            valor = premios.get(acertos, 0.0)
            premio_total += qtd * valor

        # 4. Obter custo do jogo do ConfigService
        config_lotofacil = await config_service_instance.get_config_lotofacil()
        custo_jogo = float(config_lotofacil.get("custo_jogo", 3.50)) # Default para 3.50 se não encontrar
        total_gasto = total_jogos * custo_jogo
        lucro = premio_total - total_gasto

        # 5. Salvar no Supabase
        if supabase_client and request.id_lote_jogos:
            resumo = {
                "concurso_numero": request.concurso,
                "data_conferencia": datetime.now().isoformat(),
                "jogos_gerados_id": request.id_lote_jogos,
                "resultado_oficial": request.dezenas_sorteadas,
                "total_jogos": total_jogos,
                "distribuicao_acertos": distribuicao,
                "premio_total": premio_total,
                "lucro": lucro,
                "acertos_por_jogo": acertos_por_jogo # Adicionado para corresponder ao schema
            }
            sucesso = await supabase_client.salvar_resultado_conferencia(resumo)
            if sucesso:
                await supabase_client.atualizar_status_conferencia(request.id_lote_jogos, "conferido")
                logger.info(f"✅ Conferência concluída e salva para concurso {request.concurso} (lote {request.id_lote_jogos}).")
            else:
                logger.error(f"❌ Erro ao salvar resultado da conferência para concurso {request.concurso}.")

        return ConferirResponse(
            concurso=request.concurso,
            dezenas_sorteadas=request.dezenas_sorteadas,
            total_jogos=total_jogos,
            distribuicao_acertos=distribuicao,
            total_gasto=total_gasto,
            premio_total=premio_total,
            lucro=lucro,
            id_lote_jogos=request.id_lote_jogos,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao conferir jogos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao conferir jogos: {str(e)}")

# ==========================
# Endpoint de Treinamento da IA (futuro)
# ==========================
# @app.post("/treinar_ia/{resultados_conferencia_id}", summary="Inicia um ciclo de aprendizado da IA com base em resultados de conferência.")
# async def treinar_ia_endpoint(resultados_conferencia_id: int):
#     if not lotofacil_ai_engine:
#         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Motor de IA não inicializado.")
#     try:
#         # await lotofacil_ai_engine.executar_ciclo_aprendizado(resultados_conferencia_id)
#         return {"message": "Ciclo de aprendizado da IA iniciado (funcionalidade em desenvolvimento)."}
#     except Exception as e:
#         logger.error(f"Erro ao treinar IA: {e}", exc_info=True)
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao treinar IA: {e}")
