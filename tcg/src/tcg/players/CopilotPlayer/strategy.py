"""
Strategy Module - 戦略決定エンジン

攻撃、防御、経済成長などの戦略を決定するモジュール
"""

from typing import List, Tuple, Optional
from tcg.players.CopilotPlayer.evaluator import FortressEvaluator
from .tactics import TacticalPatterns


class StrategyEngine:
    """戦略決定エンジン"""
    
    def __init__(self, evaluator: FortressEvaluator):
        self.evaluator = evaluator
        self.tactics = TacticalPatterns()
        self.history = []  # 過去の行動履歴
    
    def decide_actions(self, state: List, team: int, game_phase: str,
                      moving_pawns: List, spawning_pawns: List,
                      step: int) -> List[Tuple[float, int, int, int]]:
        """
        すべての可能なアクションを生成し、優先度付けして返す
        
        Returns:
            (優先度, コマンド, subject, to) のリスト
        """
        actions = []
        
        # 高度な戦術パターンからアクションを生成
        actions.extend(self._advanced_tactical_actions(state, team, game_phase))
        
        # 各戦略から行動を生成
        actions.extend(self._neutral_conquest_strategy(state, team, game_phase, step))
        actions.extend(self._enemy_attack_strategy(state, team, game_phase, moving_pawns))
        actions.extend(self._defense_strategy(state, team, moving_pawns, spawning_pawns))
        actions.extend(self._upgrade_strategy(state, team, game_phase, step))
        actions.extend(self._reinforcement_strategy(state, team, game_phase))
        actions.extend(self._opportunistic_strategy(state, team, game_phase))
        
        return actions
    
    def _advanced_tactical_actions(self, state: List, team: int, 
                                  game_phase: str) -> List[Tuple]:
        """高度な戦術パターンに基づくアクション"""
        actions = []
        
        # 初期中立兵士数
        INITIAL_NEUTRAL = [10, 0, 10, 20, 30, 20, 20, 30, 20, 10, 0, 10]
        
        # 挟撃攻撃の機会
        pincer_opportunities = self.tactics.detect_pincer_attack_opportunity(state, team)
        for target, attackers, total_troops in pincer_opportunities:
            # 最も部隊が多い攻撃元を選択
            best_attacker = max(attackers, key=lambda x: state[x][3])
            if state[best_attacker][3] >= 12:  # より慎重に
                # 中央ハブの場合はさらに慎重
                if target in [4, 7] and state[target][0] == 0:
                    if INITIAL_NEUTRAL[target] >= 30 and state[best_attacker][3] < 25:
                        continue  # 兵力不足なのでスキップ
                priority = 120 + len(attackers) * 15
                actions.append((priority, 1, best_attacker, target))
        
        # 突破の機会
        breakthrough_opportunities = self.tactics.detect_breakthrough_opportunity(state, team)
        for my_fort, weak_enemy, targets in breakthrough_opportunities:
            if state[my_fort][3] >= 12:
                priority = 100 + len(targets) * 8
                actions.append((priority, 1, my_fort, weak_enemy))
        
        # チョークポイントの確保（より慎重に）
        choke_points = self.tactics.identify_choke_points(state, team)
        for choke in choke_points:
            if state[choke][0] == 0:  # 中立のチョークポイント
                # 中央ハブの場合は慎重に
                if choke in [4, 7]:
                    required_troops = 25  # 高い閾値
                else:
                    required_troops = 10
                
                # 隣接する味方要塞から攻撃
                for my_fort in range(12):
                    if state[my_fort][0] == team and choke in self.evaluator.ADJACENCY[my_fort]:
                        if state[my_fort][3] >= required_troops:
                            # 攻撃成功率を確認
                            _, prob = self.evaluator.evaluate_attack_success(
                                state[my_fort][3], state[choke][3],
                                state[choke][2], state[choke][1], 100, state[my_fort][1]
                            )
                            if prob >= 0.8:  # 80%以上の成功率
                                priority = 130 if choke not in [4, 7] else 110
                                actions.append((priority, 1, my_fort, choke))
        
        # 包囲される危険がある要塞への援軍
        endangered = self.tactics.detect_encirclement_danger(state, team)
        for fort in endangered:
            neighbors = self.evaluator.ADJACENCY[fort]
            for ally in neighbors:
                if state[ally][0] == team and state[ally][3] >= 8:  # より慎重に
                    priority = 125
                    actions.append((priority, 1, ally, fort))
        
        # 拡張回廊の制圧（弱い要塞のみ）
        corridors = self.tactics.detect_expansion_corridors(state, team)
        for corridor in corridors:
            # 弱い中立要塞（10兵以下）のみ対象
            weak_corridor = [f for f in corridor if INITIAL_NEUTRAL[f] <= 10]
            if not weak_corridor:
                continue
            
            # 回廊の入口（味方に最も近い要塞）を見つける
            for fort in weak_corridor:
                for my_fort in range(12):
                    if state[my_fort][0] == team and fort in self.evaluator.ADJACENCY[my_fort]:
                        if state[my_fort][3] >= 8:
                            priority = 95 + len(weak_corridor) * 5
                            actions.append((priority, 1, my_fort, fort))
                            break
        
        return actions
    
    def _neutral_conquest_strategy(self, state: List, team: int, 
                                  game_phase: str, step: int) -> List[Tuple]:
        """中立要塞制圧戦略（初期兵士数を考慮）"""
        actions = []
        my_fortresses = [i for i in range(12) if state[i][0] == team]
        
        # 初期中立兵士数
        INITIAL_NEUTRAL = [10, 0, 10, 20, 30, 20, 20, 30, 20, 10, 0, 10]
        
        for my_fort in my_fortresses:
            fort_troops = state[my_fort][3]
            fort_kind = state[my_fort][1]
            
            # 最低限の部隊がある場合のみ
            if fort_troops < 6:
                continue
            
            neighbors = self.evaluator.ADJACENCY[my_fort]
            
            for neighbor in neighbors:
                if state[neighbor][0] != 0:  # 中立でない
                    continue
                
                neutral_troops = state[neighbor][3]
                neutral_level = state[neighbor][2]
                neutral_kind = state[neighbor][1]
                
                # 初期兵士数を取得
                initial_troops = INITIAL_NEUTRAL[neighbor]
                
                # 攻撃成功率を計算
                travel_time = self.evaluator.estimate_travel_time(my_fort, neighbor, fort_kind)
                success, probability = self.evaluator.evaluate_attack_success(
                    fort_troops, neutral_troops, neutral_level, 
                    neutral_kind, travel_time, fort_kind
                )
                
                # 成功確率の閾値を初期兵士数に応じて調整
                if initial_troops <= 10:
                    threshold = 0.65  # 弱い要塞：積極的
                elif initial_troops <= 20:
                    threshold = 0.75  # 中程度：慣重
                else:  # 30以上（中央ハブ）
                    threshold = 0.85  # 強い要塞：非常に慣重
                
                if probability >= threshold:
                    # 要塞の価値を評価
                    fortress_value = self.evaluator.evaluate_fortress(
                        neighbor, state, team, game_phase
                    )
                    
                    # 優先度を計算
                    priority = 80 + fortress_value * 0.3 + probability * 30
                    
                    # 弱い中立要塞（10兵）を最優先
                    if initial_troops <= 10:
                        priority += 150
                        if game_phase == 'early':
                            priority += 100  # 序盤はさらに優先
                    
                    # 中程度の要塞（20兵）
                    elif initial_troops <= 20:
                        if game_phase == 'early':
                            priority += 50
                        else:
                            priority += 80
                    
                    # 中央ハブ（30兵）は十分な兵力がある場合のみ
                    else:
                        if fort_troops >= 25 and probability >= 0.9:
                            priority += 100  # 十分な兵力と高確率
                        elif game_phase == 'mid' and fort_troops >= 20:
                            priority += 50  # 中盤で兵力があれば
                        else:
                            priority -= 50  # それ以外は優先度下げ
                    
                    # 部隊が十分にある場合は優先度を上げる
                    if fort_troops >= 15:
                        priority += 15
                    
                    actions.append((priority, 1, my_fort, neighbor))
        
        return actions
        
        return actions
    
    def _enemy_attack_strategy(self, state: List, team: int, game_phase: str,
                              moving_pawns: List) -> List[Tuple]:
        """敵要塞攻撃戦略（より慎重に）"""
        actions = []
        my_fortresses = [i for i in range(12) if state[i][0] == team]
        enemy_team = 2 if team == 1 else 1
        
        for my_fort in my_fortresses:
            fort_troops = state[my_fort][3]
            fort_kind = state[my_fort][1]
            fort_level = state[my_fort][2]
            
            # 攻撃に必要な最低部隊数（より高く設定）
            min_troops = 15 if game_phase == 'early' else 12
            if fort_troops < min_troops:
                continue
            
            neighbors = self.evaluator.ADJACENCY[my_fort]
            
            for neighbor in neighbors:
                if state[neighbor][0] != enemy_team:
                    continue
                
                enemy_troops = state[neighbor][3]
                enemy_level = state[neighbor][2]
                enemy_kind = state[neighbor][1]
                
                # 敵が移動中の部隊を計算（この要塞に向かっている敵）
                incoming_enemy = sum(
                    1 for pawn in moving_pawns
                    if pawn[0] == enemy_team and pawn[3] == neighbor
                )
                
                # 攻撃成功率を計算
                travel_time = self.evaluator.estimate_travel_time(my_fort, neighbor, fort_kind)
                success, probability = self.evaluator.evaluate_attack_success(
                    fort_troops, enemy_troops + incoming_enemy, 
                    enemy_level, enemy_kind, travel_time, fort_kind
                )
                
                # 成功率の閾値をより厳しく
                threshold = 0.75 if game_phase == 'late' else 0.8
                if probability > threshold:
                    # 要塞の重要度
                    importance = self.evaluator.BASE_IMPORTANCE[neighbor]
                    
                    # 優先度を計算
                    priority = 70 + importance * 2 + probability * 35
                    
                    # 敵の部隊が少ない場合は優先
                    if enemy_troops < 8:
                        priority += 25
                    
                    # 終盤は攻撃を積極化（ただし成功率が高い場合のみ）
                    if game_phase == 'late' and probability >= 0.85:
                        priority += 30
                    
                    # 中央ハブを取れる場合は優先（十分な確率で）
                    if neighbor in [4, 7] and probability >= 0.85:
                        priority += 80
                    
                    # 自分の部隊が多い場合は優先度を上げる
                    troop_advantage = (fort_troops - enemy_troops) / (enemy_troops + 1)
                    if troop_advantage > 1.5:  # 1.5倍以上の戦力差
                        priority += troop_advantage * 15
                    
                    actions.append((priority, 1, my_fort, neighbor))
        
        return actions
    
    def _defense_strategy(self, state: List, team: int, 
                         moving_pawns: List, spawning_pawns: List) -> List[Tuple]:
        """防御戦略"""
        actions = []
        my_fortresses = [i for i in range(12) if state[i][0] == team]
        enemy_team = 2 if team == 1 else 1
        
        # 攻撃されている要塞を検出
        under_attack = {}
        for pawn in moving_pawns:
            pawn_team, kind, from_, to, pos = pawn
            if pawn_team == enemy_team and state[to][0] == team:
                if to not in under_attack:
                    under_attack[to] = {'count': 0, 'threat': 0}
                under_attack[to]['count'] += 1
                # 脅威レベルを計算（部隊の攻撃力に基づく）
                under_attack[to]['threat'] += self.evaluator.ATTACK_POWER[kind]
        
        # 出撃予定の敵部隊も考慮
        for pawn in spawning_pawns:
            pawn_team, kind, count, from_, to, pos = pawn
            if pawn_team == enemy_team and state[to][0] == team:
                if to not in under_attack:
                    under_attack[to] = {'count': 0, 'threat': 0}
                under_attack[to]['count'] += 1
                under_attack[to]['threat'] += count * self.evaluator.ATTACK_POWER[kind] * 0.5
        
        # 攻撃されている要塞への援軍
        for target_fort, threat_info in under_attack.items():
            threat_level = threat_info['threat']
            attack_count = threat_info['count']
            
            # 現在の防御力
            current_defense = state[target_fort][3]
            
            # 援軍が必要か判定
            if threat_level > current_defense * 0.6:
                # 隣接する味方要塞から援軍
                neighbors = self.evaluator.ADJACENCY[target_fort]
                
                for my_fort in neighbors:
                    if state[my_fort][0] == team and state[my_fort][3] >= 6:
                        # 要塞の重要度
                        importance = self.evaluator.BASE_IMPORTANCE[target_fort]
                        
                        # 優先度を計算（脅威が大きいほど優先）
                        priority = 120 + threat_level * 2 + importance * 5 + attack_count * 15
                        
                        # 中央ハブは絶対に守る
                        if target_fort in [4, 7]:
                            priority += 150
                        
                        actions.append((priority, 1, my_fort, target_fort))
        
        return actions
    
    def _upgrade_strategy(self, state: List, team: int, 
                         game_phase: str, step: int) -> List[Tuple]:
        """アップグレード戦略"""
        actions = []
        my_fortresses = [i for i in range(12) if state[i][0] == team]
        
        for my_fort in my_fortresses:
            fort_level = state[my_fort][2]
            fort_troops = state[my_fort][3]
            fort_kind = state[my_fort][1]
            upgrade_time = state[my_fort][4]
            
            # アップグレード可能か確認
            if upgrade_time != -1 or fort_level >= 5:
                continue
            
            # アップグレードに必要な部隊数
            max_troops = self.evaluator.FORTRESS_LIMIT[fort_level]
            required_troops = max_troops // 2
            
            if fort_troops < required_troops:
                continue
            
            # 部隊がさらに余裕がある場合を優先
            troop_ratio = fort_troops / max_troops
            if troop_ratio < 0.6:
                continue
            
            # 要塞の重要度
            importance = self.evaluator.BASE_IMPORTANCE[my_fort]
            
            # 生産効率の改善度
            current_rate = self.evaluator._calculate_production_rate(fort_kind, fort_level)
            future_rate = self.evaluator._calculate_production_rate(fort_kind, fort_level + 1)
            efficiency_gain = future_rate - current_rate
            
            # 敵に隣接しているか（前線の要塞は優先）
            enemy_neighbors = sum(
                1 for n in self.evaluator.ADJACENCY[my_fort]
                if state[n][0] not in [0, team]
            )
            
            # 優先度を計算
            priority = 60 + importance * 4 + efficiency_gain * 5 + enemy_neighbors * 8
            
            # フェーズ別の調整
            if game_phase == 'early':
                # 序盤は重要拠点のみ
                if my_fort in [4, 7]:
                    priority += 80
                else:
                    priority -= 20
            elif game_phase == 'mid':
                # 中盤は積極的にアップグレード
                priority += 50
            else:  # late
                # 終盤は攻撃優先だが、余裕があればアップグレード
                priority -= 10
            
            # 部隊が溢れている場合は優先度を上げる
            if troop_ratio > 0.85:
                priority += 30
            
            # レベルが低い要塞を優先
            priority += (5 - fort_level) * 5
            
            actions.append((priority, 2, my_fort, 0))
        
        return actions
    
    def _reinforcement_strategy(self, state: List, team: int, 
                               game_phase: str) -> List[Tuple]:
        """部隊再配置戦略（後方から前線へ）"""
        actions = []
        my_fortresses = [i for i in range(12) if state[i][0] == team]
        enemy_team = 2 if team == 1 else 1
        
        for my_fort in my_fortresses:
            fort_troops = state[my_fort][3]
            fort_level = state[my_fort][2]
            max_troops = self.evaluator.FORTRESS_LIMIT[fort_level]
            
            # 部隊が溜まっているか
            if fort_troops < max_troops * 0.7:
                continue
            
            # この要塞が前線か後方か判定
            neighbors = self.evaluator.ADJACENCY[my_fort]
            enemy_neighbors = sum(
                1 for n in neighbors if state[n][0] == enemy_team
            )
            neutral_neighbors = sum(
                1 for n in neighbors if state[n][0] == 0
            )
            
            # 後方の安全な要塞（敵に隣接していない）
            if enemy_neighbors == 0 and neutral_neighbors == 0:
                # 前線の味方要塞を探す
                for neighbor in neighbors:
                    if state[neighbor][0] == team:
                        neighbor_enemies = sum(
                            1 for n in self.evaluator.ADJACENCY[neighbor]
                            if state[n][0] == enemy_team
                        )
                        neighbor_neutrals = sum(
                            1 for n in self.evaluator.ADJACENCY[neighbor]
                            if state[n][0] == 0
                        )
                        
                        # 隣接要塞が前線の場合
                        if neighbor_enemies > 0 or neighbor_neutrals > 0:
                            importance = self.evaluator.BASE_IMPORTANCE[neighbor]
                            
                            # 優先度を計算
                            priority = 50 + neighbor_enemies * 10 + importance * 3
                            
                            # 中盤以降は再配置を積極化
                            if game_phase in ['mid', 'late']:
                                priority += 20
                            
                            actions.append((priority, 1, my_fort, neighbor))
        
        return actions
    
    def _opportunistic_strategy(self, state: List, team: int, 
                               game_phase: str) -> List[Tuple]:
        """機会主義的戦略（弱った敵への攻撃など）"""
        actions = []
        my_fortresses = [i for i in range(12) if state[i][0] == team]
        enemy_team = 2 if team == 1 else 1
        
        for my_fort in my_fortresses:
            fort_troops = state[my_fort][3]
            fort_kind = state[my_fort][1]
            
            if fort_troops < 5:
                continue
            
            neighbors = self.evaluator.ADJACENCY[my_fort]
            
            for neighbor in neighbors:
                neighbor_team = state[neighbor][0]
                neighbor_troops = state[neighbor][3]
                neighbor_level = state[neighbor][2]
                
                # 部隊が極端に少ない要塞への攻撃
                if neighbor_team == enemy_team and neighbor_troops < 5:
                    travel_time = self.evaluator.estimate_travel_time(my_fort, neighbor, fort_kind)
                    success, probability = self.evaluator.evaluate_attack_success(
                        fort_troops, neighbor_troops, neighbor_level,
                        state[neighbor][1], travel_time, fort_kind
                    )
                    
                    if probability > 0.8:  # 高確率で勝てる
                        priority = 90 + self.evaluator.BASE_IMPORTANCE[neighbor] * 3
                        actions.append((priority, 1, my_fort, neighbor))
                
                # 中立で部隊が少ない要塞への拡張
                elif neighbor_team == 0 and neighbor_troops < 8:
                    if game_phase in ['mid', 'late']:
                        priority = 70 + self.evaluator.BASE_IMPORTANCE[neighbor] * 2
                        actions.append((priority, 1, my_fort, neighbor))
        
        return actions
    
    def select_best_action(self, actions: List[Tuple]) -> Tuple[int, int, int]:
        """
        最適な行動を選択
        
        Returns:
            (command, subject, to)
        """
        if not actions:
            return (0, 0, 0)
        
        # 優先度でソート
        actions.sort(reverse=True, key=lambda x: x[0])
        
        # 最高優先度の行動を選択
        _, command, subject, to = actions[0]
        
        # 履歴に追加
        self.history.append((command, subject, to))
        
        return (command, subject, to)
