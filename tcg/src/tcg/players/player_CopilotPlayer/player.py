"""
CopilotPlayer - 最強のタワーディフェンスAI

複数の高度な戦略とアルゴリズムを組み合わせた最適化AIプレイヤー
"""

from typing import Tuple, List
from tcg.controller import Controller
from tcg.players.player_CopilotPlayer.evaluator import FortressEvaluator
from .strategy import StrategyEngine
from .optimizer import ActionOptimizer
from .exploits import GameExploits


class CopilotPlayer(Controller):
    """
    CopilotPlayer - 最強AI
    
    特徴:
    - 多次元要塞評価システム
    - 動的戦況分析
    - 適応的戦略選択
    - 先読みシミュレーション
    - リスク管理
    """
    
    # ゲームフェーズの閾値
    EARLY_GAME_THRESHOLD = 3000
    MID_GAME_THRESHOLD = 15000
    
    def __init__(self):
        super().__init__()
        
        # 各モジュールの初期化
        self.evaluator = FortressEvaluator()
        self.strategy = StrategyEngine(self.evaluator)
        self.optimizer = ActionOptimizer(self.evaluator)
        self.exploits = GameExploits()
        
        # ゲーム状態の追跡
        self.step = 0
        self.team = 1
        self.game_phase = 'early'
        
        # パフォーマンス追跡
        self.previous_dominance = 0.0
        self.dominance_history = []
        
    def team_name(self) -> str:
        return "CopilotPlayer"
    
    def update(self, info) -> Tuple[int, int, int]:
        """
        メイン更新ループ
        
        Args:
            info: [team_id, state, moving_pawns, spawning_pawns, done]
        
        Returns:
            (command, subject, to)
        """
        # 情報の展開
        self.team, state, moving_pawns, spawning_pawns, done = info
        self.step += 1
        
        # ゲームフェーズの判定
        self.game_phase = self._determine_game_phase()
        
        # 戦況の分析
        self._analyze_situation(state)
        
        # ゲームメカニクスの抜け穴を活用した追加チェック
        self._exploit_game_mechanics(state, moving_pawns)
        
        # 全ての可能なアクションを生成
        actions = self.strategy.decide_actions(
            state, self.team, self.game_phase, 
            moving_pawns, spawning_pawns, self.step
        )
        
        # アクションの最適化
        optimized_actions = self.optimizer.optimize_actions(
            actions, state, self.team, self.game_phase
        )
        
        # 最適なアクションを選択
        command, subject, to = self.strategy.select_best_action(optimized_actions)
        
        return command, subject, to
    
    def _exploit_game_mechanics(self, state: List, moving_pawns: List):
        """ゲームメカニクスの抜け穴を活用"""
        # 生産オーバーフローを検出して対処
        wasting = self.exploits.detect_production_overflow_waste(state, self.team)
        if wasting:
            # 無駄にしている要塞があることを記録（戦略で活用）
            pass
        
        # 重要なタイミングウィンドウを検出
        windows = self.exploits.find_critical_timing_windows(state, self.team, self.step)
        if windows:
            # タイミングを戦略に反映
            pass
    
    def _determine_game_phase(self) -> str:
        """ゲームフェーズを判定"""
        if self.step < self.EARLY_GAME_THRESHOLD:
            return 'early'
        elif self.step < self.MID_GAME_THRESHOLD:
            return 'mid'
        else:
            return 'late'
    
    def _analyze_situation(self, state: List):
        """戦況を分析"""
        # 支配度の計算
        dominance = self.evaluator.calculate_dominance_score(state, self.team)
        self.dominance_history.append(dominance)
        
        # 履歴の管理（最新100ステップのみ保持）
        if len(self.dominance_history) > 100:
            self.dominance_history.pop(0)
        
        self.previous_dominance = dominance
