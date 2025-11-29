"""Contest Writer - Módulo para inserir novos concursos no Supabase"""
import asyncio
import asyncpg
import json
import logging
from datetime import date
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ContestWriter:
    """Gerencia a inserção de novos concursos e atualização de estatísticas."""

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
                logger.info(f"[ContestWriter] Conectado ao Supabase: {version.split()[0]}")
            self._initialized = True
        except Exception as e:
            logger.error(f"[ContestWriter] Erro ao conectar: {e}")
            raise

    async def close(self):
        """Fecha o pool de conexões."""
        if self.pool:
            await self.pool.close()
            logger.info("[ContestWriter] Pool fechado.")
            self._initialized = False

    async def add_contest(self, numero: int, data_sorteio: date, dezenas: list) -> bool:
        """
        Adiciona um novo concurso e atualiza estatísticas.

        Args:
            numero: Número do concurso
            data_sorteio: Data do sorteio (objeto date)
            dezenas: Lista com 15 dezenas sorteadas

        Returns:
            True se inseriu com sucesso, False caso contrário
        """
        if not self._initialized:
            await self.initialize()

        # Validações
        if not isinstance(dezenas, list) or len(dezenas) != 15:
            logger.error(f"[ContestWriter] Dezenas inválidas: {dezenas}")
            return False

        dezenas_sorted = sorted(dezenas)
        if len(set(dezenas_sorted)) != 15 or any(d < 1 or d > 25 for d in dezenas_sorted):
            logger.error(f"[ContestWriter] Dezenas fora do range: {dezenas_sorted}")
            return False

        async with self.pool.acquire() as conn:
            try:
                # Verifica se já existe
                existing = await conn.fetchval(
                    "SELECT numero FROM concursos WHERE numero = $1",
                    numero
                )
                if existing:
                    logger.warning(f"[ContestWriter] Concurso {numero} já existe")
                    return False

                # Calcula estatísticas
                soma_dezenas = sum(dezenas_sorted)
                pares = sum(1 for d in dezenas_sorted if d % 2 == 0)
                impares = 15 - pares
                primos_set = {2, 3, 5, 7, 11, 13, 17, 19, 23}
                primos = sum(1 for d in dezenas_sorted if d in primos_set)
                fibonacci_set = {1, 2, 3, 5, 8, 13, 21}
                fibonacci = sum(1 for d in dezenas_sorted if d in fibonacci_set)

                moldura_set = {1,2,3,4,5,6,10,11,15,16,20,21,22,23,24,25}
                centro_set = {7,8,9,12,13,14,17,18,19}
                moldura = sum(1 for d in dezenas_sorted if d in moldura_set)
                centro = sum(1 for d in dezenas_sorted if d in centro_set)

                # Repetições do concurso anterior
                repetidas_anterior = 0
                ultimo = await conn.fetchrow(
                    "SELECT numero, dezenas FROM concursos ORDER BY numero DESC LIMIT 1"
                )
                if ultimo and ultimo["numero"] == numero - 1:
                    dezenas_anteriores = set(json.loads(ultimo["dezenas"]))
                    repetidas_anterior = len(set(dezenas_sorted) & dezenas_anteriores)

                # Converte dezenas para JSON
                dezenas_json = json.dumps(dezenas_sorted)

                # Insere o concurso
                await conn.execute(
                    """
                    INSERT INTO concursos 
                    (numero, data, dezenas, soma_dezenas, pares, impares, 
                     primos, fibonacci, repetidas_anterior, moldura, centro)
                    VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    numero, data_sorteio, dezenas_json, soma_dezenas, 
                    pares, impares, primos, fibonacci, repetidas_anterior, 
                    moldura, centro
                )

                logger.info(f"[ContestWriter] ✅ Concurso {numero} inserido!")

                # Atualiza frequências e padrões
                await self._update_frequencies(conn)
                await self._update_patterns(conn)

                return True

            except Exception as e:
                logger.error(f"[ContestWriter] Erro ao inserir concurso {numero}: {e}")
                import traceback
                traceback.print_exc()
                return False

    async def _update_frequencies(self, conn):
        """Atualiza a tabela de frequências."""
        try:
            for dezena in range(1, 26):
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) 
                    FROM concursos c, jsonb_array_elements(c.dezenas) AS d
                    WHERE d::int = $1
                    """,
                    dezena
                )

                ultima_aparicao = await conn.fetchval(
                    """
                    SELECT MAX(c.numero) 
                    FROM concursos c, jsonb_array_elements(c.dezenas) AS d
                    WHERE d::int = $1
                    """,
                    dezena
                )

                await conn.execute(
                    """
                    UPDATE frequencias 
                    SET ocorrencias = $1, ultima_aparicao = $2, updated_at = NOW()
                    WHERE dezena = $3
                    """,
                    count, ultima_aparicao, dezena
                )

            logger.info("[ContestWriter] Frequências atualizadas")
        except Exception as e:
            logger.error(f"[ContestWriter] Erro ao atualizar frequências: {e}")

    async def _update_patterns(self, conn):
        """Atualiza padrões gerais (dezenas quentes/frias)."""
        try:
            freq_data = await conn.fetch(
                "SELECT dezena, ocorrencias FROM frequencias ORDER BY ocorrencias DESC, dezena"
            )

            dezenas_ordenadas = [row["dezena"] for row in freq_data]
            dezenas_quentes = dezenas_ordenadas[:15]
            dezenas_frias = dezenas_ordenadas[-5:]

            quentes_json = json.dumps(dezenas_quentes)
            frias_json = json.dumps(dezenas_frias)

            await conn.execute(
                """
                INSERT INTO padroes_gerais (tipo, valor, updated_at) 
                VALUES ('dezenas_quentes', $1::jsonb, NOW())
                ON CONFLICT (tipo) DO UPDATE 
                SET valor = EXCLUDED.valor, updated_at = NOW()
                """,
                quentes_json
            )

            await conn.execute(
                """
                INSERT INTO padroes_gerais (tipo, valor, updated_at) 
                VALUES ('dezenas_frias', $1::jsonb, NOW())
                ON CONFLICT (tipo) DO UPDATE 
                SET valor = EXCLUDED.valor, updated_at = NOW()
                """,
                frias_json
            )

            logger.info("[ContestWriter] Padrões atualizados")
        except Exception as e:
            logger.error(f"[ContestWriter] Erro ao atualizar padrões: {e}")


# --- TESTE ---
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from config_supabase import SUPABASE_DB_URL

    async def test_writer():
        logging.basicConfig(level=logging.INFO)
        writer = ContestWriter(SUPABASE_DB_URL)

        try:
            await writer.initialize()

            # Testa inserção de um novo concurso
            novo_concurso = {
                "numero": 3203,
                "data": date(2024, 1, 18),
                "dezenas": [2, 3, 5, 8, 10, 12, 14, 16, 18, 20, 21, 22, 23, 24, 25]
            }

            print(f"\n=== TESTE CONTESTWRITER - INSERINDO CONCURSO {novo_concurso['numero']} ===")
            resultado = await writer.add_contest(
                novo_concurso["numero"],
                novo_concurso["data"],
                novo_concurso["dezenas"]
            )
            print(f"Resultado inserção: {resultado}")

        except Exception as e:
            print(f"Erro no teste: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await writer.close()

    asyncio.run(test_writer())
