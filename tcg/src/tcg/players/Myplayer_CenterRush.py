from tcg.controller import Controller
from collections import defaultdict

CENTER = {4, 7}

class Myplayer_CenterRush(Controller):
    def __init__(self):
        super().__init__()
        self.step = 0
        self.CAPACITY = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}
        self.cooldown = defaultdict(int)

    def team_name(self):
        return "CENTER_RUSH"

    def update(self, info):
        my_team, raw_state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        forts = self._parse_state(raw_state)
        predicted = self._predict_future(forts, moving_pawns)

        my_forts = [f for f in forts if f["team"] == my_team]
        enemy_forts = [f for f in forts if f["team"] != my_team]

        # ==================================================
        # 1. 中央一点突破
        # ==================================================
        for cid in CENTER:
            tgt = forts[cid]
            if tgt["team"] == my_team:
                continue

            attackers = [
                f for f in my_forts
                if cid in f["neighbors"]
                and f["pawns"] > 8
                and self.cooldown[f["id"]] <= self.step
            ]

            if not attackers:
                continue

            attackers.sort(key=lambda f: f["pawns"], reverse=True)
            a = attackers[0]

            send = a["pawns"] // 2

            # 到達前の増援を見込む
            distance = 20
            future_gain = distance / 5
            need = predicted[cid] + future_gain + 3

            if send > need * 1.2:
                self.cooldown[a["id"]] = self.step + 15
                return (1, a["id"], cid)

        # ==================================================
        # 2. 中央防衛（取ったら最優先）
        # ==================================================
        for cid in CENTER:
            mf = forts[cid]
            if mf["team"] != my_team:
                continue

            if predicted[cid] < 5:
                helpers = [
                    f for f in my_forts
                    if cid in f["neighbors"]
                    and f["id"] != cid
                    and f["pawns"] > 10
                    and self.cooldown[f["id"]] <= self.step
                ]
                if helpers:
                    h = max(helpers, key=lambda f: f["pawns"])
                    self.cooldown[h["id"]] = self.step + 8
                    return (1, h["id"], cid)

        # ==================================================
        # 3. 中央へ通じる前線を掃除
        # ==================================================
        for f in enemy_forts:
            if any(c in f["neighbors"] for c in CENTER):
                for mf in my_forts:
                    if f["id"] in mf["neighbors"] and mf["pawns"] > f["pawns"] * 1.3:
                        return (1, mf["id"], f["id"])

        # ==================================================
        # 4. 後方のみアップグレード
        # ==================================================
        for mf in my_forts:
            if mf["level"] >= 5:
                continue
            if mf["pawns"] < mf["capacity"] * 0.9:
                continue

            if all(forts[n]["team"] == my_team for n in mf["neighbors"]):
                return (2, mf["id"], 0)

        # ==================================================
        # 5. 兵腐り防止
        # ==================================================
        for mf in my_forts:
            if mf["pawns"] > mf["capacity"] * 0.95:
                for n in mf["neighbors"]:
                    if forts[n]["team"] == my_team:
                        return (1, mf["id"], n)

        return (0, 0, 0)

    # ==================================================
    # 内部処理
    # ==================================================
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
            p_team, p_kind, _, to, _ = p
            if p_team == forts[to]["team"]:
                pred[to] += 1
            else:
                pred[to] -= 1 if p_kind == 1 else 0.65
        return pred

