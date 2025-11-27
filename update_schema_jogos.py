"""Script para atualizar schema da tabela jogos_gerados"""
import asyncio
import asyncpg
import sys
import os

sys.path.append(os.path.dirname(__file__))
from config_supabase import SUPABASE_DB_URL


async def update_schema():
    print("=== ATUALIZANDO SCHEMA jogos_gerados ===\n")

    try:
        conn = await asyncpg.connect(SUPABASE_DB_URL)
        print("✅ Conectado ao Supabase\n")

        # Adiciona coluna parametros
        print("📝 Adicionando coluna 'parametros'...")
        await conn.execute("""
            ALTER TABLE jogos_gerados 
            ADD COLUMN IF NOT EXISTS parametros JSONB
        """)
        print("✅ Coluna 'parametros' adicionada\n")

        # Adiciona coluna resultado_verificado
        print("📝 Adicionando coluna 'resultado_verificado'...")
        await conn.execute("""
            ALTER TABLE jogos_gerados 
            ADD COLUMN IF NOT EXISTS resultado_verificado BOOLEAN DEFAULT false
        """)
        print("✅ Coluna 'resultado_verificado' adicionada\n")

        # Cria índice
        print("📝 Criando índice...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_jogos_resultado_verificado 
            ON jogos_gerados(resultado_verificado)
        """)
        print("✅ Índice criado\n")

        # Verifica estrutura final
        print("📊 Estrutura final da tabela jogos_gerados:")
        rows = await conn.fetch("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'jogos_gerados' 
            ORDER BY ordinal_position
        """)

        for row in rows:
            nullable = "NULL" if row["is_nullable"] == "YES" else "NOT NULL"
            print(f"   - {row['column_name']}: {row['data_type']} ({nullable})")

        await conn.close()
        print("\n✅ SCHEMA ATUALIZADO COM SUCESSO!")

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(update_schema())
