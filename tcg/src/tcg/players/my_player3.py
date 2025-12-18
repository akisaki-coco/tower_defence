from tcg.controller import Controller
from collections import defaultdict

class Myplayer3(Controller):
    def __init__(self):
        super().__init__()
        self.step = 0
        self.CAPACITY = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}
        self.cooldown = defaultdict(int)

    def team_name(self):
        return "Kensei_WIN"

    def update(self, info):
        my_team, raw_state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        forts = self._parse_state(raw_state)
        predicted = self._predict_future(forts, moving_pawns)

        my_forts = [f for f in forts if f["team"] == my_team]
        targets = [f for f in forts if f["team"] != my_team]

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
                "capacity": self.CAPACITY[d[2]]
            })
        return forts

    def _predict_future(self, forts, moving_pawns):
        """移動中の兵を考慮した未来予測"""
        pred = [f["pawns"] for f in forts]

        for p in moving_pawns:
            p_team, p_kind, p_from, p_to, p_pos = p
            if p_team == forts[p_to]["team"]:
                pred[p_to] += 1
            else:
                pred[p_to] -= 1 if p_kind == 1 else 0.7

        return pred

