from tcg.controller import Controller
from .gemini_analysis import GameAnalysis
from .gemini_strategy import GeminiStrategy

class GeminiPlayer(Controller):
    def __init__(self):
        super().__init__()
        self.strategy = GeminiStrategy()

    def team_name(self) -> str:
        return "Gemini"

    def update(self, info):
        # info: [team, state, pawn, SpawnPoint, done]
        analysis = GameAnalysis(info)
        command, subject, to = self.strategy.get_best_move(analysis)
        return command, subject, to
