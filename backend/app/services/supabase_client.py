import logging
from typing import List, Dict, Any, Optional

from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SupabaseClient:
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.client: Optional[Client] = None
        self._is_connected = False

    async def connect(self) -> bool:
        """
        Inicializa o cliente Supabase e testa a conexão.
        """
        try:
            self.client = create_client(self.url, self.key)
            # Teste simples: tentar selecionar algo da tabela concursos
            response = self.client.table("concursos").select("numero").limit(1).execute()
            # se não der exceção, consideramos conectado, mesmo que não haja dados
            self._is_connected = True
            logger.info("Conexão com Supabase estabelecida e verificada.")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar ou verificar conexão com Supabase: {e}", exc_info=True)
            self._is_connected = False
            return False

    def is_connected(self) -> bool:
        """
        Retorna o status da conexão.
        """
        return self._is_connected

    async def close(self):
        """
        "Fecha" a conexão (na prática só limpa a referência).
        """
        self.client = None
        self._is_connected = False
        logger.info("Conexão com Supabase fechada (referência limpa).")

    # --------- CONCURSOS ---------

    async def get_ultimo_concurso(self) -> Optional[Dict[str, Any]]:
        """
        Busca o último concurso sorteado.
        """
        try:
            response = self.client.table("concursos")\
                .select("*")\
                .order("numero", desc=True)\
                .limit(1)\
                .execute()
            data = response.data
            if data:
                return data[0]
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar último concurso: {e}", exc_info=True)
            return None

    async def get_concursos_anteriores(self, concurso_alvo: int, quantidade: int = 10) -> List[Dict[str, Any]]:
        """
        Busca os N concursos anteriores ao concurso_alvo.
        """
        try:
            response = self.client.table("concursos")\
                .select("numero, data_sorteio, dezenas")\
                .lt("numero", concurso_alvo)\
                .order("numero", desc=True)\
                .limit(quantidade)\
                .execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Erro ao buscar concursos anteriores: {e}", exc_info=True)
            return []

    async def get_todos_concursos(self) -> List[Dict[str, Any]]:
        """
        Busca todos os concursos.
        """
        try:
            response = self.client.table("concursos")\
                .select("numero, dezenas")\
                .order("numero", desc=False)\
                .execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Erro ao buscar todos os concursos: {e}", exc_info=True)
            return []

    # --------- JOGOS GERADOS ---------

    async def salvar_jogos_gerados(self, jogos_data: Dict[str, Any]) -> Optional[str]:
        """
        Salva um lote de jogos gerados no Supabase.
        """
        try:
            response = self.client.table("jogos_gerados").insert(jogos_data).execute()
            data = response.data
            if data and data[0].get("id"):
                logger.info(
                    f"Lote de jogos {data[0]['id']} salvo com sucesso para o concurso "
                    f"{jogos_data.get('concurso_alvo')}."
                )
                return data[0]["id"]
            logger.error(f"Falha ao salvar jogos gerados: {data}")
            return None
        except Exception as e:
            logger.error(f"Erro ao salvar jogos gerados: {e}", exc_info=True)
            return None

    async def get_jogos_por_lote_id(self, lote_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca um lote de jogos gerados pelo seu ID.
        """
        try:
            response = self.client.table("jogos_gerados")\
                .select("*")\
                .eq("id", lote_id)\
                .limit(1)\
                .execute()
            data = response.data
            if data:
                return data[0]
            logger.warning(f"Lote de jogos com ID {lote_id} não encontrado.")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar lote de jogos {lote_id}: {e}", exc_info=True)
            return None

    async def atualizar_status_conferencia(self, lote_id: str, status: str) -> bool:
        """
        Atualiza o status de conferência de um lote de jogos.
        """
        try:
            response = self.client.table("jogos_gerados")\
                .update({"status_conferencia": status})\
                .eq("id", lote_id)\
                .execute()
            logger.info(f"Status de conferência do lote {lote_id} atualizado para '{status}'.")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar status de conferência do lote {lote_id}: {e}", exc_info=True)
            return False

    # --------- RESULTADOS CONFERÊNCIA ---------

    async def salvar_resultado_conferencia(self, resumo: Dict[str, Any]) -> bool:
        """
        Salva o resultado da conferência de um lote de jogos.
        """
        try:
            response = self.client.table("resultados_conferencia").insert(resumo).execute()
            logger.info(
                f"Resultado da conferência para o concurso {resumo.get('concurso')} salvo com sucesso."
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar resultado da conferência: {e}", exc_info=True)
            return False

    async def get_resultado_conferencia_por_lote(self, jogos_gerados_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca o resultado mais recente da conferência para um lote específico.
        """
        try:
            response = self.client.table("resultados_conferencia")\
                .select("*")\
                .eq("jogos_gerados_id", jogos_gerados_id)\
                .order("id", desc=True)\
                .limit(1)\
                .execute()
            data = response.data
            if data:
                return data[0]
            logger.warning(f"Nenhum resultado de conferência encontrado para o lote {jogos_gerados_id}.")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar resultado_conferencia para lote {jogos_gerados_id}: {e}", exc_info=True)
            return None

    # --------- CONFIGURAÇÕES ---------

    async def get_configuracao_por_nome(self, nome_config: str) -> Optional[Dict[str, Any]]:
        """
        Busca uma configuração específica pelo nome.
        """
        try:
            response = self.client.table("configuracoes")\
                .select("*")\
                .eq("nome_config", nome_config)\
                .limit(1)\
                .execute()
            data = response.data
            if data:
                return data[0]
            logger.warning(f"Configuração '{nome_config}' não encontrada.")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar configuração '{nome_config}': {e}", exc_info=True)
            return None

    async def get_tabela_premios(self) -> Optional[Dict[str, Any]]:
        """
        Busca a tabela de prêmios da Lotofácil.
        """
        try:
            response = self.client.table("configuracoes")\
                .select("valor")\
                .eq("nome_config", "tabela_premios_lotofacil")\
                .limit(1)\
                .execute()
            data = response.data
            if data and data[0].get("valor"):
                return data[0]["valor"]
            logger.warning("Tabela de prêmios não encontrada na configuração 'tabela_premios_lotofacil'.")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar tabela de prêmios: {e}", exc_info=True)
            return None

    async def get_config_lotofacil(self) -> Optional[Dict[str, Any]]:
        """
        Busca as configurações gerais da Lotofácil (ex: custo do jogo).
        """
        try:
            response = self.client.table("configuracoes")\
                .select("valor")\
                .eq("nome_config", "config_lotofacil")\
                .limit(1)\
                .execute()
            data = response.data
            if data and data[0].get("valor"):
                return data[0]["valor"]
            logger.warning("Configuração 'config_lotofacil' não encontrada.")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar configuração 'config_lotofacil': {e}", exc_info=True)
            return None
