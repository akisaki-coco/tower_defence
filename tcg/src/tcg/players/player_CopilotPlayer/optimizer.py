"""
Optimizer Module - 行動の最適化

リスク・リターン分析と資源配分の最適化を行うモジュール
"""

from typing import List, Tuple, Dict
from .evaluator import FortressEvaluator


class ActionOptimizer:
    """行動最適化クラス"""
    
    def __init__(self, evaluator: FortressEvaluator):
        self.evaluator = evaluator
    
    def optimize_actions(self, actions: List[Tuple], state: List, team: int,
                        game_phase: str) -> List[Tuple]:
        """
        アクションリストを最適化
        
        - 重複する行動の排除
        - リスク・リターンの再評価
        - 資源制約の考慮
        
        Returns:
            最適化されたアクションリスト
        """
        if not actions:
            return []
        
        # 重複排除
        unique_actions = self._remove_duplicates(actions)
        
        # リスク評価
        evaluated_actions = self._evaluate_risks(unique_actions, state, team)
        
        # 資源制約を考慮
        feasible_actions = self._filter_feasible_actions(evaluated_actions, state, team)
        
        # リスク・リターン比で再評価
        optimized_actions = self._rerank_by_risk_return(feasible_actions, state, team)
        
        return optimized_actions
    
    def _remove_duplicates(self, actions: List[Tuple]) -> List[Tuple]:
        """重複する行動を排除"""
        seen = set()
        unique = []
        
        for action in actions:
            priority, command, subject, to = action
            key = (command, subject, to)
            
            if key not in seen:
                seen.add(key)
                unique.append(action)
            else:
                # 同じ行動で優先度が高い方を残す
                for i, existing in enumerate(unique):
                    if (existing[1], existing[2], existing[3]) == key:
                        if priority > existing[0]:
                            unique[i] = action
                        break
        
        return unique
    
    def _evaluate_risks(self, actions: List[Tuple], state: List, 
                       team: int) -> List[Tuple]:
        """各行動のリスクを評価"""
        evaluated = []
        
        for action in actions:
            priority, command, subject, to = action
            
            if command == 1:  # 部隊移動
                risk = self._calculate_movement_risk(subject, to, state, team)
                # リスクが高い場合は優先度を下げる
                adjusted_priority = priority * (1.0 - risk * 0.3)
                evaluated.append((adjusted_priority, command, subject, to))
            
            elif command == 2:  # アップグレード
                risk = self._calculate_upgrade_risk(subject, state, team)
                adjusted_priority = priority * (1.0 - risk * 0.2)
                evaluated.append((adjusted_priority, command, subject, to))
            
            else:
                evaluated.append(action)
        
        return evaluated
    
    def _calculate_movement_risk(self, from_id: int, to_id: int, 
                                 state: List, team: int) -> float:
        """部隊移動のリスクを計算 (0.0 〜 1.0)"""
        risk = 0.0
        
        # 出発要塞が脆弱になるリスク
        fort_troops = state[from_id][3]
        if fort_troops < 8:
            risk += 0.3
        
        # 出発要塞が攻撃されやすい位置にあるか
        enemy_team = 2 if team == 1 else 1
        enemy_neighbors = sum(
            1 for n in self.evaluator.ADJACENCY[from_id]
            if state[n][0] == enemy_team
        )
        if enemy_neighbors > 0:
            risk += 0.2 * enemy_neighbors
        
        # 目標が敵要塞で、反撃のリスク
        if state[to_id][0] == enemy_team:
            enemy_troops = state[to_id][3]
            if enemy_troops > fort_troops * 0.4:
                risk += 0.3
        
        return min(1.0, risk)
    
    def _calculate_upgrade_risk(self, fortress_id: int, state: List, 
                               team: int) -> float:
        """アップグレードのリスクを計算"""
        risk = 0.0
        
        # 前線の要塞でアップグレードするリスク
        enemy_team = 2 if team == 1 else 1
        enemy_neighbors = sum(
            1 for n in self.evaluator.ADJACENCY[fortress_id]
            if state[n][0] == enemy_team
        )
        
        if enemy_neighbors > 0:
            # 前線でのアップグレードは部隊が減るのでリスク
            risk += 0.2 * enemy_neighbors
            
            # ただし、部隊が十分にあればリスクは低い
            fort_troops = state[fortress_id][3]
            fort_level = state[fortress_id][2]
            max_troops = self.evaluator.FORTRESS_LIMIT[fort_level]
            
            if fort_troops > max_troops * 0.8:
                risk -= 0.15
        
        return max(0.0, min(1.0, risk))
    
    def _filter_feasible_actions(self, actions: List[Tuple], state: List,
                                team: int) -> List[Tuple]:
        """資源制約を考慮して実行可能な行動のみをフィルタ"""
        feasible = []
        
        for action in actions:
            priority, command, subject, to = action
            
            if command == 1:  # 部隊移動
                # 十分な部隊があるか
                if state[subject][0] == team and state[subject][3] >= 2:
                    # 隣接しているか
                    if to in self.evaluator.ADJACENCY[subject]:
                        feasible.append(action)
            
            elif command == 2:  # アップグレード
                fort_level = state[subject][2]
                fort_troops = state[subject][3]
                upgrade_time = state[subject][4]
                
                # アップグレード可能か
                if (state[subject][0] == team and 
                    upgrade_time == -1 and 
                    fort_level < 5 and
                    fort_troops >= self.evaluator.FORTRESS_LIMIT[fort_level] // 2):
                    feasible.append(action)
            
            else:
                feasible.append(action)
        
        return feasible
    
    def _rerank_by_risk_return(self, actions: List[Tuple], state: List,
                              team: int) -> List[Tuple]:
        """リスク・リターン比で再ランク付け"""
        reranked = []
        
        for action in actions:
            priority, command, subject, to = action
            
            if command == 1:  # 部隊移動
                # リターンの計算
                if state[to][0] == team:
                    # 味方への援軍：防御価値
                    return_value = self.evaluator.BASE_IMPORTANCE[to] * 2
                else:
                    # 攻撃：要塞の価値
                    return_value = self.evaluator.evaluate_fortress(
                        to, state, team, 'mid'
                    ) * 0.1
                
                # リスクの計算
                risk = self._calculate_movement_risk(subject, to, state, team)
                
                # リスク・リターン比
                if risk < 0.01:
                    risk = 0.01
                risk_return_ratio = return_value / risk
                
                # 優先度を調整
                adjusted_priority = priority + risk_return_ratio * 5
                reranked.append((adjusted_priority, command, subject, to))
            
            else:
                reranked.append(action)
        
        return reranked
    
    def calculate_resource_allocation(self, state: List, team: int) -> Dict[str, float]:
        """
        資源配分の最適化
        
        Returns:
            推奨される資源配分（攻撃、防御、経済の割合）
        """
        # 現在の戦況を評価
        dominance = self.evaluator.calculate_dominance_score(state, team)
        
        # 我々の要塞数
        our_fortresses = sum(1 for i in range(12) if state[i][0] == team)
        enemy_team = 2 if team == 1 else 1
        enemy_fortresses = sum(1 for i in range(12) if state[i][0] == enemy_team)
        
        allocation = {
            'attack': 0.0,
            'defense': 0.0,
            'economy': 0.0,
        }
        
        # 支配度に基づく配分
        if dominance > 0.3:  # 優勢
            allocation['attack'] = 0.5
            allocation['defense'] = 0.2
            allocation['economy'] = 0.3
        elif dominance > 0:  # やや優勢
            allocation['attack'] = 0.4
            allocation['defense'] = 0.3
            allocation['economy'] = 0.3
        elif dominance > -0.3:  # やや劣勢
            allocation['attack'] = 0.3
            allocation['defense'] = 0.4
            allocation['economy'] = 0.3
        else:  # 劣勢
            allocation['attack'] = 0.2
            allocation['defense'] = 0.5
            allocation['economy'] = 0.3
        
        # 要塞数による調整
        if our_fortresses < 4:
            # 要塞が少ない場合は拡張優先
            allocation['attack'] += 0.2
            allocation['defense'] -= 0.1
            allocation['economy'] -= 0.1
        
        return allocation
    
    def should_take_aggressive_action(self, state: List, team: int, 
                                     game_phase: str) -> bool:
        """
        積極的な行動を取るべきか判定
        
        Returns:
            積極的に行動すべきならTrue
        """
        dominance = self.evaluator.calculate_dominance_score(state, team)
        
        # 終盤は積極的に
        if game_phase == 'late':
            return True
        
        # 優勢な場合は積極的に
        if dominance > 0.2:
            return True
        
        # 劣勢でも序盤は積極的に（中立要塞の確保）
        if game_phase == 'early' and dominance > -0.4:
            return True
        
        return False
    
    def calculate_optimal_upgrade_sequence(self, state: List, 
                                          team: int) -> List[int]:
        """
        最適なアップグレード順序を計算
        
        Returns:
            アップグレードすべき要塞IDのリスト（優先順）
        """
        candidates = []
        
        for i in range(12):
            if state[i][0] == team and state[i][4] == -1 and state[i][2] < 5:
                # 現在の生産率
                current_rate = self.evaluator._calculate_production_rate(
                    state[i][1], state[i][2]
                )
                # アップグレード後の生産率
                future_rate = self.evaluator._calculate_production_rate(
                    state[i][1], state[i][2] + 1
                )
                
                # 改善率
                improvement = future_rate - current_rate
                
                # 要塞の重要度
                importance = self.evaluator.BASE_IMPORTANCE[i]
                
                # スコアを計算
                score = improvement * 10 + importance * 5
                
                candidates.append((score, i))
        
        # スコア順にソート
        candidates.sort(reverse=True)
        
        return [fort_id for _, fort_id in candidates]
