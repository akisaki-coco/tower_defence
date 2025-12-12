"""
Evaluator Module - 要塞と戦況の評価システム

要塞の価値を多次元的に評価し、戦況を分析するモジュール
"""

from typing import List, Tuple, Dict
import math


class FortressEvaluator:
    """要塞の多次元評価クラス"""
    
    # グラフの隣接関係（双方向）
    ADJACENCY = [
        [1, 3, 4],      # 0
        [0, 2, 4],      # 1
        [1, 4, 5],      # 2
        [0, 4, 6, 7],   # 3
        [0, 1, 2, 3, 5, 6, 7, 8],  # 4: 中央ハブ
        [2, 4, 7, 8],   # 5
        [3, 4, 7, 9],   # 6
        [3, 4, 5, 6, 8, 9, 10, 11],  # 7: 中央ハブ
        [4, 5, 7, 11],  # 8
        [6, 7, 10],     # 9
        [7, 9, 11],     # 10
        [7, 8, 10],     # 11
    ]
    
    # 初期中立兵士数
    INITIAL_NEUTRAL_TROOPS = [10, 0, 10, 20, 30, 20, 20, 30, 20, 10, 0, 10]
    
    # 各要塞の戦略的重要度（接続数と位置に基づく基本スコア）
    BASE_IMPORTANCE = {
        0: 3, 1: 4, 2: 3,       # 上側エリア
        3: 6, 4: 10, 5: 6,      # 中央上（4は最重要ハブ）
        6: 6, 7: 10, 8: 6,      # 中央下（7は最重要ハブ）
        9: 3, 10: 4, 11: 3      # 下側エリア
    }
    
    # 生産クールダウン [kind][level]
    PRODUCTION_COOLDOWN = [
        [60, 60, 54, 48, 42, 35],  # kind 0: 速い
        [90, 90, 81, 72, 63, 54]   # kind 1: 遅い
    ]
    
    # 要塞レベルごとの制限
    FORTRESS_LIMIT = [10, 10, 20, 30, 40, 50]
    
    # 攻撃力（1部隊あたり）
    ATTACK_POWER = [0.65, 0.95]  # [kind 0, kind 1]
    
    def __init__(self):
        # グラフの中心性を事前計算
        self.degree_centrality = self._calculate_degree_centrality()
        self.closeness_centrality = self._calculate_closeness_centrality()
    
    def _calculate_degree_centrality(self) -> Dict[int, float]:
        """次数中心性を計算（接続数の多さ）"""
        centrality = {}
        for i in range(12):
            centrality[i] = len(self.ADJACENCY[i]) / 11  # 正規化
        return centrality
    
    def _calculate_closeness_centrality(self) -> Dict[int, float]:
        """近接中心性を計算（他の全ノードへの平均距離の逆数）"""
        centrality = {}
        for i in range(12):
            distances = self._bfs_distances(i)
            total_distance = sum(distances.values())
            if total_distance > 0:
                centrality[i] = (len(distances) - 1) / total_distance
            else:
                centrality[i] = 0
        return centrality
    
    def _bfs_distances(self, start: int) -> Dict[int, int]:
        """BFSで全ノードへの最短距離を計算"""
        distances = {start: 0}
        queue = [start]
        visited = {start}
        
        while queue:
            current = queue.pop(0)
            for neighbor in self.ADJACENCY[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)
        
        return distances
    
    def evaluate_fortress(self, fortress_id: int, state: List, team: int, 
                         game_phase: str) -> float:
        """
        要塞の総合的な価値を評価
        
        Args:
            fortress_id: 要塞ID
            state: ゲーム状態
            team: 自チームID
            game_phase: ゲームフェーズ（'early', 'mid', 'late'）
        
        Returns:
            要塞の価値スコア
        """
        fort = state[fortress_id]
        fort_team, kind, level, troops, upgrade_time, neighbors = fort
        
        score = 0
        
        # 基本的な戦略価値
        strategic_value = self.BASE_IMPORTANCE[fortress_id]
        score += strategic_value * 10
        
        # グラフ理論的な中心性
        score += self.degree_centrality[fortress_id] * 15
        score += self.closeness_centrality[fortress_id] * 20
        
        # 経済的価値（生産効率）
        production_rate = self._calculate_production_rate(kind, level)
        score += production_rate * 8
        
        # 戦術的価値（位置関係）
        tactical_value = self._calculate_tactical_value(
            fortress_id, state, team, game_phase
        )
        score += tactical_value
        
        # 現在の軍事力
        military_value = troops * 0.5
        score += military_value
        
        # フェーズ別の調整
        if game_phase == 'early':
            # 序盤は中立の重要拠点を優先
            if fort_team == 0:
                score *= 1.5
        elif game_phase == 'mid':
            # 中盤は経済成長を重視
            score += production_rate * 5
        else:  # late
            # 終盤は軍事力を重視
            score += military_value * 1.5
        
        return score
    
    def _calculate_production_rate(self, kind: int, level: int) -> float:
        """生産効率を計算（単位時間あたりの部隊生産数）"""
        cooldown = self.PRODUCTION_COOLDOWN[kind][level]
        if cooldown > 0:
            return 1.0 / cooldown * 100  # スケーリング
        return 0
    
    def _calculate_tactical_value(self, fortress_id: int, state: List, 
                                  team: int, game_phase: str) -> float:
        """戦術的価値を計算（周辺の状況を考慮）"""
        neighbors = self.ADJACENCY[fortress_id]
        
        friendly_count = 0
        enemy_count = 0
        neutral_count = 0
        
        for neighbor_id in neighbors:
            neighbor_team = state[neighbor_id][0]
            if neighbor_team == team:
                friendly_count += 1
            elif neighbor_team == 0:
                neutral_count += 1
            else:
                enemy_count += 1
        
        tactical_score = 0
        
        # 前線の要塞は重要（敵に隣接）
        if enemy_count > 0:
            tactical_score += enemy_count * 15
        
        # 中立に隣接している要塞も重要（拡張の拠点）
        if neutral_count > 0:
            tactical_score += neutral_count * 10
        
        # 孤立している要塞は価値が低い
        if friendly_count == 0 and enemy_count == 0:
            tactical_score -= 20
        
        return tactical_score
    
    def evaluate_attack_success(self, attacker_troops: float, 
                               defender_troops: float, defender_level: int,
                               defender_kind: int, travel_time: int,
                               attacker_kind: int = 0) -> Tuple[bool, float]:
        """
        攻撃の成功率を詳細に評価
        
        Returns:
            (成功するか, 成功確率)
        """
        # 送られる部隊は半分
        attacking_force = attacker_troops / 2
        
        # 最低限の部隊が残っているか確認
        if attacking_force < 3:
            return False, 0.0
        
        # 移動中の減衰（距離による損失を仮定）
        attacking_force *= 0.95  # 5%のロス（より現実的に）
        
        # 到着時の敵の生産予測（より保守的に）
        production_cooldown = self.PRODUCTION_COOLDOWN[defender_kind][defender_level]
        if production_cooldown > 0:
            # 保守的に1.5倍の生産を見積もる
            additional_troops = (travel_time / production_cooldown) * 1.5
        else:
            additional_troops = 0
        
        total_defense = defender_troops + additional_troops
        
        # 攻撃力の計算
        attack_damage = attacking_force * self.ATTACK_POWER[attacker_kind]
        
        # 防御側の反撃力（残存部隊の攻撃力）
        defense_damage = total_defense * self.ATTACK_POWER[defender_kind]
        
        # ダメージ交換後の結果
        remaining_attack = attacking_force - defense_damage / self.ATTACK_POWER[attacker_kind]
        remaining_defense = total_defense - attack_damage / self.ATTACK_POWER[defender_kind]
        
        # 成功判定：残存攻撃部隊が残り、防御部隊が0以下
        success = remaining_attack > 1.0 and remaining_defense <= 0
        
        # 成功確率の計算（より保守的に）
        if remaining_defense <= 0:
            # 攻撃成功時：余裕度に基づく確率
            margin = abs(remaining_defense) / (total_defense + 1)
            probability = min(0.95, 0.5 + margin * 0.5)  # 最大95%
        else:
            # 攻撃失敗時：防御側の残存兵力に基づく
            probability = max(0.0, 1.0 - remaining_defense / (attacking_force + 1))
            probability *= 0.5  # さらに保守的に
        
        return success, probability
    
    def calculate_game_state_score(self, state: List, team: int) -> Dict[str, float]:
        """
        ゲーム全体の戦況を評価
        
        Returns:
            各種スコアの辞書
        """
        scores = {
            'fortress_count': 0,
            'total_troops': 0,
            'total_production': 0,
            'strategic_control': 0,
            'military_power': 0,
        }
        
        for i in range(12):
            fort = state[i]
            fort_team, kind, level, troops, _, _ = fort
            
            if fort_team == team:
                scores['fortress_count'] += 1
                scores['total_troops'] += troops
                scores['total_production'] += self._calculate_production_rate(kind, level)
                scores['strategic_control'] += self.BASE_IMPORTANCE[i]
                scores['military_power'] += troops * self.ATTACK_POWER[kind]
        
        return scores
    
    def estimate_travel_time(self, from_id: int, to_id: int, pawn_kind: int) -> int:
        """
        部隊の移動時間を推定
        
        Args:
            from_id: 出発要塞
            to_id: 目標要塞
            pawn_kind: 部隊の種類（0: 速い、1: 遅い）
        
        Returns:
            推定移動時間（ステップ数）
        """
        # 要塞間の距離を計算（ユークリッド距離の近似）
        # 実際の距離は固定だが、種類によって速度が異なる
        
        # 基本移動時間（要塞間の平均的な移動時間）
        base_time = 100
        
        # 種類による補正
        if pawn_kind == 0:  # 速い
            return int(base_time * 0.8)
        else:  # 遅い
            return int(base_time * 1.2)
    
    def find_critical_fortresses(self, state: List, team: int) -> List[int]:
        """
        防御すべき重要な要塞を特定
        
        Returns:
            重要要塞のIDリスト（優先度順）
        """
        critical = []
        
        for i in range(12):
            if state[i][0] == team:
                # 敵に隣接している要塞
                enemy_neighbors = sum(
                    1 for n in self.ADJACENCY[i] if state[n][0] not in [0, team]
                )
                
                if enemy_neighbors > 0:
                    importance = self.BASE_IMPORTANCE[i]
                    priority = importance * 10 + enemy_neighbors * 20
                    critical.append((priority, i))
        
        # 優先度順にソート
        critical.sort(reverse=True)
        return [fort_id for _, fort_id in critical]
    
    def calculate_dominance_score(self, state: List, team: int) -> float:
        """
        領域支配度を計算
        
        Returns:
            支配度スコア（-1.0 〜 1.0）
        """
        our_score = self.calculate_game_state_score(state, team)
        enemy_team = 2 if team == 1 else 1
        enemy_score = self.calculate_game_state_score(state, enemy_team)
        
        # 総合スコアを計算
        our_total = (
            our_score['fortress_count'] * 20 +
            our_score['total_troops'] * 0.5 +
            our_score['total_production'] * 10 +
            our_score['strategic_control'] * 5
        )
        
        enemy_total = (
            enemy_score['fortress_count'] * 20 +
            enemy_score['total_troops'] * 0.5 +
            enemy_score['total_production'] * 10 +
            enemy_score['strategic_control'] * 5
        )
        
        total = our_total + enemy_total
        if total > 0:
            return (our_total - enemy_total) / total
        return 0.0
