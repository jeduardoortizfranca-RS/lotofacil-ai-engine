"""
Popula a coluna data_sorteio na tabela concursos
usando o arquivo CSV: data/historico_concursos_completo.csv

Formato esperado (delimitador ';'):
Concurso;Data;bola 1;...;bola 15
3530;04/11/2025;1;2;3;...
...
"""

import asyncio
import asyncpg
import csv
from datetime import datetime, date
from pathlib import Path
import os
import sys

# Garante que conseguimos importar config_supabase.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_supabase import SUPABASE_DB_URL


ARQUIVO_CSV = Path("data/historico_concursos_completo.csv")


def converter_data_br_para_date(data_br: str) -> date:
    """
    Converte data no formato dd/mm/aaaa para objeto date do Python.
    Exemplo: "04/11/2025" -> date(2025, 11, 4)
    """
    data_br = data_br.strip()
    if not data_br:
        raise ValueError("Data vazia")

    # Converte string para datetime e depois extrai só a data
    dt = datetime.strptime(data_br, "%d/%m/%Y")
    return dt.date()  # Retorna objeto date, não string


async def popular_datas_concursos(db_url: str, caminho_csv: Path):
    if not caminho_csv.exists():
        print(f"❌ Arquivo não encontrado: {caminho_csv.resolve()}")
        return

    print("\n" + "="*60)
    print("=== POPULANDO data_sorteio A PARTIR DO CSV ===")
    print("="*60)
    print(f"📂 Lendo arquivo: {caminho_csv.resolve()}\n")

    conn = await asyncpg.connect(db_url)
    print("✅ Conectado ao Supabase\n")

    total_linhas = 0
    atualizados = 0
    ignorados = 0
    erros = 0

    try:
        with open(caminho_csv, "r", encoding="utf-8-sig") as f:  # utf-8-sig remove BOM
            reader = csv.reader(f, delimiter=";")

            # Lê cabeçalho
            header = next(reader, None)
            if header:
                # Remove BOM se existir no primeiro campo
                if header[0].startswith('\ufeff'):
                    header[0] = header[0].replace('\ufeff', '')
                print(f"📋 Header detectado ({len(header)} colunas): {header[:5]}...\n")

            for row in reader:
                total_linhas += 1

                # Ignora linhas vazias
                if not row or len(row) < 2:
                    continue

                try:
                    concurso_str = row[0].strip()
                    data_str_br = row[1].strip()

                    if not concurso_str.isdigit():
                        raise ValueError(f"Concurso inválido: '{concurso_str}'")

                    numero = int(concurso_str)
                    data_obj = converter_data_br_para_date(data_str_br)  # Agora retorna date

                    # Verifica se já existe data (não sobrescreve)
                    data_existente = await conn.fetchval(
                        "SELECT data_sorteio FROM concursos WHERE numero = $1",
                        numero,
                    )

                    if data_existente is not None:
                        ignorados += 1
                        continue

                    # Atualiza com objeto date (não string)
                    resultado = await conn.execute(
                        """
                        UPDATE concursos
                        SET data_sorteio = $2
                        WHERE numero = $1
                        """,
                        numero,
                        data_obj,  # Passa objeto date
                    )

                    if resultado.startswith("UPDATE") and not resultado.endswith(" 0"):
                        atualizados += 1
                        # Mostra alguns exemplos
                        if atualizados <= 5 or atualizados % 500 == 0:
                            print(f"Concurso {numero:4d}: data_sorteio = {data_obj} ✅")
                    else:
                        erros += 1
                        if erros <= 5:
                            print(f"⚠️ Concurso {numero}: não encontrado na tabela concursos.")

                except Exception as e:
                    erros += 1
                    if erros <= 10:
                        print(f"❌ Erro na linha {total_linhas}: {e}")
                    continue

        print("\n" + "="*50)
        print("=== RESUMO POPULAÇÃO DE DATAS (CSV) ===")
        print("="*50)
        print(f"Linhas lidas do CSV:       {total_linhas}")
        print(f"Concursos atualizados:     {atualizados}")
        print(f"Concursos já com data:     {ignorados}")
        print(f"Linhas com erro:           {erros}")
        print("="*50)

        # Checagem rápida: mostra primeiro e último concurso com data
        primeiro = await conn.fetchrow(
            """
            SELECT numero, data_sorteio
            FROM concursos
            WHERE data_sorteio IS NOT NULL
            ORDER BY numero ASC
            LIMIT 1
            """
        )

        ultimo = await conn.fetchrow(
            """
            SELECT numero, data_sorteio
            FROM concursos
            WHERE data_sorteio IS NOT NULL
            ORDER BY numero DESC
            LIMIT 1
            """
        )

        print("\n🔍 Validação rápida:")
        if primeiro:
            print(f"  Primeiro com data: concurso {primeiro['numero']}, data {primeiro['data_sorteio']}")
        if ultimo:
            print(f"  Último com data:   concurso {ultimo['numero']}, data {ultimo['data_sorteio']}")
        print()

    finally:
        await conn.close()
        print("🔌 Conexão fechada.")


async def main():
    await popular_datas_concursos(SUPABASE_DB_URL, ARQUIVO_CSV)


if __name__ == "__main__":
    asyncio.run(main())
