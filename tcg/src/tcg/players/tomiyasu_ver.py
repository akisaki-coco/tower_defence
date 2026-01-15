from tcg.controller import Controller
from collections import defaultdict

class CursorStrategist(Controller):
    def __init__(self):
        super().__init__()
        self.step = 0
        self.LIMIT = [10, 10, 20, 30, 40, 50]
        self.COOL = [
            [60, 60, 54, 48, 42, 35],  # Circle (kind 0)
            [90, 90, 81, 72, 63, 54]   # Square (kind 1)
        ]
        self.cooldown = defaultdict(int)

    def team_name(self):
        return "CursorStrategist_v3"

    def update(self, info):
        my_team, raw_state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        forts = self._parse_state(raw_state)
        predicted = self._predict_future(forts, moving_pawns, spawning_pawns)

        my_forts = [f for f in forts if f["team"] == my_team]
        enemies = [f for f in forts if f["team"] != my_team and f["team"] != 0]
        neutrals = [f for f in forts if f["team"] == 0]

        # ======================================================
        # 1. 緊急防衛（未来で落ちる拠点を守る）
        # ======================================================
        for mf in my_forts:
            if predicted[mf["id"]] < 5:  # 防衛しきい値を引き上げ
                helpers = [
                    f for f in my_forts
                    if mf["id"] in f["neighbors"]
                    and f["id"] != mf["id"]
                    and f["pawns"] > 5
                    and self.cooldown[f["id"]] <= self.step
                ]
                if helpers:
                    h = max(helpers, key=lambda f: f["pawns"])
                    self.cooldown[h["id"]] = self.step + 5
                    return (1, h["id"], mf["id"])

        # ======================================================
        # 2. 集中攻撃（中立 > 弱い敵）
        # ======================================================
        targets = neutrals + enemies
        # 狙いやすさでソート（中立優先、次に予測兵数が少ない順）
        targets.sort(key=lambda f: (f["team"] != 0, predicted[f["id"]]))

        for tgt in targets:
            tid = tgt["id"]
            attackers = [
                f for f in my_forts
                if tid in f["neighbors"]
                and f["pawns"] > 4 # より少ない兵数でも攻撃参加を検討
                and self.cooldown[f["id"]] <= self.step
            ]

            if not attackers:
                continue

            total_attack_power = sum(f["pawns"] // 2 for f in attackers)
            
            # 攻撃判定を強気に
            # 中立拠点なら即座に、敵拠点なら少し多めに送る
            needed = predicted[tid] + (2 if tgt["team"] == 0 else 5)

            if total_attack_power > needed:
                # 兵が多い砦から順に殴る
                attackers.sort(key=lambda f: f["pawns"], reverse=True)
                a = attackers[0]
                self.cooldown[a["id"]] = self.step + 8 # クールダウンを短縮
                return (1, a["id"], tid)

        # ======================================================
        # 3. 拡張（アップグレード）
        # ======================================================
        for mf in my_forts:
            # アップグレード中ではない、かつレベル5未満
            if raw_state[mf["id"]][4] == -1 and mf["level"] < 5:
                # 兵数が上限の半分以上必要 (Game.upgrade 参照)
                cost = self.LIMIT[mf["level"]] // 2
                if mf["pawns"] > cost + 8: # 余裕を持って
                    # 周辺に敵が少ない、または自分が圧倒している場合
                    danger = sum(
                        forts[n]["pawns"] for n in mf["neighbors"]
                        if forts[n]["team"] not in (0, my_team)
                    )
                    if danger < mf["pawns"] * 0.4:
                        return (2, mf["id"], 0)

        # ======================================================
        # 4. 兵員輸送（溢れそうな時だけ）
        # ======================================================
        for mf in my_forts:
            if mf["pawns"] > self.LIMIT[mf["level"]] * 0.9 and self.cooldown[mf["id"]] <= self.step:
                # 敵に隣接していない砦から、敵に隣接している砦へ送る
                is_frontline = any(forts[n]["team"] not in (0, my_team) for n in mf["neighbors"])
                if not is_frontline:
                    # 隣接する味方砦の中で、一番前線に近い（または兵が少ない）ところへ送る
                    neighbors_my_forts = [forts[n] for n in mf["neighbors"] if forts[n]["team"] == my_team]
                    if neighbors_my_forts:
                        target_f = min(neighbors_my_forts, key=lambda f: f["pawns"])
                        self.cooldown[mf["id"]] = self.step + 10
                        return (1, mf["id"], target_f["id"])

        return (0, 0, 0)

    # ======================================================
    # 内部処理
    # ======================================================
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
                "capacity": self.LIMIT[d[2]]
            })
        return forts

    def _predict_future(self, forts, moving_pawns, spawning_pawns):
        """移動中・出撃中の兵を考慮した未来予測"""
        pred = [f["pawns"] for f in forts]

        # 移動中の兵
        for p in moving_pawns:
            p_team, p_kind, p_from, p_to, p_pos = p
            if p_team == forts[p_to]["team"]:
                pred[p_to] += 1
            else:
                damage = 0.65 if p_kind == 0 else 0.95
                pred[p_to] -= damage
        
        # 出撃待機中の兵
        for s in spawning_pawns:
            s_team, s_kind, s_num, s_from, s_to, s_pos = s
            if s_team == forts[s_to]["team"]:
                pred[s_to] += s_num
            else:
                damage = 0.65 if s_kind == 0 else 0.95
                pred[s_to] -= s_num * damage

        return pred
