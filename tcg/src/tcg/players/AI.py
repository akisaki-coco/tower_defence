"""
AIPlayer Main Class

ゲームシステムと戦略ロジック(AI_strategy.py)をつなぐ「体」の役割。
"""
from tcg.controller import Controller
from .AI_strategy import Strategy

class AIPlayer(Controller):
    def __init__(self) -> None:
        super().__init__()
        # ここで「頭脳」であるStrategyクラスを読み込む
        self.strategy = Strategy()
        self.step = 0

    def team_name(self):
        # トーナメント表に表示される名前
        return "My Strong AI"

    def update(self, info) -> tuple[int, int, int]:
        """
        毎フレーム呼び出されるメソッド
        """
        # ゲーム情報を受け取る
        # info = [team_id, state, moving_pawns, spawning_pawns, done]
        team, state, moving_pawns, spawning_pawns, done = info
        
        # 戦略クラス(AI_strategy.py)に判断を任せる
        return self.strategy.decide_action(state)
