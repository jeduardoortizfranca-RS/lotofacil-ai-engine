import json
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MazusoftAnalyzer:
    def __init__(self, data_path: str = "data/mazusoft_data.json"):
        self.data_path = data_path
        self.data: Dict[str, Any] = {}
        self.is_loaded = False
        logger.info(f"MazusoftAnalyzer inicializado com data_path: {self.data_path}")

    async def _carregar_dados(self): # <-- AGORA É ASYNC DEF
        """Carrega os dados do arquivo JSON do Mazusoft."""
        if self.is_loaded:
            logger.debug("Dados do Mazusoft ja carregados. Pulando carregamento.")
            return

        if not os.path.exists(self.data_path):
            logger.warning(f"Arquivo de dados do Mazusoft nao encontrado em: {self.data_path}. Criando arquivo vazio.")
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            self.data = {}
            self.is_loaded = True
            return

        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.is_loaded = True
            logger.info(f"Dados do Mazusoft carregados com sucesso de: {self.data_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON do arquivo {self.data_path}: {e}. O arquivo pode estar corrompido ou vazio.")
            self.data = {} # Garante que self.data seja um dicionario vazio em caso de erro
            self.is_loaded = False
            raise # Re-levanta o erro para ser tratado externamente
        except Exception as e:
            logger.error(f"Erro inesperado ao carregar dados do Mazusoft de {self.data_path}: {e}")
            self.data = {}
            self.is_loaded = False
            raise

    def analisar_jogo(self, jogo: List[int]) -> Dict[str, Any]:
        """Realiza a analise de um jogo com base nos dados do Mazusoft."""
        if not self.is_loaded:
            logger.warning("Dados do Mazusoft nao carregados. Nao e possivel analisar o jogo.")
            return {"padroes": {}, "tendencias": {}, "analise_mazusoft_habilitada": False}

        # Exemplo de analise (substitua pela logica real do Mazusoft)
        analise = {
            "padroes": {
                "soma_dezenas": sum(jogo),
                "dezenas_impares": len([d for d in jogo if d % 2 != 0]),
                "dezenas_pares": len([d for d in jogo if d % 2 == 0]),
            },
            "tendencias": {
                "frequencia_passada": {d: self.data.get(str(d), 0) for d in jogo}
            },
            "analise_mazusoft_habilitada": True
        }
        logger.debug(f"Analise Mazusoft para jogo {jogo}: {analise}")
        return analise

    def atualizar_com_resultado(self, resultado: List[int]):
        """Atualiza os dados do Mazusoft com um novo resultado de concurso."""
        if not self.is_loaded:
            logger.warning("Dados do Mazusoft nao carregados. Nao e possivel atualizar com o resultado.")
            return

        # Exemplo de atualizacao (substitua pela logica real do Mazusoft)
        for dezena in resultado:
            self.data[str(dezena)] = self.data.get(str(dezena), 0) + 1

        try:
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info(f"Dados do Mazusoft atualizados e salvos em: {self.data_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar dados atualizados do Mazusoft em {self.data_path}: {e}")

