"""
Importador de Histórico Lotofácil - CSV COMPLETO para Supabase

Formato esperado: Concurso;Data;bola 1;...;bola 15
"""

import asyncio
import asyncpg
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
import sys
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(__file__))
from config_supabase import SUPABASE_DB_URL

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
CENTRO = {7, 8, 9, 12, 13, 14, 17, 18, 19}


async def limpar_tabelas(conn: asyncpg.Connection):
    """Apaga concursos, frequencias, padroes_gerais e jogos_gerados."""
    logger.info("🧹 Limpando dados existentes...")
    await conn.execute("DELETE FROM jogos_gerados")
    await conn.execute("DELETE FROM padroes_gerais")
    await conn.execute("DELETE FROM frequencias")
    await conn.execute("DELETE FROM concursos")
    await conn.execute(
        """
        INSERT INTO frequencias (dezena, ocorrencias, ultima_aparicao)
        SELECT generate_series(1, 25), 0, NULL
        ON CONFLICT (dezena) DO NOTHING
        """
    )
    logger.info("✅ Tabelas limpas.\n")


async def importar_csv_completo(caminho_csv: Path, db_url: str):
    """Importa TODO o histórico a partir do CSV completo."""
    if not caminho_csv.exists():
        print(f"❌ Arquivo não encontrado: {caminho_csv}")
        return

    print(f"📂 Lendo arquivo: {caminho_csv}\n")

    conn = await asyncpg.connect(db_url)
    print("✅ Conectado ao Supabase\n")

    try:
        await limpar_tabelas(conn)

        total_linhas = 0
        importados = 0
        erros = 0

        with open(caminho_csv, "r", encoding="utf-8") as f:
            sample = f.read(1024)
            f.seek(0)
            delimiter = ";" if sample.count(";") > sample.count(",") else ","
            logger.info(f"🔍 Delimitador: '{delimiter}'")

            reader = csv.reader(f, delimiter=delimiter)
            header = next(reader, None)
            if header:
                logger.info(f"📋 Colunas: {len(header)}\n")

            for row in reader:
                total_linhas += 1
                if not row or all(not c.strip() for c in row):
                    continue

                try:
                    if len(row) < 17:
                        erros += 1
                        continue

                    concurso_str = row[0].strip()
                    data_str = row[1].strip()

                    if not concurso_str.isdigit():
                        erros += 1
                        continue

                    numero = int(concurso_str)

                    try:
                        data_concurso = datetime.strptime(data_str, "%d/%m/%Y").date()
                    except ValueError:
                        erros += 1
                        continue

                    dezenas_raw = row[2:17]
                    dezenas = []
                    for d_str in dezenas_raw:
                        d_str = d_str.strip()
                        if not d_str.isdigit():
                            raise ValueError(f"dezena não numérica: '{d_str}'")
                        d_int = int(d_str)
                        if d_int < 1 or d_int > 25:
                            raise ValueError(f"dezena fora do intervalo: {d_int}")
                        dezenas.append(d_int)

                    if len(dezenas) != 15 or len(set(dezenas)) != 15:
                        raise ValueError("dezenas inválidas")

                    dezenas_sorted = sorted(dezenas)
                    soma = sum(dezenas_sorted)
                    pares = sum(1 for d in dezenas_sorted if d % 2 == 0)
                    impares = 15 - pares
                    primos = sum(1 for d in dezenas_sorted if d in PRIMOS)
                    fibonacci = sum(1 for d in dezenas_sorted if d in FIBONACCI)
                    moldura = sum(1 for d in dezenas_sorted if d in MOLDURA)
                    centro = sum(1 for d in dezenas_sorted if d in CENTRO)

                    repetidas_anterior = 0
                    if numero > 1:
                        anterior = await conn.fetchrow(
                            "SELECT dezenas FROM concursos WHERE numero = $1",
                            numero - 1,
                        )
                        if anterior:
                            dezenas_anteriores = set(json.loads(anterior["dezenas"]))
                            repetidas_anterior = len(set(dezenas_sorted) & dezenas_anteriores)

                    dezenas_json = json.dumps(dezenas_sorted)

                    await conn.execute(
                        """
                        INSERT INTO concursos
                        (numero, data, dezenas, soma_dezenas, pares, impares,
                         primos, fibonacci, repetidas_anterior, moldura, centro)
                        VALUES
                        ($1, $2, $3::jsonb, $4, $5, $6, $7, $8, $9, $10, $11)
                        """,
                        numero, data_concurso, dezenas_json, soma, pares, impares,
                        primos, fibonacci, repetidas_anterior, moldura, centro,
                    )

                    importados += 1
                    if importados % 200 == 0:
                        logger.info(f"📈 {importados} concursos importados...")

                except Exception as e:
                    erros += 1
                    continue

        print("\n=== RESUMO IMPORTAÇÃO ===")
        print(f"Linhas lidas: {total_linhas}")
        print(f"Concursos importados: {importados}")
        print(f"Linhas com erro: {erros}")

        await recalcular_frequencias_e_padroes(conn)

    finally:
        await conn.close()
        print("\n🔌 Conexão fechada.")


async def recalcular_frequencias_e_padroes(conn: asyncpg.Connection):
    """Recalcula frequências e padrões."""
    logger.info("\n🔄 Recalculando frequências...")

    for dezena in range(1, 26):
        count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM concursos c, jsonb_array_elements(c.dezenas) AS d
            WHERE d::int = $1
            """,
            dezena,
        )
        ultima = await conn.fetchval(
            """
            SELECT MAX(c.numero)
            FROM concursos c, jsonb_array_elements(c.dezenas) AS d
            WHERE d::int = $1
            """,
            dezena,
        )
        await conn.execute(
            """
            UPDATE frequencias
            SET ocorrencias = $1, ultima_aparicao = $2, updated_at = NOW()
            WHERE dezena = $3
            """,
            count, ultima, dezena,
        )

    freq_data = await conn.fetch(
        "SELECT dezena, ocorrencias FROM frequencias ORDER BY ocorrencias DESC, dezena"
    )
    dezenas_ordenadas = [row["dezena"] for row in freq_data]
    dezenas_quentes = dezenas_ordenadas[:15]
    dezenas_frias = dezenas_ordenadas[-5:]

    await conn.execute(
        """
        INSERT INTO padroes_gerais (tipo, valor, updated_at)
        VALUES ('dezenas_quentes', $1::jsonb, NOW())
        ON CONFLICT (tipo) DO UPDATE SET valor = EXCLUDED.valor, updated_at = NOW()
        """,
        json.dumps(dezenas_quentes),
    )
    await conn.execute(
        """
        INSERT INTO padroes_gerais (tipo, valor, updated_at)
        VALUES ('dezenas_frias', $1::jsonb, NOW())
        ON CONFLICT (tipo) DO UPDATE SET valor = EXCLUDED.valor, updated_at = NOW()
        """,
        json.dumps(dezenas_frias),
    )

    total = await conn.fetchval("SELECT COUNT(*) FROM concursos")
    avg_soma = await conn.fetchval("SELECT AVG(soma_dezenas)::numeric(5,1) FROM concursos")
    avg_pares = await conn.fetchval("SELECT AVG(pares)::numeric(3,1) FROM concursos")
    avg_repet = await conn.fetchval(
        "SELECT AVG(repetidas_anterior)::numeric(3,1) FROM concursos WHERE repetidas_anterior > 0"
    )

    logger.info("\n📊 ESTATÍSTICAS FINAIS:")
    logger.info(f"   Total concursos: {total}")
    logger.info(f"   Soma média: {avg_soma}")
    logger.info(f"   Pares médios: {avg_pares}")
    logger.info(f"   Repetições médias: {avg_repet}")


async def main():
    print("=== IMPORTADOR HISTÓRICO LOTOFÁCIL (CSV COMPLETO) ===\n")
    csv_path = Path("data/historico_concursos_completo.csv")
    if not csv_path.exists():
        print(f"❌ Arquivo não encontrado: {csv_path.resolve()}")
        return
    await importar_csv_completo(csv_path, SUPABASE_DB_URL)


if __name__ == "__main__":
    asyncio.run(main())
