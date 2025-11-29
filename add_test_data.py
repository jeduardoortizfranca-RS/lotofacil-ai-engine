import asyncio
import asyncpg
import json
from datetime import date
from config_supabase import SUPABASE_DB_URL

# Dados de exemplo (concursos fictícios para teste)
CONCURSOS_TESTE = [
    {
        "numero": 3200,
        "data": date(2024, 1, 15),
        "dezenas": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    },
    {
        "numero": 3201,
        "data": date(2024, 1, 16),
        "dezenas": [2, 4, 6, 8, 10, 11, 13, 15, 17, 19, 21, 22, 23, 24, 25]
    },
    {
        "numero": 3202,
        "data": date(2024, 1, 17),
        "dezenas": [1, 3, 5, 7, 9, 11, 12, 14, 16, 18, 20, 21, 23, 24, 25]
    }
]

async def adicionar_concursos_teste():
    print("🔄 Conectando ao Supabase...")

    try:
        conn = await asyncpg.connect(SUPABASE_DB_URL)
        print("✅ Conectado!\n")

        for concurso in CONCURSOS_TESTE:
            numero = concurso["numero"]
            data_sorteio = concurso["data"]
            dezenas = concurso["dezenas"]

            # Converte a lista para JSON string
            dezenas_json = json.dumps(dezenas)

            # Calcula estatísticas
            soma = sum(dezenas)
            pares = sum(1 for d in dezenas if d % 2 == 0)
            impares = 15 - pares
            primos = sum(1 for d in dezenas if d in {2, 3, 5, 7, 11, 13, 17, 19, 23})
            fibonacci = sum(1 for d in dezenas if d in {1, 2, 3, 5, 8, 13, 21})

            moldura_set = {1,2,3,4,5,6,10,11,15,16,20,21,22,23,24,25}
            centro_set = {7,8,9,12,13,14,17,18,19}
            moldura = sum(1 for d in dezenas if d in moldura_set)
            centro = sum(1 for d in dezenas if d in centro_set)

            # Insere no banco (agora com dezenas_json como string)
            await conn.execute("""
                INSERT INTO concursos 
                (numero, data, dezenas, soma_dezenas, pares, impares, primos, fibonacci, moldura, centro)
                VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8, $9, $10)
            """, numero, data_sorteio, dezenas_json, soma, pares, impares, primos, fibonacci, moldura, centro)

            print(f"✅ Concurso {numero} adicionado ({data_sorteio})")
            print(f"   Dezenas: {dezenas[:5]}... (15 total)")
            print(f"   Soma: {soma} | Pares: {pares} | Ímpares: {impares}\n")

        # Atualiza frequências
        print("📊 Atualizando frequências...")
        for dezena in range(1, 26):
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM concursos c, jsonb_array_elements(c.dezenas) AS d
                WHERE d::int = $1
            """, dezena)

            ultima_aparicao = await conn.fetchval("""
                SELECT MAX(c.numero) FROM concursos c, jsonb_array_elements(c.dezenas) AS d
                WHERE d::int = $1
            """, dezena)

            await conn.execute("""
                UPDATE frequencias 
                SET ocorrencias = $1, ultima_aparicao = $2, updated_at = NOW()
                WHERE dezena = $3
            """, count, ultima_aparicao, dezena)

        print("✅ Frequências atualizadas!")

        # Calcula dezenas quentes e frias
        freq_data = await conn.fetch("""
            SELECT dezena, ocorrencias FROM frequencias ORDER BY ocorrencias DESC, dezena
        """)

        dezenas_ordenadas = [row["dezena"] for row in freq_data]
        dezenas_quentes = dezenas_ordenadas[:15]
        dezenas_frias = dezenas_ordenadas[-5:]

        # Converte para JSON antes de inserir
        quentes_json = json.dumps(dezenas_quentes)
        frias_json = json.dumps(dezenas_frias)

        await conn.execute("""
            INSERT INTO padroes_gerais (tipo, valor)
            VALUES ('dezenas_quentes', $1::jsonb)
            ON CONFLICT (tipo) DO UPDATE SET valor = EXCLUDED.valor, updated_at = NOW()
        """, quentes_json)

        await conn.execute("""
            INSERT INTO padroes_gerais (tipo, valor)
            VALUES ('dezenas_frias', $1::jsonb)
            ON CONFLICT (tipo) DO UPDATE SET valor = EXCLUDED.valor, updated_at = NOW()
        """, frias_json)

        print("✅ Padrões gerais atualizados!")
        print(f"   🔥 Dezenas quentes: {dezenas_quentes[:5]}...")
        print(f"   ❄️  Dezenas frias: {dezenas_frias}")

        # Verifica o resultado final
        total = await conn.fetchval("SELECT COUNT(*) FROM concursos")
        print(f"\n🎯 Total de concursos no banco: {total}")

        await conn.close()
        print("\n✅ DADOS DE TESTE ADICIONADOS COM SUCESSO!")

    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=== ADICIONANDO DADOS DE TESTE AO SUPABASE ===\n")
    asyncio.run(adicionar_concursos_teste())
    print("\n=== FIM ===")
