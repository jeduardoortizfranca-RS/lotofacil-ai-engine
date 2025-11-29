import csv
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

CSV_FILENAME = "Ciclo_das_Dezenas_Completo.csv"  # nome exato do arquivo na pasta data


async def import_ciclo_das_dezenas():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Erro: DATABASE_URL não encontrada no arquivo .env")
        return

    conn = None
    try:
        conn = await asyncpg.connect(db_url)
        print("Conexão com o Supabase estabelecida com sucesso.")

        csv_path = os.path.join(os.path.dirname(__file__), "data", CSV_FILENAME)

        if not os.path.exists(csv_path):
            print(f"Erro: Arquivo CSV não encontrado em {csv_path}")
            return

        print(f"Iniciando importação do arquivo de ciclo das dezenas: {csv_path}")

        updates = []

        # Abrir CSV com separador ; e tratar BOM
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f, delimiter=";")
            header = next(reader)

            # Normalizar cabeçalho (remover espaços, lower)
            header_norm = [h.strip().lower() for h in header]
            print("Cabeçalho lido:", header_norm)

            # Mapear índices esperados
            try:
                idx_concurso  = header_norm.index("concurso")
                idx_repetidas = header_norm.index("repetidas")
                idx_soma      = header_norm.index("soma")
                idx_pares     = header_norm.index("pares")
                idx_ciclo     = header_norm.index("ciclo")
                idx_qtd       = header_norm.index("qtd")

                # ausente1..ausente10
                ausente_idxs = []
                for i in range(1, 11):
                    col_name = f"ausente{i}"
                    if col_name in header_norm:
                        ausente_idxs.append(header_norm.index(col_name))
                    else:
                        print(f"Aviso: coluna '{col_name}' não encontrada no cabeçalho.")
                if not ausente_idxs:
                    print("Aviso: nenhuma coluna 'ausente1..10' encontrada. Ausentes ficarão vazios.")
            except ValueError as e:
                print(f"Erro ao mapear cabeçalhos do CSV de ciclo: {e}")
                print("Cabeçalho lido:", header_norm)
                return

            for i, row in enumerate(reader):
                if not row:
                    continue

                try:
                    # concurso
                    concurso_str = row[idx_concurso].strip()
                    if not concurso_str:
                        continue
                    numero = int(concurso_str)

                    # repetidas, soma, pares (podem estar vazios em algumas linhas)
                    def to_int_or_none(val: str):
                        val = val.strip()
                        if val == "":
                            return None
                        return int(val)

                    repetidas = to_int_or_none(row[idx_repetidas]) if idx_repetidas is not None else None
                    soma = to_int_or_none(row[idx_soma]) if idx_soma is not None else None
                    pares = to_int_or_none(row[idx_pares]) if idx_pares is not None else None

                    # ciclo (texto)
                    ciclo = row[idx_ciclo].strip() if idx_ciclo is not None and row[idx_ciclo].strip() != "" else None

                    # qtd (inteiro)
                    qtd = to_int_or_none(row[idx_qtd]) if idx_qtd is not None else None

                    # ausentes: montar lista de inteiros ignorando vazios
                    ausentes_list = []
                    for idx_a in ausente_idxs:
                        if idx_a < len(row):
                            val = row[idx_a].strip()
                            if val != "":
                                try:
                                    ausentes_list.append(int(val))
                                except ValueError:
                                    pass

                    ausentes = ausentes_list if ausentes_list else None

                    updates.append(
                        (
                            repetidas,
                            soma,
                            pares,
                            ciclo,
                            qtd,
                            ausentes,
                            numero, # O número do concurso é o último parâmetro
                        )
                    )

                except Exception as e:
                    print(f"Erro ao processar linha {i+2} do CSV: {row}. Detalhes: {e}")
                    continue

        if not updates:
            print("Nenhum registro válido para atualização foi encontrado.")
            return

        print(f"Preparando para atualizar {len(updates)} concursos com informações de ciclo...")

        update_sql = """
            UPDATE concursos
               SET repetidas_anterior = COALESCE($1, repetidas_anterior),
                   soma_dezenas       = COALESCE($2, soma_dezenas),
                   pares              = COALESCE($3, pares),
                   ciclo              = COALESCE($4, ciclo),
                   ciclo_qtd          = COALESCE($5, ciclo_qtd),
                   ausentes           = COALESCE($6, ausentes)
             WHERE numero = $7; -- CORREÇÃO AQUI: $7 para o número do concurso
        """

        await conn.executemany(update_sql, updates)

        print("Atualização de ciclo das dezenas concluída com sucesso!")

    except asyncpg.PostgresError as e:
        print(f"Erro no banco de dados: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
    finally:
        if conn:
            await conn.close()
            print("Conexão com o Supabase fechada.")


if __name__ == "__main__":
    asyncio.run(import_ciclo_das_dezenas())
