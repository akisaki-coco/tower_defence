"""
Taishi Rulebase V14 "Pressure Phantom"

Machined Player対策特化版。
中央での消耗戦を避け、外周・末端への分散圧力(Pressure)で敵兵站を崩壊させる。
また、行動可能判定のバグを修正し、安定性を確保。

主な変更点:
1. is_free(i): upgrade_time の判定を (<= 0) に統一し、バグを修正。
2. Importance Rebalance: 中央(4,7)の価値を下げ、外周(0-3, 9-11)を重視。
3. Stalemate Detection: 膠着状態を検知するロジックを追加。
4. Pressure Mode: 膠着時に「緩い分散圧力」を加え、敵を強制的に動かす。
"""

from tcg.controller import Controller
from collections import deque, defaultdict
import random

class TaishiRulebase(Controller):
    # ゲーム設定
    FORTRESS_LIMIT = [10, 10, 20, 30, 40, 50]
    
    # CHANGE: 戦略的価値マップの大幅変更
    # 中央(4, 7)はMachinedが死守するため、あえて価値を下げて無視する。
    # その代わり、補給線の末端や枝(0-3, 9-11)を重視し、外から崩す。
    FORTRESS_IMPORTANCE = {
        0: 30, 1: 30, 2: 30,   # 末端/枝 (価値増)
        3: 20, 
        4: 5,                 # 中央上 (価値減: 激戦区無視)
        5: 20,
        6: 20, 
        7: 5,                 # 中央下 (価値減: 激戦区無視)
        8: 20,
        9: 30, 10: 30, 11: 30  # 末端/枝 (価値増)
    }

    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        self.team = 0
        self.state = []
        self.adjacency = {}
        
        self.decoy_cooldown = 0
        
        # CHANGE: Stalemate / Pressure 管理用
        self.ownership_history = deque(maxlen=60)
        self.stalemate = False
        self.pressure_cooldown = 0
        self.last_pressure_target = -1
        self.last_pressure_hidden_power = 0

    def team_name(self) -> str:
        mode = "S" if self.stalemate else "N"
        return f"Taishi_Pressure_v14[{mode}]"

    # CHANGE: 行動可能判定の統一メソッド
    # README仕様準拠: 0=アップグレード可能, -1=初期/アイドル
    # これ以外の正の値はクールダウン中
    def is_free(self, i: int) -> bool:
        return self.state[i][4] <= 0

    def update(self, info) -> tuple[int, int, int]:
        self.team, self.state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        if done:
            return 0, 0, 0

        # --- 0. 戦況分析 ---
        my_id = self.team
        enemy_id = 2 if my_id == 1 else 1

        if not self.adjacency:
            for i in range(12):
                self.adjacency[i] = self.state[i][5]

        my_forts = [i for i in range(12) if self.state[i][0] == my_id]
        enemy_forts = [i for i in range(12) if self.state[i][0] == enemy_id]
        neutral_forts = [i for i in range(12) if self.state[i][0] == 0]
        
        # 距離マップ
        targets = enemy_forts + neutral_forts
        dist_to_front = self._calculate_distance_to_targets(targets if targets else list(range(12)))

        # 移動兵力計算 (Total War Awareness)
        incoming_friendly = defaultdict(int)
        incoming_hostile = defaultdict(int)
        enemy_hidden_power = defaultdict(int)

        all_pawns = moving_pawns + spawning_pawns
        for pawn in all_pawns:
            if len(pawn) == 5: # moving
                p_team, _, _, p_to, _ = pawn
                num = 1
            else: # spawning
                p_team, _, num, _, p_to, _ = pawn
            
            if p_team == my_id:
                incoming_friendly[p_to] += num
            else:
                incoming_hostile[p_to] += num
                if self.state[p_to][0] == enemy_id:
                    enemy_hidden_power[p_to] += num

        # --- CHANGE: 攻撃候補の先行評価 (Stalemate判定用) ---
        # まず通常の「本命攻撃(Synchro Strike)」が可能か計算する
        strike_candidates = []
        best_margin = 0
        potential_targets = neutral_forts + enemy_forts
        
        for t in potential_targets:
            t_hp = self.state[t][3] + enemy_hidden_power[t]
            t_imp = self.FORTRESS_IMPORTANCE[t]
            t_owner = self.state[t][0]
            
            total_power = 0
            attackers = []
            
            for n in self.state[t][5]:
                # CHANGE: is_free判定を使用
                if self.state[n][0] == my_id and self.is_free(n):
                    if incoming_hostile[n] == 0:
                        power = self.state[n][3] // 2
                        if power > 0:
                            attackers.append((n, power))
                            total_power += power
            
            if total_power == 0: continue

            ratio = 1.05 if t_owner == 0 else 1.2
            if total_power > t_hp * ratio:
                margin = total_power - t_hp
                score = 5000 + (t_imp * 20) + margin
                strike_candidates.append({
                    "target": t, "score": score, 
                    "attackers": attackers, "is_enemy": (t_owner == enemy_id)
                })
                if margin > best_margin:
                    best_margin = margin

        # --- CHANGE: 歪み検知 (Distortion Trigger) ---
        distortion_detected = False
        if self.last_pressure_target != -1:
            # 前回Pressureを撃った先の「隠し戦力(援軍)」が増えたか？
            current_hidden = enemy_hidden_power[self.last_pressure_target]
            if current_hidden > self.last_pressure_hidden_power:
                distortion_detected = True
        
        # --- CHANGE: Stalemate 判定 ---
        current_ownership = tuple([self.state[i][0] for i in range(12)])
        self.ownership_history.append(current_ownership)
        
        self.stalemate = False
        # データが溜まってから判定
        if len(self.ownership_history) >= 60:
            changes = 0
            old_state = self.ownership_history[0]
            for i in range(12):
                if old_state[i] != current_ownership[i]:
                    changes += 1
            
            # 条件: 盤面変化が少なく(<=2)、かつ決定打(margin>=6)がない
            if changes <= 2 and best_margin < 6:
                self.stalemate = True
        
        # 歪みを検知したら即解除 (本命を通すチャンス)
        if distortion_detected:
            self.stalemate = False
            self.last_pressure_target = -1

        # --- アクション生成 ---
        actions = []

        # A. Iron Dome (緊急防衛) Priority: 20000+
        for i in my_forts:
            curr = self.state[i][3]
            proj = curr + incoming_friendly[i]
            danger = incoming_hostile[i]
            
            if danger > proj:
                deficit = danger - proj
                prio = 20000 + deficit * 10
                
                for n in self.state[i][5]:
                    # CHANGE: is_free判定を使用
                    if self.state[n][0] == my_id and self.is_free(n):
                        # 余裕があるか
                        if incoming_hostile[n] == 0 and self.state[n][3] > 5:
                            actions.append((prio, 1, n, i))

        # --- CHANGE: Pressure Mode (緩い分散圧力) Priority: 9000 ---
        # 拮抗中のみ発動。本命攻撃(strike_candidates)が弱いときに、ジャブを打つ。
        if self.stalemate and self.pressure_cooldown == 0:
            pressure_targets = []
            
            # ターゲット選定: 敵が持っている中央拠点の「裏側」を狙う
            # 7(中央下)が敵なら {9,10,11}
            if self.state[7][0] == enemy_id:
                pressure_targets.extend([9, 10, 11])
            # 4(中央上)が敵なら {0,1,2,3}
            if self.state[4][0] == enemy_id:
                pressure_targets.extend([0, 1, 2, 3])
            
            # 該当がなければ全体から中立/敵を探す
            if not pressure_targets:
                pressure_targets = potential_targets

            pressure_candidates = []
            
            for t in pressure_targets:
                if t not in potential_targets: continue
                t_owner = self.state[t][0]
                t_true_hp = self.state[t][3] + enemy_hidden_power[t]
                
                # 攻撃元を探す
                for n in self.state[t][5]:
                    # CHANGE: is_free判定
                    if self.state[n][0] == my_id and self.is_free(n):
                        # 出撃制約: 敵の脅威が小さい & 最低保持数を残せる
                        if incoming_hostile[n] < 2:
                            curr = self.state[n][3]
                            send = curr // 2
                            remain = curr - send
                            min_hold = 8 # 最低保持数
                            
                            if remain >= min_hold:
                                # 最低成立条件チェック (無意味な攻撃は避ける)
                                thresh = 0.9 if t_owner == 0 else 0.6
                                if send > t_true_hp * thresh:
                                    # 敵を動かすのが目的なので、敵領土への攻撃を優先
                                    score = 9000 + send
                                    if t_owner == enemy_id: score += 100
                                    pressure_candidates.append((score, 1, n, t))
            
            if pressure_candidates:
                # 1つだけ採用
                pressure_candidates.sort(key=lambda x: x[0], reverse=True)
                best_p = pressure_candidates[0]
                actions.append(best_p)
                
                # 状態更新
                self.pressure_cooldown = 2 # 薄く長く (2ターンに1回)
                self.last_pressure_target = best_p[3]
                self.last_pressure_hidden_power = enemy_hidden_power[best_p[3]]

        if self.pressure_cooldown > 0:
            self.pressure_cooldown -= 1

        # B. Synchro Strike & Decoy (本命攻撃) Priority: 5000+
        if self.decoy_cooldown > 0: self.decoy_cooldown -= 1
        
        best_strike = None
        if strike_candidates:
            strike_candidates.sort(key=lambda x: x["score"], reverse=True)
            best_strike = strike_candidates[0]
            
            # Decoy (Pressureが出ていない時のみ)
            is_pressuring = (self.stalemate and actions and actions[-1][0] >= 9000)
            
            if not is_pressuring and best_strike["is_enemy"] and self.decoy_cooldown == 0:
                main_t = best_strike["target"]
                main_ids = [a[0] for a in best_strike["attackers"]]
                decoy_targets = [ef for ef in enemy_forts if ef != main_t]
                
                for dt in decoy_targets:
                    for n in self.state[dt][5]:
                        # CHANGE: is_free判定
                        if (self.state[n][0] == my_id and self.is_free(n)
                            and n not in main_ids 
                            and 3 <= self.state[n][3] <= 15):
                            actions.append((best_strike["score"] + 100, 1, n, dt))
                            self.decoy_cooldown = 3
                            break 
                    if actions: break

        # Pressureが出ていなければ本命登録
        has_pressure = any(9000 <= a[0] < 20000 for a in actions)
        
        if not has_pressure and best_strike:
            prio = best_strike["score"]
            t = best_strike["target"]
            for subj, _ in best_strike["attackers"]:
                actions.append((prio, 1, subj, t))

        # C. Logistics (兵站) Priority: 2000-4000
        for i in my_forts:
            # CHANGE: is_free判定
            if not self.is_free(i): continue
            
            cap = self.FORTRESS_LIMIT[self.state[i][2]]
            troops = self.state[i][3]
            
            threshold = cap * 0.8
            if troops >= threshold:
                candidates = []
                my_dist = dist_to_front[i]
                for n in self.state[i][5]:
                    if self.state[n][0] == my_id:
                        score = 0
                        n_dist = dist_to_front[n]
                        if n_dist < my_dist: score += 50
                        score += self.FORTRESS_IMPORTANCE[n]
                        score -= self.state[n][3]
                        candidates.append((n, score))
                
                if candidates:
                    candidates.sort(key=lambda x: x[1], reverse=True)
                    tgt = candidates[0][0]
                    prio = 2000 + troops
                    if troops >= cap - 1: prio += 2000
                    actions.append((prio, 1, i, tgt))

        # D. Investment (投資) Priority: 1500
        for i in my_forts:
            # CHANGE: is_free判定
            if not self.is_free(i): continue
            
            lv = self.state[i][2]
            if lv >= 5: continue
            
            cap = self.FORTRESS_LIMIT[lv]
            troops = self.state[i][3]
            cost = cap // 2
            
            if troops >= cost and incoming_hostile[i] == 0:
                prio = 1500 + lv * 100
                if self.FORTRESS_IMPORTANCE[i] >= 30: prio += 500
                actions.append((prio, 2, i, 0))

        # --- Final Decision ---
        if not actions:
            return 0, 0, 0
            
        actions.sort(key=lambda x: x[0], reverse=True)
        return actions[0][1], actions[0][2], actions[0][3]

    def _calculate_distance_to_targets(self, targets):
        dist = {i: 999 for i in range(12)}
        queue = deque()
        for t in targets:
            dist[t] = 0
            queue.append(t)
        while queue:
            u = queue.popleft()
            d = dist[u]
            if u in self.adjacency:
                for v in self.adjacency[u]:
                    if dist[v] > d + 1:
                        dist[v] = d + 1
                        queue.append(v)
        return dist