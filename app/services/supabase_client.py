"""
Cliente Supabase para operações de banco de dados
"""
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import asyncpg
from datetime import datetime, date # Importar date também
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env
load_dotenv()

class SupabaseClient:
    """
    Cliente para interação com banco Supabase via asyncpg.
    Gerencia pool de conexões e operações CRUD.
    """
    def __init__(self):
        self.pool = None
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL não encontrada. Configure no arquivo backend/.env")
        masked_url = self.db_url.split(":")[0] + "://..." + self.db_url.split("@")[-1]
        print(f"SupabaseClient inicializado com: {masked_url}")

    async def get_pool(self):
        """Retorna pool de conexões (cria se não existir)"""
        if self.pool is None:
            print("Criando pool de conexões...")
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )
            print("Pool de conexões criado com sucesso")
        return self.pool

    async def close(self):
        """Fecha pool de conexões"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    def _json_serial(self, obj):
        """JSON serializer para objetos datetime e date"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    def _process_dezenas(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Garante que dezenas seja lista[int]."""
        if "dezenas" in row_data:
            if isinstance(row_data["dezenas"], str):
                try:
                    row_data["dezenas"] = json.loads(row_data["dezenas"])
                except json.JSONDecodeError as e:
                    print(f"Erro ao decodificar dezenas: {e}. Retornando lista vazia.")
                    row_data["dezenas"] = []
            elif isinstance(row_data["dezenas"], list):
                row_data["dezenas"] = [int(d) for d in row_data["dezenas"]]
            else:
                row_data["dezenas"] = []
        return row_data

    def _process_numeric_fields(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Campos numéricos nunca ficam None."""
        numeric_fields = [
            "repetidas_anterior",
            "soma_dezenas",
            "pares",
            "ciclo_qtd",
            "ausentes", # Adicionado conforme a documentação da tabela concursos
        ]
        for field in numeric_fields:
            if field in row_data and row_data[field] is None:
                row_data[field] = 0 # Define 0 como padrão para None
        return row_data

    # ============================================================================
    # MÉTODOS PARA CONCURSOS
    # ============================================================================

    async def get_ultimo_concurso(self) -> Optional[Dict[str, Any]]:
        """Retorna o último concurso registrado."""
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                print("Buscando último concurso...")
                row = await conn.fetchrow("""
                    SELECT numero, data, dezenas, soma_dezenas, pares, repetidas_anterior, ciclo_custom, ciclo_qtd, ausentes
                    FROM concursos
                    ORDER BY numero DESC
                    LIMIT 1;
                """)
                if row:
                    data = dict(row)
                    data = self._process_dezenas(data)
                    data = self._process_numeric_fields(data)
                    # Formatar data para dd-mm-yy se for um objeto date/datetime
                    if isinstance(data.get("data"), (date, datetime)):
                        data["data"] = data["data"].strftime("%d-%m-%y")
                    print(f"Último concurso encontrado: {data['numero']}")
                    return data
                print("Nenhum concurso encontrado.")
                return None
        except Exception as e:
            print(f"Erro ao buscar último concurso: {e}")
            raise

    async def get_concurso_por_numero(self, numero: int) -> Optional[Dict[str, Any]]:
        """Busca um concurso específico pelo número."""
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                print(f"Buscando concurso {numero}...")
                row = await conn.fetchrow("""
                    SELECT numero, data, dezenas, soma_dezenas, pares, repetidas_anterior, ciclo_custom, ciclo_qtd, ausentes
                    FROM concursos
                    WHERE numero = $1;
                """, numero)
                if row:
                    data = dict(row)
                    data = self._process_dezenas(data)
                    data = self._process_numeric_fields(data)
                    # Formatar data para dd-mm-yy se for um objeto date/datetime
                    if isinstance(data.get("data"), (date, datetime)):
                        data["data"] = data["data"].strftime("%d-%m-%y")
                    print(f"Concurso {numero} encontrado.")
                    return data
                print(f"Concurso {numero} não encontrado.")
                return None
        except Exception as e:
            print(f"Erro ao buscar concurso {numero}: {e}")
            raise

    async def get_ultimos_concursos(self, qtd: int) -> List[Dict[str, Any]]:
        """Retorna os N últimos concursos."""
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                print(f"Buscando os últimos {qtd} concursos...")
                rows = await conn.fetch("""
                    SELECT numero, data, dezenas, soma_dezenas, pares, repetidas_anterior, ciclo_custom, ciclo_qtd, ausentes
                    FROM concursos
                    ORDER BY numero DESC
                    LIMIT $1;
                """, qtd)
                concursos = []
                for row in rows:
                    data = dict(row)
                    data = self._process_dezenas(data)
                    data = self._process_numeric_fields(data)
                    # Formatar data para dd-mm-yy se for um objeto date/datetime
                    if isinstance(data.get("data"), (date, datetime)):
                        data["data"] = data["data"].strftime("%d-%m-%y")
                    concursos.append(data)
                print(f"{len(concursos)} concursos encontrados.")
                return concursos
        except Exception as e:
            print(f"Erro ao buscar últimos {qtd} concursos: {e}")
            raise

    async def inserir_ou_atualizar_concurso(self, concurso_data: Dict[str, Any]) -> bool:
        """
        Insere um novo concurso ou atualiza um existente.
        Ajustado para aceitar data no formato dd-mm-yy.
        """
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                numero = concurso_data["numero"]
                data_str = concurso_data.get("data")
                dezenas = json.dumps(concurso_data.get("dezenas", []))
                soma_dezenas = concurso_data.get("soma_dezenas", 0)
                pares = concurso_data.get("pares", 0)
                repetidas_anterior = concurso_data.get("repetidas_anterior", 0)
                ciclo_custom = concurso_data.get("ciclo_custom")
                ciclo_qtd = concurso_data.get("ciclo_qtd", 0)
                ausentes = concurso_data.get("ausentes", 0)

                # Converter data de dd-mm-yy para objeto date
                data_obj = None
                if data_str:
                    try:
                        data_obj = datetime.strptime(data_str, "%d-%m-%y").date()
                    except ValueError:
                        print(f"⚠️ Formato de data inválido para concurso {numero}: {data_str}. Esperado dd-mm-yy.")
                        # Se a data for inválida, tentamos continuar sem ela ou com None
                        data_obj = None # Ou raise ValueError("...")

                print(f"Inserindo/Atualizando concurso {numero}...")
                await conn.execute("""
                    INSERT INTO concursos (numero, data, dezenas, soma_dezenas, pares, repetidas_anterior, ciclo_custom, ciclo_qtd, ausentes)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (numero) DO UPDATE SET
                        data = EXCLUDED.data,
                        dezenas = EXCLUDED.dezenas,
                        soma_dezenas = EXCLUDED.soma_dezenas,
                        pares = EXCLUDED.pares,
                        repetidas_anterior = EXCLUDED.repetidas_anterior,
                        ciclo_custom = EXCLUDED.ciclo_custom,
                        ciclo_qtd = EXCLUDED.ciclo_qtd,
                        ausentes = EXCLUDED.ausentes;
                """,
                numero,
                data_obj, # Passa o objeto date
                dezenas,
                soma_dezenas,
                pares,
                repetidas_anterior,
                ciclo_custom,
                ciclo_qtd,
                ausentes
                )
                print(f"Concurso {numero} inserido/atualizado com sucesso.")
                return True
        except Exception as e:
            print(f"Erro ao inserir/atualizar concurso {concurso_data.get('numero')}: {e}")
            raise

    # ============================================================================
    # MÉTODOS PARA JOGOS GERADOS
    # ============================================================================

    async def salvar_jogos_gerados(
        self,
        concurso_alvo: int,
        quantidade_jogos: int,
        jogos: List[List[int]], # Lista de listas de inteiros
        custo_total: float,
        concursos_base_analise: List[int], # Lista de números de concursos
        pesos_ia_utilizados: Dict[str, float],
    ) -> Optional[str]:
        """
        Salva um lote de jogos gerados pela IA no banco de dados.
        Retorna o ID do lote gerado.
        """
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                print(f"Salvando {quantidade_jogos} jogos para o concurso {concurso_alvo}...")
                row = await conn.fetchrow("""
                    INSERT INTO jogos_gerados (
                        concurso_alvo,
                        quantidade_jogos,
                        jogos,
                        custo_total,
                        concursos_base_analise,
                        pesos_ia_utilizados,
                        data_geracao,
                        status_conferencia
                    ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), 'pendente')
                    RETURNING id;
                """,
                concurso_alvo,
                quantidade_jogos,
                json.dumps(jogos),  # Armazenar jogos como JSONB
                custo_total,
                json.dumps(concursos_base_analise),  # Armazenar como JSONB
                json.dumps(pesos_ia_utilizados),  # Armazenar como JSONB
                )
                if row:
                    print(f"Jogos salvos com sucesso! ID do lote: {row['id']}")
                    return str(row["id"])
                raise Exception("Falha ao obter ID do lote de jogos gerados.")
        except Exception as e:
            print(f"Erro ao salvar jogos gerados: {e}")
            raise

    async def get_jogos_gerados_para_concurso(self, concurso_alvo: int) -> Optional[Dict[str, Any]]:
        """
        Busca o último lote de jogos gerados para um concurso específico
        que ainda não foi conferido.
        """
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                print(f"Buscando jogos gerados para o concurso {concurso_alvo} (status: pendente)...")
                row = await conn.fetchrow("""
                    SELECT
                        id,
                        concurso_alvo,
                        quantidade_jogos,
                        jogos,
                        custo_total,
                        concursos_base_analise,
                        pesos_ia_utilizados,
                        data_geracao,
                        status_conferencia
                    FROM jogos_gerados
                    WHERE concurso_alvo = $1 AND status_conferencia = 'pendente'
                    ORDER BY data_geracao DESC
                    LIMIT 1;
                """, concurso_alvo)
                if row:
                    data = dict(row)
                    data["jogos"] = json.loads(data["jogos"])  # Decodificar JSONB de volta para lista
                    # concursos_base_analise e pesos_ia_utilizados também são JSONB
                    if 'concursos_base_analise' in data and isinstance(data['concursos_base_analise'], str):
                        data['concursos_base_analise'] = json.loads(data['concursos_base_analise'])
                    if 'pesos_ia_utilizados' in data and isinstance(data['pesos_ia_utilizados'], str):
                        data['pesos_ia_utilizados'] = json.loads(data['pesos_ia_utilizados'])
                    print(f"Lote de jogos {data['id']} encontrado para o concurso {concurso_alvo}.")
                    return data
                print(f"Nenhum lote de jogos 'pendente' encontrado para o concurso {concurso_alvo}.")
                return None
        except Exception as e:
            print(f"Erro ao buscar jogos gerados para concurso {concurso_alvo}: {e}")
            raise

    # ============================================================================
    # MÉTODOS PARA RESULTADOS DA CONFERÊNCIA
    # ============================================================================

    async def salvar_resultado_conferencia(
        self,
        numero_concurso: int,
        jogos_gerados_id: str,
        resultado_oficial: Dict[str, Any],  # JSONB (OBRIGATÓRIO/NOT NULL)
        resumo: Dict[str, Any],  # JSONB (OBRIGATÓRIO/NOT NULL)
        total_jogos: int,
        acertos_por_jogo: List[int],  # JSONB
        distribuicao_acertos: Dict[str, int],  # JSONB
        premio_total: float,
        lucro: float,
        # total_gasto foi removido, conforme documentação
    ) -> bool:
        """
        Salva o resultado da conferência de um concurso.
        Usa ON CONFLICT para atualizar se já existir.
        Ajustado para não usar 'total_gasto' e garantir JSONs obrigatórios.
        """
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                print(f"Salvando resultado da conferência para concurso {numero_concurso} (lote {jogos_gerados_id})...")
                await conn.execute("""
                    INSERT INTO resultados_conferencia (
                        numero_concurso,
                        jogos_gerados_id,
                        resultado_oficial,
                        resumo,
                        total_jogos,
                        acertos_por_jogo,
                        distribuicao_acertos,
                        premio_total,
                        lucro,
                        data_conferencia
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    ON CONFLICT (numero_concurso) DO UPDATE SET
                        jogos_gerados_id = EXCLUDED.jogos_gerados_id,
                        resultado_oficial = EXCLUDED.resultado_oficial,
                        resumo = EXCLUDED.resumo,
                        total_jogos = EXCLUDED.total_jogos,
                        acertos_por_jogo = EXCLUDED.acertos_por_jogo,
                        distribuicao_acertos = EXCLUDED.distribuicao_acertos,
                        premio_total = EXCLUDED.premio_total,
                        lucro = EXCLUDED.lucro,
                        data_conferencia = NOW();
                """,
                numero_concurso,
                jogos_gerados_id,
                json.dumps(resultado_oficial, default=self._json_serial), # Converte datetime/date
                json.dumps(resumo, default=self._json_serial), # Converte datetime/date
                total_jogos,
                json.dumps(acertos_por_jogo),
                json.dumps(distribuicao_acertos),
                premio_total,
                lucro
                )
                print(f"Resultado da conferência para concurso {numero_concurso} salvo/atualizado no banco.")
                return True
        except Exception as e:
            print(f"Erro ao salvar resultado da conferência: {e}")
            return False

    async def atualizar_status_conferencia(self, jogos_gerados_id: str, status: str) -> bool:
        """
        Atualiza o status de conferência de um lote de jogos gerados.
        Ajustado para usar jogos_gerados_id em vez de concurso_alvo.
        """
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                print(f"Atualizando status de conferência para lote {jogos_gerados_id} para '{status}'...")
                await conn.execute("""
                    UPDATE jogos_gerados
                    SET status_conferencia = $1
                    WHERE id = $2;
                """, status, jogos_gerados_id) # Usa o ID do lote
                print(f"Status de conferência para lote {jogos_gerados_id} atualizado.")
                return True
        except Exception as e:
            print(f"Erro ao atualizar status de conferência para lote {jogos_gerados_id}: {e}")
            return False

    # ============================================================================
    # MÉTODOS PARA PESOS DA IA
    # ============================================================================

    async def get_pesos_ia_atuais(self) -> Dict[str, Any]:
        """
        Retorna os pesos mais recentes da IA (versão ativa).
        Se não houver, retorna pesos padrão (versão 1).
        """
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                print("Buscando pesos da IA ativos...")
                row = await conn.fetchrow("""
                    SELECT versao, pesos, ativo, motivo, data_criacao
                    FROM pesos_ia
                    WHERE ativo = TRUE
                    ORDER BY versao DESC
                    LIMIT 1;
                """)
                if row:
                    print(f"Pesos da IA versão {row['versao']} encontrados.")
                    return {
                        "versao": row["versao"],
                        "pesos": row["pesos"],
                        "ativo": row["ativo"],
                        "data_criacao": row["data_criacao"].isoformat() if row["data_criacao"] else ""
                    }
                print("Nenhum peso da IA ativo encontrado. Retornando pesos padrão.")
                # Pesos padrão (versão 1)
                return {
                    "versao": 1,
                    "pesos": {
                        "repetidas": 0.25,
                        "ausentes": 0.15,
                        "frequencia_10": 0.20,
                        "soma": 0.15,
                        "pares": 0.10,
                        "duques": 0.10,
                        "primos_fib_mult3": 0.05
                    },
                    "ativo": True,
                    "data_criacao": ""
                }
        except Exception as e:
            print(f"Erro ao buscar pesos da IA: {e}")
            return {
                "versao": 1,
                "pesos": {
                    "repetidas": 0.25,
                    "ausentes": 0.15,
                    "frequencia_10": 0.20,
                    "soma": 0.15,
                    "pares": 0.10,
                    "duques": 0.10,
                    "primos_fib_mult3": 0.05
                },
                "ativo": True,
                "data_criacao": ""
            }

    async def salvar_novos_pesos_ia(self, pesos: Dict[str, float], motivo: str = "") -> int:
        """
        Salva uma nova versão de pesos da IA.
        Desativa versões anteriores e ativa a nova.
        Retorna o número da nova versão.
        """
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                print("Desativando pesos da IA anteriores...")
                await conn.execute("""
                    UPDATE pesos_ia
                    SET ativo = FALSE;
                """)
                row = await conn.fetchrow("""
                    SELECT COALESCE(MAX(versao), 0) + 1 AS nova_versao
                    FROM pesos_ia;
                """)
                nova_versao = row["nova_versao"]
                print(f"Salvando nova versão de pesos da IA (versão {nova_versao})...")
                await conn.execute("""
                    INSERT INTO pesos_ia (versao, pesos, ativo, motivo, data_criacao)
                    VALUES ($1, $2, TRUE, $3, NOW());
                """,
                nova_versao,
                json.dumps(pesos),
                motivo
                )
                print(f"Nova versão de pesos da IA {nova_versao} salva com sucesso!")
                return nova_versao
        except Exception as e:
            print(f"Erro ao salvar novos pesos da IA: {e}")
            raise

