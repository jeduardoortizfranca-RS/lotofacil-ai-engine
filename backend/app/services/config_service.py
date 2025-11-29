# backend/app/services/config_service.py

import logging
from typing import Dict, Any, Optional
from app.services.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Serviço para gerenciar configurações globais do sistema,
    como custo do jogo e pesos da IA, lendo do Supabase.
    Implementado como singleton simples.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.supabase_client: Optional[SupabaseClient] = None
            self._initialized = True
            logger.info("ConfigService inicializado (singleton).")

    async def initialize(self, supabase_client: SupabaseClient):
        """
        Inicializa o ConfigService com uma instância do SupabaseClient.
        Deve ser chamado uma vez na inicialização da aplicação.
        """
        if self.supabase_client is None:
            self.supabase_client = supabase_client
            logger.info("ConfigService conectado ao SupabaseClient.")
        else:
            logger.debug("ConfigService já está conectado ao SupabaseClient.")

    # ---------- CONFIG LOTOFÁCIL (custo do jogo) ----------

    @classmethod
    async def get_config_lotofacil(cls) -> Dict[str, Any]:
        """
        Busca as configurações gerais da Lotofácil (ex: custo do jogo)
        da tabela 'padroes_gerais' no Supabase.
        Retorno esperado: {"custo_jogo": 3.50}
        """
        instance = cls()
        if not instance.supabase_client:
            logger.error("ConfigService não inicializado com SupabaseClient.")
            return {"custo_jogo": 3.50}  # Valor default em caso de falha

        try:
            response = await instance.supabase_client.get_config_by_type("config_lotofacil")
            if response and response.get("valor"):
                logger.debug(f"Configuração Lotofácil carregada: {response['valor']}")
                return response["valor"]
            logger.warning("Configuração 'config_lotofacil' não encontrada. Usando default.")
            return {"custo_jogo": 3.50}
        except Exception as e:
            logger.error(f"Erro ao buscar config_lotofacil do Supabase: {e}", exc_info=True)
            return {"custo_jogo": 3.50}  # Valor default em caso de erro

    # ---------- PESOS DA IA (tabela pesos_ia) ----------

    @classmethod
    async def get_pesos_ia_atuais(cls) -> Dict[str, float]:
        """
        Busca os pesos de fitness mais recentes da IA
        da tabela 'pesos_ia' no Supabase.
        """
        instance = cls()
        if not instance.supabase_client:
            logger.error("ConfigService não inicializado com SupabaseClient.")
            return cls._pesos_default()

        try:
            response = await instance.supabase_client.get_latest_pesos_ia()
            if response and response.get("pesos"):
                logger.debug(f"Pesos da IA carregados (versão {response.get('versao')}): {response['pesos']}")
                return response["pesos"]
            logger.warning("Nenhum peso da IA encontrado na tabela 'pesos_ia'. Usando defaults.")
            return cls._pesos_default()
        except Exception as e:
            logger.error(f"Erro ao buscar pesos da IA do Supabase: {e}", exc_info=True)
            return cls._pesos_default()

    @classmethod
    async def registrar_nova_versao_pesos(cls, pesos: Dict[str, float], motivo_ajuste: str) -> bool:
        """
        Registra uma nova versão dos pesos da IA na tabela 'pesos_ia'.
        """
        instance = cls()
        if not instance.supabase_client:
            logger.error("ConfigService não inicializado com SupabaseClient.")
            return False

        try:
            latest_pesos_record = await instance.supabase_client.get_latest_pesos_ia()
            nova_versao = (latest_pesos_record.get("versao", 0) if latest_pesos_record else 0) + 1

            success = await instance.supabase_client.insert_pesos_ia(
                versao=nova_versao,
                pesos=pesos,
                motivo_ajuste=motivo_ajuste
            )
            if success:
                logger.info(f"✅ Nova versão de pesos da IA registrada: Versão {nova_versao}, Motivo: {motivo_ajuste}")
            else:
                logger.error(f"Falha ao registrar nova versão de pesos da IA: Versão {nova_versao}")
            return success
        except Exception as e:
            logger.error(f"Erro ao registrar nova versão de pesos da IA no Supabase: {e}", exc_info=True)
            return False

    # ---------- PRÊMIOS (tabela premios) ----------

    @classmethod
    async def get_premios_por_acertos(cls) -> Dict[int, float]:
        """
        Busca a tabela de prêmios por acertos da tabela 'premios' no Supabase.
        """
        instance = cls()
        if not instance.supabase_client:
            logger.error("ConfigService não inicializado com SupabaseClient.")
            return cls._premios_default()

        try:
            premios_list = await instance.supabase_client.get_premios()
            premios_dict = {p.get('acertos'): float(p.get('valor')) for p in premios_list if p.get('acertos') is not None and p.get('valor') is not None}
            if premios_dict:
                logger.debug(f"Tabela de prêmios carregada: {premios_dict}")
                return premios_dict
            logger.warning("Tabela de prêmios vazia ou não encontrada. Usando valores padrão.")
            return cls._premios_default()
        except Exception as e:
            logger.error(f"Erro ao buscar tabela de prêmios do Supabase: {e}", exc_info=True)
            return cls._premios_default()

    # ---------- VALORES DEFAULT ----------

    @staticmethod
    def _pesos_default() -> Dict[str, float]:
        """
        Pesos padrão iniciais para a IA, caso não exista nada na tabela.
        """
        return {
            "soma": 0.15, "pares": 0.10, "duques": 0.10, "ausentes": 0.15,
            "repetidas": 0.25, "frequencia": 0.20, "primos": 0.05,
            "fibonacci": 0.05, "multiplos_3": 0.05, "moldura": 0.05,
            "centro": 0.05, "sequencia_longa": 0.05, "densidade": 0.05
        }

    @staticmethod
    def _premios_default() -> Dict[int, float]:
        """
        Valores de prêmio padrão, caso a tabela 'premios' esteja vazia ou inacessível.
        """
        return {11: 6.0, 12: 12.0, 13: 30.0, 14: 1500.0, 15: 1000000.0}
