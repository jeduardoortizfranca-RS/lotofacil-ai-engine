"""
Lotofacil AI Engine v3.0 - Módulo de Aprendizado por Reforço
Implementa Q-Learning para otimização contínua dos pesos do algoritmo
Autor: Inner AI + Jose Eduardo França
Data: Novembro 2025
"""

import json
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import os
from collections import defaultdict

logger = logging.getLogger(__name__)

class QLearningAgent:
    """
    Agente de Q-Learning para otimização adaptativa dos pesos do algoritmo

    Estados: Configurações atuais do sistema (temperatura, alerta_salto, etc.)
    Ações: Ajustes nos pesos dos critérios (freq, gap, anomalo, etc.)
    Recompensas: Baseadas em acertos (11=1pt, 12=3pt, 13=8pt, 14=20pt, 15=100pt)
    """

    def __init__(
        self,
        state_space: Dict[str, List[float]] = None,
        action_space: Dict[str, List[float]] = None,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon: float = 0.15,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.01,
        weights_file: str = "data/lotofacil_weights.json",
        q_table_file: str = "data/lotofacil_q_table.json"
    ):
        """Inicializa o agente Q-Learning"""
        logger.info("✅ Q-Learning Agent inicializado")
        logger.info(f"   Learning rate: {learning_rate}")
        logger.info(f"   Epsilon inicial: {epsilon}")
        logger.info(f"   Decay: {epsilon_decay}")

        self.state_space = state_space or {
            'temperatura': [0.0, 0.3, 0.6, 1.0],
            'alerta_salto': [0, 1],
            'media_acertos': [8, 10, 12, 14],
            'recorrencia': [0.0, 0.3, 0.6, 0.9]
        }

        self.action_space = action_space or {
            'freq': [-0.2, -0.1, 0.0, 0.1, 0.2],
            'gap': [-0.3, -0.15, 0.0, 0.15, 0.3],
            'anomalo': [-0.5, -0.25, 0.0, 0.25, 0.5],
            'break': [-0.4, -0.2, 0.0, 0.2, 0.4],
            'diversity': [-0.3, -0.15, 0.0, 0.15, 0.3],
            'consec': [-0.4, -0.2, 0.0, 0.2, 0.4],
            'primo': [-0.2, -0.1, 0.0, 0.1, 0.2],
            'fib': [-0.2, -0.1, 0.0, 0.1, 0.2],
            'mult3': [-0.2, -0.1, 0.0, 0.1, 0.2],
            'moldura': [-0.3, -0.15, 0.0, 0.15, 0.3],
            'centro': [-0.2, -0.1, 0.0, 0.1, 0.2],
            'soma': [-0.3, -0.15, 0.0, 0.15, 0.3],
            'par': [-0.2, -0.1, 0.0, 0.1, 0.2],
            'impar': [-0.2, -0.1, 0.0, 0.1, 0.2],
            'linha': [-0.2, -0.1, 0.0, 0.1, 0.2],
            'coluna': [-0.2, -0.1, 0.0, 0.1, 0.2],
            'quadrante': [-0.2, -0.1, 0.0, 0.1, 0.2],
            'recurrence': [-0.3, -0.15, 0.0, 0.15, 0.3]
        }

        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.weights_file = weights_file
        self.q_table_file = q_table_file

        self.q_table = defaultdict(lambda: defaultdict(float))
        self.episode_count = 0
        self.performance_history = []
        self.ultima_acao = None

        if not self.load_q_table():
            logger.info("📝 Q-table nova inicializada")

        self.current_weights = self.load_weights()

    def _discretize_state(self, state: Dict[str, float]) -> Tuple:
        """Discretiza estado contínuo em bins"""
        discrete = []
        for key, value in state.items():
            if key in self.state_space:
                bins = self.state_space[key]
                discrete_value = np.digitize([value], bins)[0]
                discrete.append(discrete_value)
        return tuple(discrete)

    def _get_state_key(self, state: Dict[str, float]) -> str:
        """Converte estado em chave string para Q-table"""
        return str(self._discretize_state(state))

    def _action_to_key(self, action: Dict[str, float]) -> str:
        """Converte ação em chave string"""
        return "_".join([f"{k}:{v:.2f}" for k, v in sorted(action.items())])

    def load_weights(self) -> Dict[str, float]:
        """Carrega pesos salvos ou inicializa padrão"""
        if os.path.exists(self.weights_file):
            try:
                with open(self.weights_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                weights = data.get("weights", {})
                logger.info(f"✅ Pesos carregados de {self.weights_file}")
                return weights
            except Exception as e:
                logger.warning(f"Erro ao carregar pesos: {e}")
                return self._initialize_default_weights()
        else:
            return self._initialize_default_weights()

    def _initialize_default_weights(self) -> Dict[str, float]:
        """Inicializa pesos padrão balanceados"""
        default_weights = {
            'freq': 1.0,
            'gap': 0.8,
            'anomalo': 0.6,
            'break': 0.7,
            'diversity': 1.2,
            'consec': 0.5,
            'primo': 0.9,
            'fib': 0.8,
            'mult3': 0.7,
            'moldura': 1.0,
            'centro': 0.8,
            'soma': 1.1,
            'par': 1.0,
            'impar': 1.0,
            'linha': 0.6,
            'coluna': 0.6,
            'quadrante': 0.7,
            'recurrence': 0.9
        }
        logger.info("📊 Pesos padrão inicializados")
        return default_weights

    def save_weights(self, weights: Dict[str, float]) -> None:
        """Salva pesos atuais em disco"""
        try:
            os.makedirs(os.path.dirname(self.weights_file), exist_ok=True)
            payload = {
                "weights": weights,
                "episode": self.episode_count,
                "epsilon": self.epsilon,
                "timestamp": datetime.now().isoformat()
            }
            with open(self.weights_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            logger.debug(f"Pesos salvos ({len(weights)} critérios).")
        except Exception as e:
            logger.error(f"Erro ao salvar pesos: {e}")

    def save_q_table(self) -> None:
        """Persiste a Q-table em disco"""
        try:
            os.makedirs(os.path.dirname(self.q_table_file), exist_ok=True)
            
            q_table_serializable = {
                str(state): dict(actions) for state, actions in self.q_table.items()
            }
            payload = {
                "q_table": q_table_serializable,
                "episodes": self.episode_count,
                "epsilon": self.epsilon,
                "timestamp": datetime.now().isoformat(),
            }
            with open(self.q_table_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            logger.info(f"✅ Tabela Q salva: {len(self.q_table)} estados")
        except Exception as e:
            logger.error(f"Erro ao salvar Q-table: {e}")

    def load_q_table(self) -> bool:
        """Carrega a Q-table a partir do arquivo JSON"""
        if not os.path.exists(self.q_table_file):
            return False

        try:
            with open(self.q_table_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.q_table = defaultdict(lambda: defaultdict(float))
            for state_key, actions in data.get("q_table", {}).items():
                state_tuple = tuple(
                    int(x) for x in state_key.strip("()").split(",") if x
                )
                self.q_table[state_tuple] = defaultdict(
                    float, {k: v for k, v in actions.items()}
                )

            self.episode_count = data.get("episodes", 0)
            self.epsilon = data.get("epsilon", self.epsilon)

            logger.info(f"✅ Q-table carregada: {len(self.q_table)} estados")
            return True
        except Exception as e:
            logger.warning(f"Erro ao carregar Q-table: {e}")
            return False

    def choose_action(self, state: Dict[str, float]) -> Dict[str, float]:
        """Escolhe ação usando política epsilon-greedy"""
        discrete_state = self._discretize_state(state)
        
        if np.random.random() < self.epsilon:
            action = {
                criterion: np.random.choice(adjustments)
                for criterion, adjustments in self.action_space.items()
            }
            logger.debug(f"🎲 Exploração: ação aleatória (ε={self.epsilon:.3f})")
        else:
            action = {}
            for criterion in self.action_space.keys():
                best_adjustment = 0.0
                best_q_value = float('-inf')
                
                for adjustment in self.action_space[criterion]:
                    action_key = f"{criterion}_{adjustment}"
                    q_value = self.q_table[discrete_state].get(action_key, 0.0)
                    
                    if q_value > best_q_value:
                        best_q_value = q_value
                        best_adjustment = adjustment
                
                action[criterion] = best_adjustment
            
            logger.debug(f"🎯 Exploitação: melhor ação (Q-max={best_q_value:.3f})")
        
        return action

    def apply_action(
        self, 
        action: Dict[str, float], 
        current_weights: Dict[str, float]
    ) -> Dict[str, float]:
        """Aplica ações (ajustes) aos pesos atuais"""
        new_weights = current_weights.copy()
        
        for criterion, adjustment in action.items():
            if criterion in new_weights:
                new_weights[criterion] = np.clip(
                    new_weights[criterion] + adjustment,
                    0.1,  # Peso mínimo
                    3.0   # Peso máximo
                )
        
        self.ultima_acao = action
        self.current_weights = new_weights
        
        return new_weights

    def update_q_value(
        self,
        state: Dict[str, float],
        action: Dict[str, float],
        reward: float,
        next_state: Dict[str, float]
    ) -> None:
        """Atualiza Q-value usando equação de Bellman"""
        discrete_state = self._discretize_state(state)
        discrete_next_state = self._discretize_state(next_state)
        
        for criterion, adjustment in action.items():
            action_key = f"{criterion}_{adjustment}"
            
            current_q = self.q_table[discrete_state][action_key]
            
            max_next_q = max(
                self.q_table[discrete_next_state].values(),
                default=0.0
            )
            
            new_q = current_q + self.learning_rate * (
                reward + self.discount_factor * max_next_q - current_q
            )
            
            self.q_table[discrete_state][action_key] = new_q

    def train_episode(
        self,
        state: Dict[str, float],
        jogos_gerados: List[List[int]],
        resultado_real: List[int]
    ) -> float:
        """Treina o agente com resultado real do concurso"""
        acertos_list = []
        for jogo in jogos_gerados:
            acertos = len(set(jogo) & set(resultado_real))
            acertos_list.append(acertos)
        
        rewards = [
            1 if a == 11 else
            3 if a == 12 else
            8 if a == 13 else
            20 if a == 14 else
            100 if a == 15 else
            0
            for a in acertos_list
        ]
        
        avg_reward = sum(rewards) / len(rewards)
        
        next_state = state.copy()
        next_state['media_acertos'] = sum(acertos_list) / len(acertos_list)
        
        if hasattr(self, 'ultima_acao') and self.ultima_acao:
            self.update_q_value(state, self.ultima_acao, avg_reward, next_state)
        
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
        self.episode_count += 1
        
        self.performance_history.append({
            'episode': self.episode_count,
            'reward': avg_reward,
            'acertos_medio': sum(acertos_list) / len(acertos_list),
            'epsilon': self.epsilon,
            'timestamp': datetime.now().isoformat()
        })
        
        if self.episode_count % 10 == 0:
            self.save_q_table()
            self.save_weights(self.current_weights)
        
        logger.info(f"🎓 Aprendizado concluído:")
        logger.info(f"   Episódio: {self.episode_count}")
        logger.info(f"   Recompensa média: {avg_reward:.2f}")
        logger.info(f"   Acertos médios: {sum(acertos_list) / len(acertos_list):.1f}")
        logger.info(f"   Epsilon: {self.epsilon:.3f}")
        logger.info(f"   Melhor jogo: {max(acertos_list)} acertos")
        
        return avg_reward

    def ajustar_para_anti_salto(
        self, 
        current_weights: Dict[str, float]
    ) -> Dict[str, float]:
        """Ajusta pesos para modo anti-salto"""
        anti_salto_weights = current_weights.copy()

        anti_salto_weights["consec"] = anti_salto_weights.get("consec", 1.0) * 0.6
        anti_salto_weights["recurrence"] = anti_salto_weights.get("recurrence", 1.0) * 0.7
        anti_salto_weights["moldura"] = anti_salto_weights.get("moldura", 1.0) * 1.2
        anti_salto_weights["diversity"] = anti_salto_weights.get("diversity", 1.0) * 1.5
        anti_salto_weights["anomalo"] = anti_salto_weights.get("anomalo", 1.0) * 1.3

        logger.warning("🎯 Modo anti-salto ativado")
        logger.warning(f"   consec: {anti_salto_weights['consec']:.2f}")
        logger.warning(f"   diversity: {anti_salto_weights['diversity']:.2f}")

        return anti_salto_weights
