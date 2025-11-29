# backend/app/services/supabase_client.py

import os
import logging
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from datetime import datetime

logger = logging.getLogger(__name__)

class SupabaseClient:
    """
    Cliente para interagir com o Supabase, encapsulando a lógica de conexão
    e as operações CRUD para as tabelas do projeto Lotofacil AI.
    """
    _instance = None
    _initialized = False

    def __new__(cls, url: Optional[str] = None, key: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
        return cls._instance

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        if not self._initialized:
            self.url = url if url else os.getenv("SUPABASE_URL")
            self.key = key if key else os.getenv("SUPABASE_KEY")
            self.client: Optional[Client] = None
            self._is_connected = False # Flag interna para o status da conexão
            self._initialized = True
            logger.info("SupabaseClient inicializado (singleton).")

    def is_connected(self) -> bool:
        """Retorna o status atual da conexão com o Supabase."""
        return self._is_connected

    async def connect(self) -> bool:
        """
        Estabelece a conexão com o Supabase e testa se está ativa.
        """
        if self.client and self._is_connected:
            logger.info("SupabaseClient já conectado.")
            return True

        if not self.url or not self.key:
            logger.error("Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não configuradas.")
            self._is_connected = False
            return False

        try:
            self.client = create_client(self.url, self.key)
            # Testar a conexão com uma query simples
            response = self.client.table("premios").select("acertos").limit(1).execute()
            if response.data is None and response.count is None:
                raise Exception("Resposta vazia ao testar conexão, pode indicar problema de autenticação ou tabela vazia.")

            self._is_connected = True
            logger.info("✅ Conexão com Supabase estabelecida e testada com sucesso.")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ou testar conexão com Supabase: {e}", exc_info=True)
            self.client = None
            self._is_connected = False
            return False

    async def close(self):
        """Fecha a conexão com o Supabase (se aplicável)."""
        if self.client:
            # A biblioteca supabase-py não tem um método 'close' explícito para HTTPX
            # Mas podemos limpar a referência para liberar recursos.
            self.client = None
            self._is_connected = False
            logger.info("SupabaseClient desconectado.")

    async def get_config_by_type(self, config_type: str) -> Optional[Dict[str, Any]]:
        """Busca uma configuração específica da tabela 'configuracoes' pelo tipo."""
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return None
        try:
            # Jose, de acordo com suas memórias, a coluna 'tipo' não existe.
            # A coluna correta é 'nome_config'. Ajustando a query.
            response = self.client.table("configuracoes").select("*").eq("nome_config", config_type).single().execute()
            if response.data is None:
                logger.warning(f"Nenhuma configuração encontrada para o tipo: {config_type}.")
                return None
            return response.data
        except Exception as e:
            if hasattr(e, 'code') and e.code == 'PGRST116': # Código para "nenhuma linha encontrada"
                logger.warning(f"Nenhuma configuração encontrada para o tipo: {config_type}.")
                return None
            logger.error(f"Erro ao buscar configuração do tipo '{config_type}': {e}", exc_info=True)
            return None

    async def get_latest_pesos_ia(self) -> Optional[Dict[str, float]]:
        """Busca os pesos de IA mais recentes da tabela 'pesos_ia'."""
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return None
        try:
            response = self.client.table("pesos_ia").select("pesos").order("data_atualizacao", desc=True).limit(1).single().execute()
            if response.data is None:
                logger.warning("Nenhum peso de IA encontrado na tabela 'pesos_ia'.")
                return None
            return response.data.get("pesos")
        except Exception as e:
            if hasattr(e, 'code') and e.code == 'PGRST116':
                logger.warning("Nenhum peso de IA encontrado na tabela 'pesos_ia'.")
                return None
            logger.error(f"Erro ao buscar pesos de IA mais recentes: {e}", exc_info=True)
            return None

    async def insert_pesos_ia(self, pesos_data: Dict[str, Any]) -> bool:
        """Insere novos pesos de IA na tabela 'pesos_ia'."""
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return False
        try:
            response = self.client.table("pesos_ia").insert(pesos_data).execute()
            if response.data is None or not response.data:
                raise Exception(f"Erro ao inserir pesos de IA: {response.error if hasattr(response, 'error') and response.error else 'Dados vazios'}")
            logger.info("✅ Pesos de IA inseridos com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro ao inserir pesos de IA: {e}", exc_info=True)
            return False

    async def get_tabela_premios(self) -> List[Dict[str, Any]]:
        """Busca a tabela de prêmios da tabela 'premios'."""
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return []
        try:
            response = self.client.table("premios").select("*").order("acertos", desc=True).execute()
            if response.data is None:
                logger.warning("Nenhuma tabela de prêmios encontrada.")
                return []
            return response.data
        except Exception as e:
            logger.error(f"Erro ao buscar tabela de prêmios: {e}", exc_info=True)
            return []

    async def get_historico_concursos(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Busca o histórico de concursos da tabela 'concursos'."""
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return []
        try:
            query = self.client.table("concursos").select("*").order("numero", desc=True)
            if limit:
                query = query.limit(limit)
            response = query.execute()
            if response.data is None:
                logger.warning("Nenhum histórico de concursos encontrado.")
                return []
            return response.data
        except Exception as e:
            logger.error(f"Erro ao buscar histórico de concursos: {e}", exc_info=True)
            return []

    async def get_frequencias(self) -> List[Dict[str, Any]]:
        """
        NOVO MÉTODO: Busca as frequências das dezenas da tabela 'frequencias'.
        """
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return []
        try:
            response = self.client.table("frequencias").select("*").order("dezena", asc=True).execute()
            if response.data is None:
                logger.warning("Nenhuma frequência de dezenas encontrada.")
                return []
            return response.data
        except Exception as e:
            logger.error(f"Erro ao buscar frequências de dezenas: {e}", exc_info=True)
            return []

    async def salvar_jogos_gerados(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Salva um lote de jogos gerados na tabela 'jogos_gerados'."""
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return None
        try:
            response = self.client.table("jogos_gerados").insert(kwargs).execute()
            if response.data is None or not response.data:
                raise Exception(f"Erro ao salvar jogos gerados: {response.error if hasattr(response, 'error') and response.error else 'Dados vazios'}")
            logger.info(f"✅ Lote de jogos {kwargs.get('id')} salvo com sucesso.")
            return response.data[0] # Retorna o primeiro (e único) registro inserido
        except Exception as e:
            logger.error(f"Erro ao salvar jogos gerados: {e}", exc_info=True)
            return None

    async def get_jogos_por_lote_id(self, lote_id: str) -> Optional[Dict[str, Any]]:
        """Busca um lote de jogos gerados pelo ID."""
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return None
        try:
            response = self.client.table("jogos_gerados").select("*").eq("id", lote_id).single().execute()
            if response.data is None:
                logger.warning(f"Nenhum lote de jogos encontrado para o ID: {lote_id}.")
                return None
            return response.data
        except Exception as e:
            if hasattr(e, 'code') and e.code == 'PGRST116':
                logger.warning(f"Nenhum lote de jogos encontrado para o ID: {lote_id}.")
                return None
            logger.error(f"Erro ao buscar lote de jogos {lote_id}: {e}", exc_info=True)
            return None

    async def salvar_resultado_conferencia(self, resumo: Dict[str, Any]) -> bool:
        """Salva o resultado da conferência de um lote de jogos na tabela 'resultados_conferencia'."""
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return False
        try:
            # Garantir que resultado_oficial não seja nulo, conforme memória
            if 'resultado_oficial' not in resumo or resumo['resultado_oficial'] is None:
                raise ValueError("O campo 'resultado_oficial' é obrigatório e não pode ser nulo.")

            response = self.client.table("resultados_conferencia").insert(resumo).execute()
            if response.data is None or not response.data:
                raise Exception(f"Erro ao salvar resultado da conferência: {response.error if hasattr(response, 'error') and response.error else 'Dados vazios'}")
            logger.info(f"✅ Resultado da conferência para o concurso {resumo.get('concurso_numero')} salvo com sucesso.")
            return True
        except ValueError as ve:
            logger.error(f"Erro de validação ao salvar resultado da conferência: {ve}")
            return False
        except Exception as e:
            logger.error(f"Erro ao salvar resultado da conferência: {e}", exc_info=True)
            return False

    async def atualizar_status_conferencia(self, lote_id: str, status: str) -> bool:
        """Atualiza o status de conferência de um lote de jogos."""
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return False
        try:
            response = self.client.table("jogos_gerados").update({"status_conferencia": status}).eq("id", lote_id).execute()
            if response.data is None or not response.data:
                raise Exception(f"Erro ao atualizar status de conferência para o lote {lote_id}: {response.error if hasattr(response, 'error') and response.error else 'Dados vazios'}")
            logger.info(f"✅ Status de conferência do lote {lote_id} atualizado para '{status}'.")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar status de conferência para o lote {lote_id}: {e}", exc_info=True)
            return False

    async def get_concurso_por_numero(self, numero: int) -> Optional[Dict[str, Any]]:
        """Busca um concurso específico pelo número."""
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return None
        try:
            response = self.client.table("concursos").select("*").eq("numero", numero).single().execute()
            if response.data is None:
                logger.warning(f"Nenhum concurso encontrado para o número: {numero}.")
                return None
            return response.data
        except Exception as e:
            if hasattr(e, 'code') and e.code == 'PGRST116': # Código para "nenhuma linha encontrada"
                logger.warning(f"Nenhum concurso encontrado para o número: {numero}.")
                return None
            logger.error(f"Erro ao buscar concurso {numero}: {e}", exc_info=True)
            return None

    async def salvar_concurso(self, concurso_data: Dict[str, Any]) -> bool:
        """Salva um novo concurso na tabela 'concursos'."""
        if not self.client or not self._is_connected:
            logger.error("SupabaseClient não conectado.")
            return False
        try:
            response = self.client.table("concursos").insert(concurso_data).execute()
            if response.data is None or not response.data:
                raise Exception(f"Erro ao salvar concurso {concurso_data.get('numero')}: {response.error if hasattr(response, 'error') and response.error else 'Dados vazios'}")
            logger.info(f"✅ Concurso {concurso_data.get('numero')} salvo com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar concurso {concurso_data.get('numero')}: {e}", exc_info=True)
            return False
