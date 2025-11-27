"""
Importador de Ciclo das Dezenas / Ausentes para Supabase

Formato esperado: data/Ciclo_das_Dezenas_Completo.csv
concurso;repetidas;soma;pares;ciclo;qtd;ausente1;ausente2;...;ausente10
"""

import asyncio
import asyncpg
import csv
import json
import logging
from pathlib import Path
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config_supabase import SUPABASE_DB_URL
except ImportError:
    print("❌ Erro: arquivo config_supabase.py não encontrado")
    sys.exit(1)


async def importar_ciclo_dezenas(caminho_csv: Path, db_url: str):
    """Importa dados de ciclo, repetidas e ausentes do CSV para a tabela concursos."""

    if not caminho_csv.exists():
        print(f"❌ Arquivo não encontrado: {caminho_csv}")
        return

    print(f"📂 Lendo arquivo de ciclo: {caminho_csv}\n")

    try:
        conn = await asyncpg.connect(db_url)
        print("✅ Conectado ao Supabase\n")
    except Exception as e:
        print(f"❌ Erro ao conectar ao Supabase: {e}")
        return

    total_linhas = 0
    atualizados = 0
    erros = 0

    try:
        with open(caminho_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")

            header = next(reader, None)
            if header:
                logger.info(f"📋 Header detectado ({len(header)} colunas): {header[:10]}...")

            for row in reader:
                total_linhas += 1

                if not row or not row[0].strip():
                    continue

                try:
                    numero_str = row[0].strip()
                    if not numero_str.isdigit():
                        raise ValueError(f"concurso inválido: '{numero_str}'")

                    numero = int(numero_str)

                    repetidas = int(row[1]) if len(row) > 1 and row[1].strip() else None
                    soma = int(row[2]) if len(row) > 2 and row[2].strip() else None
                    pares = int(row[3]) if len(row) > 3 and row[3].strip() else None
                    ciclo = int(row[4]) if len(row) > 4 and row[4].strip() else None
                    qtd = int(row[5]) if len(row) > 5 and row[5].strip() else None

                    ausentes_raw = row[6:16] if len(row) > 6 else []
                    ausentes = [
                        int(x)
                        for x in ausentes_raw
                        if x and x.strip() != ""
                    ]

                    result = await conn.execute(
                        """
                        UPDATE concursos
                        SET
                            repetidas_anterior = COALESCE($2, repetidas_anterior),
                            soma_dezenas       = COALESCE($3, soma_dezenas),
                            pares              = COALESCE($4, pares),
                            ciclo_custom       = $5,
                            ciclo_qtd          = $6,
                            ausentes           = $7::jsonb
                        WHERE numero = $1
                        """,
                        numero,
                        repetidas,
                        soma,
                        pares,
                        ciclo,
                        qtd,
                        json.dumps(ausentes),
                    )

                    if result.startswith("UPDATE") and not result.endswith(" 0"):
                        atualizados += 1
                    else:
                        logger.warning(f"⚠️ Concurso {numero} não encontrado.")

                except ValueError as ve:
                    erros += 1
                    if erros <= 10:
                        logger.error(f"❌ Erro na linha {total_linhas}: {ve}")
                    continue
                except Exception as e:
                    erros += 1
                    if erros <= 10:
                        logger.error(f"❌ Erro inesperado na linha {total_linhas}: {e}")
                    continue

        print("\n" + "="*50)
        print("=== RESUMO IMPORTAÇÃO CICLO / AUSENTES ===")
        print("="*50)
        print(f"Linhas lidas: {total_linhas}")
        print(f"Concursos atualizados: {atualizados}")
        print(f"Linhas com erro: {erros}")
        print("="*50)

    except Exception as e:
        print(f"\n❌ Erro ao processar arquivo: {e}")
    finally:
        await conn.close()
        print("\n🔌 Conexão fechada.")


async def main():
    print("\n" + "="*60)
    print("=== IMPORTADOR CICLO DAS DEZENAS / AUSENTES ===")
    print("="*60 + "\n")

    csv_path = Path("data/Ciclo_das_Dezenas_Completo.csv")

    if not csv_path.exists():
        print(f"❌ Arquivo não encontrado: {csv_path.resolve()}")
        return

    await importar_ciclo_dezenas(csv_path, SUPABASE_DB_URL)


if __name__ == "__main__":
    asyncio.run(main())
