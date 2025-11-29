"""
Games Writer - Microserviço para salvar jogos gerados pela IA
Responsável por persistir jogos no Supabase e calcular métricas de performance.
"""
import asyncio
import asyncpg
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GamesWriter:
    """Gerencia a persistência de jogos gerados pela IA."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None
        self._initialized = False

    async def initialize(self):
        """Inicializa o pool de conexões."""
        if self._initialized:
            return
        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,
                max_size=5,
                command_timeout=60
            )
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"[GamesWriter] Conectado ao Supabase: {version.split()[0]}")
            self._initialized = True
        except Exception as e:
            logger.error(f"[GamesWriter] Erro ao conectar: {e}")
            raise

    async def close(self):
        """Fecha o pool de conexões."""
        if self.pool:
            await self.pool.close()
            logger.info("[GamesWriter] Pool fechado.")
            self._initialized = False

    async def save_games(self, games: List[Dict[str, Any]]) -> int:
        """
        Salva uma lista de jogos gerados pela IA.

        Args:
            games: Lista de dicionários com estrutura:
                {
                    "concurso_alvo": 3204,
                    "dezenas": [1, 2, 3, ..., 15],  # 15 dezenas
                    "confianca": 0.87,  # 0.0 a 1.0
                    "modo": "ia_generativa",  # ou "estatistico", "hibrido"
                    "fitness_score": 123.45,
                    "parametros": {"janela": 50, "peso_freq": 0.6, ...}  # opcional
                }

        Returns:
            Número de jogos salvos com sucesso
        """
        if not self._initialized:
            await self.initialize()

        if not games:
            logger.warning("[GamesWriter] Lista de jogos vazia")
            return 0

        saved_count = 0

        async with self.pool.acquire() as conn:
            for game in games:
                try:
                    # Validações
                    concurso_alvo = game.get("concurso_alvo")
                    dezenas = game.get("dezenas", [])
                    confianca = game.get("confianca", 0.0)
                    modo = game.get("modo", "ia_generativa")
                    fitness_score = game.get("fitness_score", 0.0)
                    parametros = game.get("parametros", {})

                    if not concurso_alvo:
                        logger.error(f"[GamesWriter] Concurso alvo ausente: {game}")
                        continue

                    if not isinstance(dezenas, list) or len(dezenas) != 15:
                        logger.error(f"[GamesWriter] Dezenas inválidas: {dezenas}")
                        continue

                    dezenas_sorted = sorted(dezenas)
                    if len(set(dezenas_sorted)) != 15 or any(d < 1 or d > 25 for d in dezenas_sorted):
                        logger.error(f"[GamesWriter] Dezenas fora do range: {dezenas_sorted}")
                        continue

                    # Converte para JSON
                    dezenas_json = json.dumps(dezenas_sorted)
                    parametros_json = json.dumps(parametros) if parametros else None

                    # Insere no banco
                    await conn.execute(
                        """
                        INSERT INTO jogos_gerados 
                        (concurso_alvo, dezenas, confianca, modo, fitness_score, parametros)
                        VALUES ($1, $2::jsonb, $3, $4, $5, $6::jsonb)
                        """,
                        concurso_alvo, dezenas_json, confianca, modo, 
                        fitness_score, parametros_json
                    )

                    saved_count += 1

                except Exception as e:
                    logger.error(f"[GamesWriter] Erro ao salvar jogo: {e}")
                    continue

        logger.info(f"[GamesWriter] ✅ {saved_count}/{len(games)} jogos salvos")
        return saved_count

    async def update_game_result(self, jogo_id: int, acertos: int) -> bool:
        """
        Atualiza o resultado de um jogo após o sorteio oficial.

        Args:
            jogo_id: ID do jogo na tabela jogos_gerados
            acertos: Número de acertos (0-15)

        Returns:
            True se atualizou com sucesso
        """
        if not self._initialized:
            await self.initialize()

        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    UPDATE jogos_gerados 
                    SET acertos = $1, resultado_verificado = true, updated_at = NOW()
                    WHERE id = $2
                    """,
                    acertos, jogo_id
                )
                logger.info(f"[GamesWriter] Jogo {jogo_id} atualizado: {acertos} acertos")
                return True
            except Exception as e:
                logger.error(f"[GamesWriter] Erro ao atualizar jogo {jogo_id}: {e}")
                return False

    async def get_performance_stats(self, concurso_alvo: Optional[int] = None) -> Dict[str, Any]:
        """
        Retorna estatísticas de performance dos jogos gerados.

        Args:
            concurso_alvo: Se informado, filtra por concurso específico

        Returns:
            Dicionário com métricas de performance
        """
        if not self._initialized:
            await self.initialize()

        async with self.pool.acquire() as conn:
            try:
                where_clause = ""
                params = []

                if concurso_alvo:
                    where_clause = "WHERE concurso_alvo = $1 AND resultado_verificado = true"
                    params.append(concurso_alvo)
                else:
                    where_clause = "WHERE resultado_verificado = true"

                # Total de jogos verificados
                total_query = f"SELECT COUNT(*) FROM jogos_gerados {where_clause}"
                total = await conn.fetchval(total_query, *params)

                if total == 0:
                    return {
                        "total_jogos": 0,
                        "media_acertos": 0.0,
                        "distribuicao": {},
                        "taxa_sucesso_12_plus": 0.0
                    }

                # Distribuição de acertos
                dist_query = f"""
                    SELECT acertos, COUNT(*) as qtd 
                    FROM jogos_gerados 
                    {where_clause}
                    GROUP BY acertos 
                    ORDER BY acertos DESC
                """
                rows = await conn.fetch(dist_query, *params)
                distribuicao = {row["acertos"]: row["qtd"] for row in rows}

                # Média de acertos
                avg_query = f"SELECT AVG(acertos)::numeric(4,2) FROM jogos_gerados {where_clause}"
                media = await conn.fetchval(avg_query, *params)

                # Taxa de sucesso (12+ pontos)
                sucesso_query = f"""
                    SELECT COUNT(*) FROM jogos_gerados 
                    {where_clause} AND acertos >= 12
                """
                sucesso = await conn.fetchval(sucesso_query, *params)
                taxa_sucesso = (sucesso / total * 100) if total > 0 else 0.0

                return {
                    "total_jogos": int(total),
                    "media_acertos": float(media) if media else 0.0,
                    "distribuicao": distribuicao,
                    "taxa_sucesso_12_plus": round(taxa_sucesso, 2),
                    "jogos_12_plus": int(sucesso)
                }

            except Exception as e:
                logger.error(f"[GamesWriter] Erro ao calcular stats: {e}")
                return {}


# --- TESTE ---
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from config_supabase import SUPABASE_DB_URL

    async def test_writer():
        logging.basicConfig(level=logging.INFO)
        writer = GamesWriter(SUPABASE_DB_URL)

        try:
            await writer.initialize()

            # Simula jogos gerados pela IA
            jogos_teste = [
                {
                    "concurso_alvo": 3204,
                    "dezenas": [1, 2, 3, 5, 7, 11, 13, 14, 16, 18, 20, 21, 23, 24, 25],
                    "confianca": 0.85,
                    "modo": "ia_generativa",
                    "fitness_score": 145.67,
                    "parametros": {"janela": 50, "peso_freq": 0.6}
                },
                {
                    "concurso_alvo": 3204,
                    "dezenas": [2, 4, 6, 8, 10, 11, 12, 15, 17, 19, 21, 22, 23, 24, 25],
                    "confianca": 0.78,
                    "modo": "hibrido",
                    "fitness_score": 132.45,
                    "parametros": {"janela": 40, "peso_freq": 0.7}
                }
            ]

            print("\n=== TESTE GAMESWRITER - SALVANDO JOGOS ===")
            saved = await writer.save_games(jogos_teste)
            print(f"✅ Jogos salvos: {saved}")

            # Testa estatísticas (sem resultados ainda)
            stats = await writer.get_performance_stats()
            print(f"\n📊 Stats gerais: {stats}")

        except Exception as e:
            print(f"❌ Erro no teste: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await writer.close()

    asyncio.run(test_writer())
