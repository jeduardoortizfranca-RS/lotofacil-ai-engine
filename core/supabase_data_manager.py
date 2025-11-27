"""Lotofácil - Gerenciador Supabase"""
import asyncio
import asyncpg
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date

logger = logging.getLogger(__name__)

class SupabaseDataManager:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None
        self._initialized = False
        logger.info("SupabaseDataManager inicializado")

    async def initialize(self):
        if self._initialized:
            return
        try:
            self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=10, command_timeout=60)
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"Conexão Supabase: {version.split()[0]}")
            self._initialized = True
            logger.info("SupabaseDataManager pronto!")
        except Exception as e:
            logger.error(f"Erro ao inicializar Supabase: {e}")
            raise

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("Pool Supabase fechado")
            self._initialized = False

    async def get_total_contests(self) -> int:
        if not self._initialized:
            await self.initialize()
        async with self.pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM concursos")
            return int(count) if count is not None else 0

    async def get_last_contest(self) -> Optional[Dict[str, Any]]:
        if not self._initialized:
            await self.initialize()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT numero, data, dezenas, soma_dezenas, pares, impares, primos, fibonacci, repetidas_anterior, moldura, centro FROM concursos ORDER BY numero DESC LIMIT 1")
            if row:
                return {"numero": row["numero"], "data": row["data"], "dezenas": json.loads(row["dezenas"]), "soma_dezenas": row["soma_dezenas"], "pares": row["pares"], "impares": row["impares"], "primos": row["primos"], "fibonacci": row["fibonacci"], "repetidas_anterior": row["repetidas_anterior"], "moldura": row["moldura"], "centro": row["centro"]}
            return None

    async def get_frequency_data(self) -> Dict[int, int]:
        if not self._initialized:
            await self.initialize()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT dezena, ocorrencias FROM frequencias ORDER BY dezena")
            return {row["dezena"]: row["ocorrencias"] for row in rows}

    async def get_general_patterns(self) -> Dict[str, List[int]]:
        if not self._initialized:
            await self.initialize()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT tipo, valor FROM padroes_gerais")
            patterns = {}
            for row in rows:
                patterns[row["tipo"]] = json.loads(row["valor"])
            return patterns

    async def get_fitness_weights(self) -> Dict[str, float]:
        if not self._initialized:
            await self.initialize()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT nome, peso FROM pesos_fitness WHERE ativo = true")
            return {row["nome"]: float(row["peso"]) for row in rows}

    async def get_recent_contests(self, limit: int = 10) -> List[Dict[str, Any]]:
        if not self._initialized:
            await self.initialize()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT numero, data, dezenas, soma_dezenas, pares, impares FROM concursos ORDER BY numero DESC LIMIT $1", limit)
            return [{"numero": row["numero"], "data": row["data"], "dezenas": json.loads(row["dezenas"]), "soma_dezenas": row["soma_dezenas"], "pares": row["pares"], "impares": row["impares"]} for row in rows]

    async def get_statistics_summary(self) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()
        async with self.pool.acquire() as conn:
            total_concursos = await conn.fetchval("SELECT COUNT(*) FROM concursos")
            total_jogos = await conn.fetchval("SELECT COUNT(*) FROM jogos_gerados")
            avg_soma = await conn.fetchval("SELECT AVG(soma_dezenas)::numeric(5,1) FROM concursos")
            avg_pares = await conn.fetchval("SELECT AVG(pares)::numeric(3,1) FROM concursos")
            avg_confianca = await conn.fetchval("SELECT AVG(confianca)::numeric(4,3) FROM jogos_gerados")
            jogos_com_acertos = await conn.fetchval("SELECT COUNT(*) FROM jogos_gerados WHERE acertos >= 11")
            patterns = await self.get_general_patterns()
            return {"total_concursos": int(total_concursos) if total_concursos else 0, "total_jogos_gerados": int(total_jogos) if total_jogos else 0, "estatisticas_concursos": {"soma_media": float(avg_soma) if avg_soma else 0.0, "pares_media": float(avg_pares) if avg_pares else 0.0}, "estatisticas_jogos": {"confianca_media": float(avg_confianca) if avg_confianca else 0.0, "jogos_com_11_acertos_ou_mais": int(jogos_com_acertos) if jogos_com_acertos else 0}, "padroes_atuais": patterns, "ultima_atualizacao": datetime.now().isoformat()}

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from config_supabase import SUPABASE_DB_URL
    async def test_manager():
        logging.basicConfig(level=logging.INFO)
        manager = SupabaseDataManager(SUPABASE_DB_URL)
        try:
            await manager.initialize()
            total = await manager.get_total_contests()
            print(f"Total concursos: {total}")
            ultimo = await manager.get_last_contest()
            if ultimo:
                print(f"Ultimo: #{ultimo['numero']} - {ultimo['dezenas'][:5]}...")
            freq = await manager.get_frequency_data()
            print(f"Frequencias: {len(freq)} dezenas")
            stats = await manager.get_statistics_summary()
            print(f"Stats: {stats['total_concursos']} concursos, {stats['total_jogos_gerados']} jogos")
        except Exception as e:
            print(f"Erro: {e}")
        finally:
            await manager.close()
    asyncio.run(test_manager())
