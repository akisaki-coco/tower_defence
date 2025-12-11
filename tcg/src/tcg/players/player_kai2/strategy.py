"""
strategy.py - Kai Player Ver.14 (ハブ要塞パンク防止版)
"""
HARD_LIMITS = [10, 10, 20, 30, 40, 50]

class Strategy:
    def __init__(self):
        pass

    def check_upgrade(self, fortress_state) -> bool:
        """アップグレード判定"""
        team, kind, level, pawn_number, upgrade_time, neighbors = fortress_state[0:6]
        
        if level >= len(HARD_LIMITS) or level >= 5: return False
        
        next_limit = HARD_LIMITS[level + 1] if level + 1 < len(HARD_LIMITS) else 50
        cost = next_limit // 2

        if pawn_number < cost: return False
        if upgrade_time > 0: return False
        
        limit = HARD_LIMITS[level]

        # Lv1: 即上げ
        if level == 1: return pawn_number >= cost
        # Lv2: 80%溜まるまで我慢
        if level == 2: return pawn_number >= limit * 0.8
        # Lv3, 4: 90%溜まるまで我慢
        if level >= 3: return pawn_number >= limit * 0.9

        return False

    def find_easy_win(self, state, fortress_id) -> int | None:
        """ハイエナ判定"""
        my_fortress = state[fortress_id]
        level = my_fortress[2]
        my_pawns = my_fortress[3]
        attack_force = my_pawns // 2
        
        if level < 5: return None
        limit = HARD_LIMITS[level]
        
        # 防衛分(40%)は残す
        if my_pawns < limit * 0.4: return None 

        for nid in my_fortress[5]:
            n_state = state[nid]
            if n_state[0] != 1:
                if n_state[3] < 5 and attack_force > n_state[3] + 2:
                    return nid
        return None

    def find_attack_target(self, state, fortress_id) -> int | None:
        """攻撃対象の選定"""
        my_fortress = state[fortress_id]
        level = my_fortress[2]
        limit = HARD_LIMITS[level]
        my_pawns = my_fortress[3]
        
        if level < 5: return None
        # Lv5でも80%未満なら攻撃禁止
        if my_pawns < limit * 0.8: return None

        attack_force = my_pawns // 2
        neighbors = my_fortress[5]
        
        candidates = []
        for nid in neighbors:
            n_state = state[nid]
            n_team, n_pawns = n_state[0], n_state[3]
            score = -9999

            if n_team == 2: # 敵
                if n_pawns > 30: score = 50 # 硬い敵は後回し
                elif attack_force > n_pawns * 1.2: 
                    score = 200 + (100 - n_pawns)
            elif n_team == 0: # 中立
                if attack_force > n_pawns:
                    score = 100 - n_pawns
            
            if score > -9999: candidates.append((score, nid))
        
        if not candidates: return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def find_reinforce_target(self, state, fortress_id) -> int | None:
        """後方支援 (Lv3以上限定版)"""
        my_fortress = state[fortress_id]
        my_level = my_fortress[2]
        my_limit = HARD_LIMITS[my_level]
        my_pawns = my_fortress[3]

        if my_level < 5: return None
        if my_pawns < my_limit * 0.4: return None # 防衛40%確保
        
        neighbors = my_fortress[5]
        is_front_line = any(state[nid][0] == 2 for nid in neighbors)
        if is_front_line: return None

        best_target = None
        min_pawn_ratio = 1.0

        for nid in neighbors:
            target = state[nid]
            if target[0] == 1: # 味方
                t_level = target[2]
                
                # --- 【修正】Lv1, Lv2 への輸送を禁止 ---
                # 容量不足で事故るため、自力で育つのを待つか、
                # 攻撃部隊がそのまま駐留して防衛・強化する形式にする。
                if t_level < 3:
                    continue

                if t_level >= len(HARD_LIMITS): continue
                t_limit = HARD_LIMITS[t_level]
                
                # 60%未満なら送る
                if target[3] < t_limit * 0.6:
                    pawn_ratio = target[3] / t_limit
                    if pawn_ratio < min_pawn_ratio:
                        min_pawn_ratio = pawn_ratio
                        best_target = nid
                        
        return best_target
