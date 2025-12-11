"""
Strict Victory Strategy

「無駄死に」を完全に防ぐための戦略
1. 攻撃は「確実に制圧できる（ダメージ > 敵兵数 + バッファ）」場合のみ許可。
   「削り」目的の攻撃は、反撃のリスクがあるため禁止します。
2. 敵が近くにいても、攻撃できない（勝てない）場合は、無理せずアップグレードに回します。
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
            
            # 状況確認
            has_enemy_neighbor = any(state[n][0] == 2 for n in neighbors)
            current_level = info[2]
            upgrade_cost = fortress_limit[current_level] // 2
            
            # 出撃可能な兵数（半分）
            sending_pawns = info[3] // 2
            
            # 自分の攻撃力
            my_attack_power = self.get_fort_strength([0, info[1], 0, sending_pawns, 0, 0])

            # ========================================================
            # 1. 攻撃判定 (Attack Logic)
            # 先に攻撃できるかチェックするが、基準を「激辛」にする
            # ========================================================
            best_target = None
            best_score = 0

            if sending_pawns >= 3: # 最低3体はいないと動かない
                for n in neighbors:
                    target = state[n]
                    target_team = target[0]
                    target_pawns = target[3]
                    
                    # 序盤の中央(4, 7)は絶対無視
                    if is_early_game and n in [4, 7] and target_team == 0:
                        continue

                    # 【重要】物理的な兵数チェック（絶対条件）
                    # 送る兵数が、敵の兵数より少なければ門前払い（相殺されるだけなので）
                    if sending_pawns <= target_pawns:
                        continue

                    # 【重要】ダメージ計算（勝利条件）
                    # 確実に制圧できるか？ (敵兵数 + マージン2体) を上回る必要がある
                    victory_threshold = target_pawns + 2.0
                    
                    # 敵(赤)の場合は、増援が来るリスクがあるのでさらに厳しく
                    if target_team == 2:
                        victory_threshold += 3.0

                    # 攻撃力が足りないなら攻撃しない
                    if my_attack_power <= victory_threshold:
                        continue

                    # スコア計算
                    score = 0
                    if target_team == 0: # 中立
                        score = 100 - target_pawns
                        if is_early_game and len(state[n][5]) >= 4: score -= 50
                    elif target_team == 2: # 敵
                        score = 200
                        # 敵が手薄ならチャンス
                        if target_pawns < 5: score += 50

                    if score > best_score:
                        best_score = score
                        best_target = n

            # 攻撃ターゲットが見つかったら、それを候補に入れる
            if best_target is not None:
                actions.append((best_score, 1, i, best_target))
                # 攻撃できるなら、アップグレードは後回し（continueしない）
            
            # ========================================================
            # 2. アップグレード (Economy Logic)
            # 攻撃する相手がいない、または勝てない場合
            # ========================================================
            if current_level < 5 and info[4] == -1:
                # コストが足りているなら
                if info[3] >= upgrade_cost:
                    # 敵が近くにいないなら、即アップグレード（優先度 最高）
                    if not has_enemy_neighbor:
                        return 2, i, 0
                    
                    # 【追加】敵が近くにいても、攻撃できない＆兵が溢れそうならアップグレード
                    # (座して死ぬよりは生産力を上げたほうがいい)
                    elif info[3] >= fortress_limit[current_level] * 0.9:
                        return 2, i, 0
                
                # 敵がいないなら、兵を貯めるためにここで終了（攻撃アクションを無効化）
                if not has_enemy_neighbor:
                    continue

            # ========================================================
            # 3. 兵站 (Logistics)
            # ========================================================
            if not has_enemy_neighbor and current_level == 5:
                if info[3] > fortress_limit[5] * 0.2:
                    for n in neighbors:
                        if state[n][0] == 1: 
                            if is_early_game and n in [4, 7]: continue
                            if any(state[nn][0] == 2 for nn in state[n][5]):
                                actions.append((50, 1, i, n))
                                break

        if actions:
            actions.sort(key=lambda x: x[0], reverse=True)
            return actions[0][1], actions[0][2], actions[0][3]

        return 0, 0, 0
