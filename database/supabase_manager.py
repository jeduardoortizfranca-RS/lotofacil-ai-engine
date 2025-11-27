"""
Gerenciador de conexão com Supabase
Autor: Inner AI + Jose Eduardo França
Data: Novembro 2025
"""

import logging
from typing import List, Dict, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class SupabaseManager:
    """
    Gerenciador de conexão com Supabase
    
    Nota: Esta é uma versão simplificada que funciona em modo offline.
    Para conectar ao Supabase real, instale: pip install supabase
    """
    
    def __init__(self, url: str, key: str):
        """
        Inicializa conexão com Supabase
        
        Args:
            url: URL do projeto Supabase
            key: Chave de API do Supabase
        """
        self.url = url
        self.key = key
        self.modo_offline = True
        
        try:
            from supabase import create_client, Client
            self.client: Client = create_client(url, key)
            self.modo_offline = False
            logger.info("✅ Supabase Manager conectado (modo online)")
        except ImportError:
            logger.warning("⚠️ Biblioteca Supabase não instalada. Usando modo offline.")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Erro ao conectar Supabase: {e}. Usando modo offline.")
            self.client = None
    
    def get_ultimos_concursos(self, limite: int = 500) -> Dict[int, List[int]]:
        """Retorna últimos concursos do banco"""
        if self.modo_offline:
            logger.info(f"Modo offline: buscando concursos do arquivo local")
            try:
                with open("data/concursos_historico.json", 'r') as f:
                    data = json.load(f)
                    return {int(k): v for k, v in list(data.items())[-limite:]}
            except FileNotFoundError:
                logger.warning("Arquivo de histórico não encontrado")
                return {}
        
        try:
            response = self.client.table('concursos').select('*').order('numero', desc=True).limit(limite).execute()
            historico = {}
            for row in response.data:
                historico[row['numero']] = row['dezenas']
            logger.info(f"✅ {len(historico)} concursos carregados do Supabase")
            return historico
        except Exception as e:
            logger.error(f"Erro ao buscar concursos: {e}")
            return {}
    
    def salvar_jogo_gerado(self, concurso_alvo: int, jogo: List[int], metadata: Dict, algoritmo: str):
        """Salva jogo gerado no banco"""
        if self.modo_offline:
            logger.info(f"Modo offline: jogo salvo localmente")
            self._salvar_jogo_local(concurso_alvo, jogo, metadata, algoritmo)
            return
        
        try:
            data = {
                'concurso_alvo': concurso_alvo,
                'dezenas': jogo,
                'algoritmo': algoritmo,
                'confianca': metadata.get('confianca', 0.0),
                'evento_raro': metadata.get('evento_raro', False),
                'tipo_raro': metadata.get('tipo_raro'),
                'validacao': metadata.get('validacao', {}),
                'data_geracao': datetime.now().isoformat(),
                'acertos': None
            }
            response = self.client.table('jogos_gerados').insert(data).execute()
            logger.info(f"✅ Jogo salvo no Supabase (ID: {response.data[0]['id']})")
        except Exception as e:
            logger.error(f"Erro ao salvar jogo: {e}")
            self._salvar_jogo_local(concurso_alvo, jogo, metadata, algoritmo)
    
    def salvar_concurso(self, concurso: int, resultado: List[int]):
        """Salva resultado de concurso"""
        if self.modo_offline:
            logger.info(f"Modo offline: concurso {concurso} salvo localmente")
            self._salvar_concurso_local(concurso, resultado)
            return
        
        try:
            data = {
                'numero': concurso,
                'dezenas': resultado,
                'data_sorteio': datetime.now().isoformat()
            }
            response = self.client.table('concursos').upsert(data).execute()
            logger.info(f"✅ Concurso {concurso} salvo no Supabase")
        except Exception as e:
            logger.error(f"Erro ao salvar concurso: {e}")
            self._salvar_concurso_local(concurso, resultado)
    
    def get_jogos_por_concurso(self, concurso: int) -> List[Dict]:
        """Retorna jogos gerados para um concurso específico"""
        if self.modo_offline:
            logger.info(f"Modo offline: buscando jogos do arquivo local")
            return self._carregar_jogos_local(concurso)
        
        try:
            response = self.client.table('jogos_gerados').select('*').eq('concurso_alvo', concurso).execute()
            logger.info(f"✅ {len(response.data)} jogos encontrados para concurso {concurso}")
            return response.data
        except Exception as e:
            logger.error(f"Erro ao buscar jogos: {e}")
            return []
    
    def atualizar_acertos(self, jogo_id: int, acertos: int):
        """Atualiza quantidade de acertos de um jogo"""
        if self.modo_offline:
            logger.info(f"Modo offline: acertos não atualizados (ID: {jogo_id})")
            return
        
        try:
            response = self.client.table('jogos_gerados').update({'acertos': acertos}).eq('id', jogo_id).execute()
            logger.info(f"✅ Jogo {jogo_id}: {acertos} acertos registrados")
        except Exception as e:
            logger.error(f"Erro ao atualizar acertos: {e}")
    
    def salvar_evento_raro(self, concurso: int, tipo: str, resultado: List[int]):
        """Salva evento raro detectado"""
        if self.modo_offline:
            logger.info(f"Modo offline: evento raro salvo localmente")
            self._salvar_evento_local(concurso, tipo, resultado)
            return
        
        try:
            data = {
                'concurso': concurso,
                'tipo': tipo,
                'dezenas': resultado,
                'data_deteccao': datetime.now().isoformat()
            }
            response = self.client.table('eventos_raros').insert(data).execute()
            logger.info(f"✅ Evento raro salvo: {tipo}")
        except Exception as e:
            logger.error(f"Erro ao salvar evento raro: {e}")
            self._salvar_evento_local(concurso, tipo, resultado)
    
    def _salvar_jogo_local(self, concurso: int, jogo: List[int], metadata: Dict, algoritmo: str):
        """Salva jogo em arquivo JSON local"""
        try:
            import os
            os.makedirs("data/jogos", exist_ok=True)
            filename = f"data/jogos/c{concurso}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'concurso_alvo': concurso,
                    'jogo': jogo,
                    'algoritmo': algoritmo,
                    'metadata': metadata,
                    'data_geracao': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar jogo local: {e}")
    
    def _salvar_concurso_local(self, concurso: int, resultado: List[int]):
        """Salva concurso em arquivo JSON local"""
        try:
            import os
            os.makedirs("data", exist_ok=True)
            try:
                with open("data/concursos_historico.json", 'r') as f:
                    historico = json.load(f)
            except FileNotFoundError:
                historico = {}
            historico[str(concurso)] = resultado
            with open("data/concursos_historico.json", 'w', encoding='utf-8') as f:
                json.dump(historico, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Concurso {concurso} salvo localmente")
        except Exception as e:
            logger.error(f"Erro ao salvar concurso local: {e}")
    
    def _carregar_jogos_local(self, concurso: int) -> List[Dict]:
        """Carrega jogos de arquivo JSON local"""
        try:
            import os
            import glob
            pattern = f"data/jogos/c{concurso}_*.json"
            arquivos = glob.glob(pattern)
            jogos = []
            for arquivo in arquivos:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    jogos.append(json.load(f))
            return jogos
        except Exception as e:
            logger.error(f"Erro ao carregar jogos locais: {e}")
            return []
    
    def _salvar_evento_local(self, concurso: int, tipo: str, resultado: List[int]):
        """Salva evento raro em arquivo JSON local"""
        try:
            import os
            os.makedirs("data", exist_ok=True)
            try:
                with open("data/eventos_raros.json", 'r') as f:
                    eventos = json.load(f)
            except FileNotFoundError:
                eventos = []
            eventos.append({
                'concurso': concurso,
                'tipo': tipo,
                'resultado': resultado,
                'data': datetime.now().isoformat()
            })
            with open("data/eventos_raros.json", 'w', encoding='utf-8') as f:
                json.dump(eventos, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Evento raro salvo localmente")
        except Exception as e:
            logger.error(f"Erro ao salvar evento local: {e}")
