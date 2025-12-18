"""
Strategic Targeting Strategy (High Priority)

1. 「兵士強化砦（Kind 1）」の取得優先度を極端に高く設定しました。
   中立だろうが敵だろうが、見つけ次第（勝てるなら）最優先で取りに行きます。
2. 兵站（バケツリレー）と溢れ防止機能は維持しています。
"""

from tcg.config import fortress_limit

class Strategy:
    def __init__(self):
        self.step = 0

    def get_fort_strength(self, fort_info):
        """部隊の強さを計算（種類補正あり）"""
        _, kind, _, pawns, _, _ = fort_info
        multiplier = 0.95 if kind == 1 else 0.65
        return pawns * multiplier

    def decide_action(self, state):
        self.step += 1
        
        my_forts = [i for i in range(12) if state[i][0] == 1]
        is_early_game = self.step < 2000

        actions = [] 

        for i in my_forts:
            info = state[i]
            neighbors = info[5]
            
            # パラメータ取得
            has_enemy_neighbor = any(state[n][0] == 2 for n in neighbors)
            current_level = info[2]
            upgrade_cost = fortress_limit[current_level] // 2
            max_pawns = fortress_limit[current_level]
            current_pawns = info[3]
            
            # 溢れ判定
            is_overflowing = current_pawns >= max_pawns * 0.9
            
            # 出撃可能な兵数（半分）
            sending_pawns = info[3] // 2
            
            # 自分の攻撃力
            my_attack_power = self.get_fort_strength([0, info[1], 0, sending_pawns, 0, 0])


            # ========================================================
            # 1. 攻撃判定 (Attack Logic)
            # ========================================================
            best_target = None
            best_score = -999

            if sending_pawns >= 3: 
                for n in neighbors:
                    target = state[n]
                    target_team = target[0]
                    target_pawns = target[3]
                    target_kind = target[1] # 0:普通, 1:強化
                    
                    # 序盤の中央無視
                    if is_early_game and n in [4, 7] and target_team == 0:
                        continue

                    # --- 勝てるかどうかの判定 ---
                    victory_threshold = target_pawns + 2.0
                    if target_team == 2: victory_threshold += 3.0
                    
                    is_winnable = (sending_pawns > target_pawns) and (my_attack_power > victory_threshold)
                    
                    allow_attack = is_winnable
                    if is_overflowing and target_team == 2:
                        allow_attack = True 
                    
                    if not allow_attack:
                        continue

                    # --- スコア計算 ---
                    score = 0
                    
                    if target_team == 0: # 中立
                        score = 100 - target_pawns
                        if is_early_game and len(state[n][5]) >= 4: score -= 50
                    elif target_team == 2: # 敵
                        score = 200
                        if target_pawns < 5: score += 50
                        if is_overflowing: score += 1000

                    # ★★★ 修正ポイント: 強化砦への執着 ★★★
                    if target_kind == 1:
                        score += 300  # ボーナスを倍増 (150 -> 300)
                        
                        # 敵が持っている強化砦は、放置すると危険なのでさらに優先
                        if target_team == 2:
                            score += 100

                    if score > best_score:
                        best_score = score
                        best_target = n

            if best_target is not None:
                actions.append((best_score, 1, i, best_target))
            
            # ========================================================
            # 2. アップグレード (Economy Logic)
            # ========================================================
            if current_level < 5 and info[4] == -1:
                if info[3] >= upgrade_cost:
                    if not has_enemy_neighbor:
                        return 2, i, 0
                    if is_overflowing and best_target is None:
                         return 2, i, 0
                
                if not has_enemy_neighbor and not is_overflowing:
                    continue

            # ========================================================
            # 3. バケツリレー (Logistics)
            # ========================================================
            threshold = 0.9 if has_enemy_neighbor else 0.4
            
            if current_pawns > max_pawns * threshold:
                for n in neighbors:
                    if state[n][0] == 1: 
                        if is_early_game and n in [4, 7]: continue
                        
                        if any(state[nn][0] == 2 for nn in state[n][5]):
                            # 強化砦を取りに行くための移動なら優先度を上げる
                            priority = 500 if is_overflowing else 60
                            actions.append((priority, 1, i, n))
                            break
                        
                        if is_overflowing:
                            actions.append((300, 1, i, n))

        if actions:
            actions.sort(key=lambda x: x[0], reverse=True)
            return actions[0][1], actions[0][2], actions[0][3]

        return 0, 0, 0
