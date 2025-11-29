"""
Core - Módulos principais do motor de IA
"""

from .lotofacil_ai_v3 import LotofacilAIv3
from .genetic_algorithm import GeneticOptimizer
from .fitness_modules import FitnessCalculator
from .mazusoft_integration import MazusoftAnalyzer
from .event_detector import EventDetector
from .reinforcement_learning import QLearningAgent

__all__ = [
    'LotofacilAIv3',
    'GeneticOptimizer',
    'FitnessCalculator',
    'MazusoftAnalyzer',
    'EventDetector',
    'QLearningAgent'
]
