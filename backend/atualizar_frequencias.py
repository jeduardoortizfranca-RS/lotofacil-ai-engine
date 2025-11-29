import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


async def atualizar_frequencias():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Erro: DATABASE_URL não encontrada no .env")
        return

    conn = None
    try:
        conn = await asyncpg.connect(db_url)
        print("Conexão com Supabase estabelecida.")

        # Buscar todos os concursos com dezenas
        rows = await conn.fetch("""
            SELECT numero, dezenas_sorteadas
            FROM concursos
            ORDER BY numero ASC;
        """)

        if not rows:
            print("Nenhum concurso encontrado na tabela 'concursos'.")
            return

        print(f"Encontrados {len(rows)} concursos. Calculando frequências...")

        # Inicializar contadores para dezenas 1..25
        ocorrencias = {d: 0 for d in range(1, 26)}
        ultima_aparicao = {d: None for d in range(1, 26)}

        for row in rows:
            numero = row["numero"]
            dezenas = row["dezenas_sorteadas"] or []

            for d in dezenas:
                d_int = int(d)
                if 1 <= d_int <= 25:
                    ocorrencias[d_int] += 1
                    ultima_aparicao[d_int] = numero

        # Montar lista de updates: (ocorrencias, ultima_aparicao, dezena)
        updates = []
        for d in range(1, 26):
            updates.append(
                (
                    ocorrencias[d],
                    ultima_aparicao[d],
                    d,
                )
            )

        print("Aplicando atualização na tabela 'frequencias'...")

        update_sql = """
            UPDATE frequencias
               SET ocorrencias = $1,
                   ultima_aparicao = $2,
                   updated_at = NOW()
             WHERE dezena = $3;
        """

        await conn.executemany(update_sql, updates)

        print("Atualização de frequências concluída com sucesso.")

    except asyncpg.PostgresError as e:
        print(f"Erro no banco de dados: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        if conn:
            await conn.close()
            print("Conexão com Supabase fechada.")


if __name__ == "__main__":
    asyncio.run(atualizar_frequencias())
