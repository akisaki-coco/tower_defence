from tcg.controller import Controller
from collections import defaultdict

class Myplayer5(Controller):
    def __init__(self):
        super().__init__()
        self.step = 0
        self.CAPACITY = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}
        self.cooldown = defaultdict(int)

    # 【重要】このメソッドがない、あるいは名前が違うとエラーになります
    def team_name(self):
        return "HD2_SUPERIOR"

    def update(self, info):
        my_team, raw_state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        forts = self._parse_state(raw_state)
        predicted = self._predict_future(forts, moving_pawns)
        my_forts = [f for f in forts if f["team"] == my_team]
        
        if not my_forts: 
            return (0, 0, 0)

        # ------------------------------------------------------
        # 1. 最優先：緊急防衛
        # ------------------------------------------------------
        for mf in my_forts:
            if predicted[mf["id"]] < 2:  # 自分の拠点が落ちそうなら
                helpers = [f for f in my_forts if mf["id"] in f["neighbors"] 
                           and f["id"] != mf["id"] and f["pawns"] > 5
                           and self.cooldown[f["id"]] <= self.step]
                if helpers:
                    h = max(helpers, key=lambda x: x["pawns"])
                    self.cooldown[h["id"]] = self.step + 2
                    return (1, h["id"], mf["id"])

        # ------------------------------------------------------
        # 2. 攻撃ロジック：ターゲットを絞って波状攻撃
        # ------------------------------------------------------
        targets = [f for f in forts if f["team"] != my_team]
        # 中立(0)を最優先、次に兵が少ない敵を狙う
        targets.sort(key=lambda f: (f["team"] != 0, predicted[f["id"]]))

        for tgt in targets:
            tid = tgt["id"]
            attackers = [f for f in my_forts if tid in f["neighbors"] 
                         and self.cooldown[f["id"]] <= self.step]
            
            if not attackers: 
                continue

            # 敵の防御(0.65倍)を突破するために必要な兵力（敵の2倍＋余裕）
            required_to_start = (predicted[tid] * 2.0) + 5
            
            # 周辺味方拠点の「総兵力」で判定（1つ出撃しても追撃を止めないため）
            current_total_strength = sum(f["pawns"] for f in attackers)

            if current_total_strength > required_to_start:
                # 最も兵が多い拠点から出撃
                best_attacker = max(attackers, key=lambda x: x["pawns"])
                if best_attacker["pawns"] > 5:
                    self.cooldown[best_attacker["id"]] = self.step + 3
                    return (1, best_attacker["id"], tid)

        # ------------------------------------------------------
        # 3. 兵力循環（後方支援）とアップグレード
        # ------------------------------------------------------
        for mf in my_forts:
            is_frontline = any(forts[n]["team"] != my_team for n in mf["neighbors"])
            
            # 前線なら、Lv3までアップグレードして耐久を上げる
            if is_frontline and mf["level"] < 3 and mf["pawns"] >= mf["capacity"] * 0.8:
                return (2, mf["id"], 0)

            # 後方拠点：前線の「最も兵が少ない拠点」へ送る（押し出し）
            if not is_frontline and mf["pawns"] > mf["capacity"] * 0.4:
                front_allies = [forts[n] for n in mf["neighbors"] if forts[n]["team"] == my_team]
                if front_allies:
                    dest = min(front_allies, key=lambda x: x["pawns"])
                    if dest["pawns"] < dest["capacity"] * 0.9:
                        self.cooldown[mf["id"]] = self.step + 2
                        return (1, mf["id"], dest["id"])

        return (0, 0, 0)

    def _parse_state(self, raw_state):
        return [{"id": i, "team": d[0], "kind": d[1], "level": d[2], "pawns": d[3], "neighbors": d[5], "capacity": self.CAPACITY.get(d[2], 50)} for i, d in enumerate(raw_state)]

    def _predict_future(self, forts, moving_pawns):
        pred = [f["pawns"] for f in forts]
        for p in moving_pawns:
            p_team, p_kind, p_from, p_to, p_pos = p
            if p_team == forts[p_to]["team"]: 
                pred[p_to] += 1
            else: 
                pred[p_to] -= 1 if p_kind == 1 else 0.65
        return pred
