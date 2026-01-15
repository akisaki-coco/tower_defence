from tcg.controller import Controller
from collections import defaultdict

class Myplayer6(Controller):
    def __init__(self):
        super().__init__()
        self.step = 0
        self.CAPACITY = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}
        self.cooldown = defaultdict(int)

    def team_name(self):
        return "Iron_Turtle"  # 鉄壁の亀

    def update(self, info):
        my_team, raw_state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        forts = self._parse_state(raw_state)
        predicted = self._predict_future(forts, moving_pawns)

        my_forts = [f for f in forts if f["team"] == my_team]
        targets = [f for f in forts if f["team"] != my_team]
        
        early = (len(my_forts) < 4)
        
        # 行動可能な自分の拠点（クールダウン中でない）
        active_forts = [f for f in my_forts if self.cooldown[f["id"]] <= self.step]
        
        if early:
            # ======================================================
            # 1. 集中攻撃（中立 > 弱い敵）
            # ======================================================
            targets.sort(key=lambda f: (f["team"] != 0, predicted[f["id"]]))
    
            for tgt in targets:
                tid = tgt["id"]
                attackers = [
                    f for f in my_forts
                    if tid in f["neighbors"]
                    and f["pawns"] > 6
                    and self.cooldown[f["id"]] <= self.step
                ]

                if not attackers:
                    continue

                total = sum(f["pawns"] // 2 for f in attackers)
                need = predicted[tid] + 2

                if total > need * 1.1:
                    # 兵が多い砦から順に殴る
                    attackers.sort(key=lambda f: f["pawns"], reverse=True)
                    a = attackers[0]
                    self.cooldown[a["id"]] = self.step + 10
                    return (1, a["id"], tid)

            # ======================================================
            # 2. 緊急防衛（未来で落ちる拠点を守る）
            # ======================================================
            for mf in my_forts:
                if predicted[mf["id"]] <= 1:
                    helpers = [
                        f for f in my_forts
                        if mf["id"] in f["neighbors"]
                        and f["id"] != mf["id"]
                        and f["pawns"] > 8
                        and self.cooldown[f["id"]] <= self.step
                    ]
                    if helpers:
                        h = max(helpers, key=lambda f: f["pawns"])
                        self.cooldown[h["id"]] = self.step + 8
                        return (1, h["id"], mf["id"])

            # ======================================================
            # 3. 拡張（安全なアップグレード）
            # ======================================================
            for mf in my_forts:
                if mf["level"] < 5 and mf["pawns"] > mf["capacity"] * 0.75:
                    danger = any(
                        forts[n]["team"] not in (0, my_team)
                        for n in mf["neighbors"]
                    )
                    if not danger:
                        return (2, mf["id"], 0)

            return (0, 0, 0)

      
        
        
        # ======================================================
        # 1. 緊急防衛 (Emergency Defense)
        # ======================================================
        # 予測兵数が「危険域（キャパの20%未満）」になっている拠点を最優先で救う
        for target in my_forts:
            if predicted[target["id"]] < target["capacity"] * 0.2:
                # 助けに行ける隣接拠点を探す
                helpers = [
                    f for f in active_forts
                    if target["id"] in f["neighbors"]
                    and f["id"] != target["id"]
                    and f["pawns"] > f["capacity"] * 0.4 # ある程度余裕がある場所から
                ]
                if helpers:
                    # 最も兵が多い拠点から救援
                    helper = max(helpers, key=lambda x: x["pawns"])
                    self.cooldown[helper["id"]] = self.step + 5
                    return (1, helper["id"], target["id"])

        # ======================================================
        # 2. 内政強化 (Upgrade) - 最優先行動
        # ======================================================
        # 兵が溜まっているなら、攻撃よりアップグレードを優先する
        for f in active_forts:
            if f["level"] < 4:
                # アップグレード条件: 
                # 1. コスト(キャパの半分)を払っても安全な量がある
                # 2. 周囲に敵が少ない、または自分の兵が十分多い
                cost = self.CAPACITY[f["level"]] // 2
                if f["pawns"] >= cost + 2: # コスト+αあれば即実行
                    # アップグレード実行
                    self.cooldown[f["id"]] = self.step + 10
                    return (2, f["id"], 0)

        # ======================================================
        # 3. 余剰兵の運用 (Overflow Management)
        # ======================================================
        # アップグレードもできず、兵が上限(90%)に達しそうな場合のみ動く
        full_forts = [f for f in active_forts if f["pawns"] >= f["capacity"] * 0.9]
        
        for f in full_forts:
            neighbors = f["neighbors"]
            
            # A. 味方への輸送 (Reinforce Ally)
            # レベル上げ直後で兵が減っている味方などを補充する
            allies = [n for n in neighbors if forts[n]["team"] == my_team]
            needy_allies = [
                n for n in allies 
                if forts[n]["pawns"] < forts[n]["capacity"] * 0.8 # 満タンじゃない味方
            ]
            
            if needy_allies:
                # 一番兵が少ない味方へ送る
                target_id = min(needy_allies, key=lambda x: forts[x]["pawns"])
                self.cooldown[f["id"]] = self.step + 5
                return (1, f["id"], target_id)

            # B. 安全な拡張 (Safe Expansion)
            # 味方に送る場所もない場合、確実に勝てる中立か敵を狙う
            enemies = [n for n in neighbors if forts[n]["team"] != my_team]
            if enemies:
                # 自分の今の兵力の半分で、相手を確実に倒せる場合のみ攻撃
                # (相手の兵数 + 5 の余裕を見る)
                safe_targets = [
                    n for n in enemies
                    if predicted[n]  < (f["pawns"] // 2) * 0.65 # 攻撃減衰も考慮
                ]
                if safe_targets:
                    # 一番弱い敵を狙う
                    target_id = min(safe_targets, key=lambda x: predicted[x])
                    self.cooldown[f["id"]] = self.step + 10
                    return (1, f["id"], target_id)

        # 何もしない (Wait)
        return (0, 0, 0)

    # ----------------------------------------------------------
    # ユーティリティ (Myplayer3と同様)
    # ----------------------------------------------------------
    def _parse_state(self, raw_state):
        forts = []
        for i, d in enumerate(raw_state):
            forts.append({
                "id": i,
                "team": d[0],
                "kind": d[1],
                "level": d[2],
                "pawns": d[3],
                "neighbors": d[5],
                "capacity": self.CAPACITY[d[2]]
            })
        return forts

    def _predict_future(self, forts, moving_pawns):
        pred = [f["pawns"] for f in forts]
        for p in moving_pawns:
            p_team, p_kind, p_from, p_to, p_pos = p
            if p_team == forts[p_to]["team"]:
                pred[p_to] += 1
            else:
                pred[p_to] -= 1 if p_kind == 1 else 0.7
        return pred
