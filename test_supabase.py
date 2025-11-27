import asyncio
import asyncpg

# Importa a configuração do Supabase
from config_supabase import SUPABASE_DB_URL

async def test_connection():
    print("🔄 Conectando ao Supabase...")
    print("   URL: " + SUPABASE_DB_URL.split('@')[1])  # Mostra só o host, não a senha

    try:
        # Tenta conectar
        conn = await asyncpg.connect(SUPABASE_DB_URL)
        print("✅ Conexão estabelecida!")

        # Testa se consegue executar um comando simples
        version = await conn.fetchval("SELECT version()")
        print(f"📋 Versão do PostgreSQL: {version.split()[0]}")

        # Verifica se as tabelas que criamos existem
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('concursos', 'frequencias', 'padroes_gerais')
        """)

        print(f"📊 Tabelas encontradas: {len(tables)}")
        for table in tables:
            print(f"   - {table['tablename']}")

        # Testa a tabela concursos (deve estar vazia por enquanto)
        count = await conn.fetchval("SELECT COUNT(*) FROM concursos")
        print(f"🎯 Concursos no banco: {count}")

        await conn.close()
        print("🔒 Conexão fechada com sucesso!")

    except Exception as e:
        print("❌ ERRO na conexão:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensagem: {str(e)}")
        print("\n💡 Possíveis causas:")
        print("   - Senha incorreta")
        print("   - URL de conexão errada")
        print("   - Supabase está offline")
        print("   - Firewall bloqueando")

if __name__ == "__main__":
    print("=== TESTE DE CONEXÃO SUPABASE - Lotofácil IA ===\n")
    asyncio.run(test_connection())
    print("\n=== FIM DO TESTE ===")
