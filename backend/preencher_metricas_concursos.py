import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# Conjuntos fixos para cálculo
PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
MULTIPLOS_3 = {3, 6, 9, 12, 15, 18, 21, 24}
MOLDURA = {
    1, 2, 3, 4, 5,     # primeira linha
    21, 22, 23, 24, 25, # última linha
    6, 11, 16,         # primeira coluna (exceto 1 e 21 já incluídos)
    10, 15, 20         # última coluna (exceto 5 e 25 já incluídos)
}
# Confirmar conjunto da moldura (sem duplicados)
MOLDURA = set(MOLDURA)
CENTRO = {n for n in range(1, 26) if n not in MOLDURA}


async def preencher_metricas():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Erro: DATABASE_URL não encontrada no arquivo .env")
        return

    conn = None
    try:
        conn = await asyncpg.connect(db_url)
        print("Conexão com Supabase estabelecida.")

        # Buscar todos os concursos ordenados por numero (crescente)
        rows = await conn.fetch("""
            SELECT numero, dezenas_sorteadas
            FROM concursos
            ORDER BY numero ASC;
        """)

        if not rows:
            print("Nenhum concurso encontrado na tabela 'concursos'.")
            return

        print(f"Encontrados {len(rows)} concursos. Calculando métricas...")

        # Vamos montar uma lista de updates: (primos, fibonacci, multiplos_3, moldura, centro, repetidas_anterior, numero)
        updates = []

        # Precisamos que o índice anterior exista para calcular repetidas_anterior
        prev_dezenas = None

        for idx, row in enumerate(rows):
            numero = row["numero"]
            dezenas = row["dezenas_sorteadas"]

            if not dezenas:
                print(f"Concurso {numero} sem dezenas_sorteadas, pulando.")
                continue

            # Garantir que são inteiros
            dezenas_set = {int(d) for d in dezenas}

            # Cálculos
            qtd_primos = sum(1 for d in dezenas_set if d in PRIMOS)
            qtd_fib = sum(1 for d in dezenas_set if d in FIBONACCI)
            qtd_mult3 = sum(1 for d in dezenas_set if d in MULTIPLOS_3)
            qtd_moldura = sum(1 for d in dezenas_set if d in MOLDURA)
            qtd_centro = sum(1 for d in dezenas_set if d in CENTRO)

            if prev_dezenas is None:
                # Primeiro concurso da sequência
                repetidas_anterior = 0
            else:
                repetidas_anterior = len(dezenas_set.intersection(prev_dezenas))

            updates.append(
                (
                    qtd_primos,
                    qtd_fib,
                    qtd_mult3,
                    qtd_moldura,
                    qtd_centro,
                    repetidas_anterior,
                    numero,
                )
            )

            prev_dezenas = dezenas_set

        print(f"Preparando para atualizar {len(updates)} concursos...")

        update_sql = """
            UPDATE concursos
            SET
                primos = $1,
                fibonacci = $2,
                multiplos_3 = $3,
                moldura = $4,
                centro = $5,
                repetidas_anterior = $6
            WHERE numero = $7;
        """

        await conn.executemany(update_sql, updates)

        print("Atualização concluída com sucesso.")
    except asyncpg.PostgresError as e:
        print(f"Erro no banco de dados: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        if conn:
            await conn.close()
            print("Conexão com Supabase fechada.")


if __name__ == "__main__":
    asyncio.run(preencher_metricas())
