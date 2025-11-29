import csv
import asyncio
import asyncpg
import os
from datetime import datetime
from dotenv import load_dotenv
import json # Necessário para json.loads, mesmo que não usemos agora para 'ausentes'

# Carregar variáveis de ambiente do .env
load_dotenv()

async def import_historico_completo():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Erro: DATABASE_URL não encontrada no arquivo .env")
        return

    conn = None
    try:
        conn = await asyncpg.connect(db_url)
        print("Conexão com o Supabase estabelecida com sucesso.")

        # Não vamos mais limpar a tabela aqui, Jose, para preservar dados existentes
        # e permitir a inclusão de 'ciclo_dezenas' depois.
        # print("Limpando a tabela 'concursos' para evitar duplicatas e dados corrompidos...")
        # await conn.execute("TRUNCATE TABLE concursos RESTART IDENTITY CASCADE;")
        # print("Tabela 'concursos' limpa.")

        csv_file_path = os.path.join(os.path.dirname(__file__), 'data', 'historico_concursos_completo.csv')

        if not os.path.exists(csv_file_path):
            print(f"Erro: Arquivo CSV não encontrado em {csv_file_path}")
            return

        print(f"Iniciando importação do arquivo: {csv_file_path}")

        records_to_insert = []

        with open(csv_file_path, 'r', encoding='utf-8-sig') as f: # Usar 'utf-8-sig' para lidar com BOM
            reader = csv.reader(f, delimiter=';')
            header = next(reader)  # Pular cabeçalho

            # Remover BOM se presente no primeiro cabeçalho
            if header and header[0].startswith('\ufeff'):
                header[0] = header[0][1:]

            print("Cabeçalho lido (após remoção de BOM):", header)

            # Mapear índices das colunas
            try:
                col_map = {
                    'Concurso': header.index('Concurso'),
                    'Data': header.index('Data'),
                    'bola 1': header.index('bola 1'),
                    'bola 2': header.index('bola 2'),
                    'bola 3': header.index('bola 3'),
                    'bola 4': header.index('bola 4'),
                    'bola 5': header.index('bola 5'),
                    'bola 6': header.index('bola 6'),
                    'bola 7': header.index('bola 7'),
                    'bola 8': header.index('bola 8'),
                    'bola 9': header.index('bola 9'),
                    'bola 10': header.index('bola 10'),
                    'bola 11': header.index('bola 11'),
                    'bola 12': header.index('bola 12'),
                    'bola 13': header.index('bola 13'),
                    'bola 14': header.index('bola 14'),
                    'bola 15': header.index('bola 15'),
                }
            except ValueError as e:
                print(f"Erro ao mapear cabeçalhos do CSV: {e}")
                print("Verifique se as colunas 'Concurso', 'Data', 'bola 1' a 'bola 15' existem e estão corretas.")
                return

            # Processar cada linha do CSV
            for i, row in enumerate(reader):
                if not row: # Pular linhas vazias
                    continue
                try:
                    numero = int(row[col_map['Concurso']])

                    # Tratar a data no formato dd/mm/yyyy
                    data_str = row[col_map['Data']]
                    data_sorteio = datetime.strptime(data_str, '%d/%m/%Y').date()

                    dezenas = []
                    for j in range(1, 16): # 'bola 1' a 'bola 15'
                        dezena = int(row[col_map[f'bola {j}']])
                        dezenas.append(dezena)
                    dezenas.sort() # Garantir que as dezenas estejam ordenadas

                    # Calcular soma_dezenas e pares/impares a partir das dezenas
                    soma_dezenas = sum(dezenas)
                    pares = len([d for d in dezenas if d % 2 == 0])
                    impares = len([d for d in dezenas if d % 2 != 0])

                    # As colunas 'repetidas_anterior', 'primos', 'fibonacci', 'multiplos_3',
                    # 'moldura', 'centro' não estão no seu CSV atual, mas existem no schema.
                    # Vamos inseri-las como NULL ou 0 por enquanto, se o schema permitir.
                    # Se você tiver essas informações em outro CSV, podemos fazer um UPDATE depois.
                    repetidas_anterior = None # Não temos no CSV atual
                    primos = None # Não temos no CSV atual
                    fibonacci = None # Não temos no CSV atual
                    multiplos_3 = None # Não temos no CSV atual
                    moldura = None # Não temos no CSV atual
                    centro = None # Não temos no CSV atual

                    records_to_insert.append((
                        numero,
                        dezenas,
                        data_sorteio,
                        soma_dezenas,
                        pares,
                        impares,
                        primos,
                        fibonacci,
                        multiplos_3,
                        moldura,
                        centro,
                        repetidas_anterior
                    ))
                except (ValueError, IndexError, json.JSONDecodeError) as e:
                    print(f"Erro ao processar linha {i+2} do CSV: {row}. Detalhes: {e}")
                    continue

            if not records_to_insert:
                print("Nenhum registro válido encontrado para importação.")
                return

            # Inserção em lote
            print(f"Preparando para inserir {len(records_to_insert)} registros na tabela 'concursos'...")
            # Usar INSERT INTO ON CONFLICT DO NOTHING para evitar duplicatas se o script for rodado mais de uma vez
            # e para preservar os dados que já possam ter sido inseridos.
            insert_query = """
                INSERT INTO concursos (
                    numero, dezenas_sorteadas, data_sorteio, soma_dezenas, pares, impares,
                    primos, fibonacci, multiplos_3, moldura, centro, repetidas_anterior
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                ) ON CONFLICT (numero) DO NOTHING;
            """
            await conn.executemany(insert_query, records_to_insert)
            print(f"Importação de {len(records_to_insert)} concursos concluída com sucesso (duplicatas ignoradas)!")

    except asyncpg.exceptions.PostgresError as e:
        print(f"Erro no banco de dados: {e}")
    except FileNotFoundError:
        print(f"Erro: O arquivo CSV 'historico_concursos_completo.csv' não foi encontrado no diretório backend/data.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
    finally:
        if conn:
            await conn.close()
            print("Conexão com o Supabase fechada.")

if __name__ == "__main__":
    asyncio.run(import_historico_completo())

