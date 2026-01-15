from tcg.controller import Controller
from collections import defaultdict

class AdaptiveChampion(Controller):
    def __init__(self):
        super().__init__()
        self.step = 0

        # 相手行動観測
        self.enemy_attack = 0
        self.enemy_upgrade = 0
        self.enemy_moves = 0

        self.enemy_type = "UNKNOWN"
        self.last_enemy_forts = None

        self.cooldown = defaultdict(int)
        self.CAPACITY = {1:10, 2:20, 3:30, 4:40, 5:50}

    def team_name(self):
        return "ADAPTIVE_CHAMPION"

    def update(self, info):
        team, raw_state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        forts = self._parse_state(raw_state)
        my_forts = [f for f in forts if f["team"] == team]
        enemy_forts = [f for f in forts if f["team"] not in (0, team)]

        # ===============================
        # 相手戦略の観測
        # ===============================
        if self.last_enemy_forts:
            for f in enemy_forts:
                prev = self.last_enemy_forts.get(f["id"])
                if prev:
                    if f["level"] > prev["level"]:
                        self.enemy_upgrade += 1
                    if f["pawns"] < prev["pawns"] - 2:
                        self.enemy_attack += 1
        self.enemy_moves += len(moving_pawns)
        self.last_enemy_forts = {f["id"]: f for f in forts}

        # ===============================
        # 相手タイプ判定（序盤）
        # ===============================
        if self.step == 80:
            if self.enemy_upgrade >= 2 and self.enemy_attack < 3:
                self.enemy_type = "TURTLE"   # HD2_WIN 系
            elif self.enemy_attack >= 4:
                self.enemy_type = "RUSH"
            else:
                self.enemy_type = "RANDOM"

        # ===============================
        # 共通：未来予測
        # ===============================
        predicted = self._predict_future(forts, moving_pawns)

        # ===============================
        # TURTLE 対策（HD2_WINメタ）
        # ===============================
        if self.enemy_type == "TURTLE":
            # 1. upgrade 直前拠点を叩く
            targets = sorted(
                enemy_forts,
                key=lambda f: (f["level"], predicted[f["id"]])
            )
            for tgt in targets:
                attackers = [
                    f for f in my_forts
                    if tgt["id"] in f["neighbors"]
                    and f["pawns"] > 8
                    and self.cooldown[f["id"]] <= self.step
                ]
                if len(attackers) >= 2:
                    a = max(attackers, key=lambda f: f["pawns"])
                    self.cooldown[a["id"]] = self.step + 8
                    return (1, a["id"], tgt["id"])

        # ===============================
        # RUSH 対策
        # ===============================
        if self.enemy_type == "RUSH":
            # 中央強化＋迎撃
            for f in my_forts:
                if f["level"] < 4 and f["pawns"] > f["capacity"] * 0.8:
                    return (2, f["id"], 0)

            for f in my_forts:
                if predicted[f["id"]] <= 1:
                    helpers = [
                        h for h in my_forts
                        if f["id"] in h["neighbors"]
                        and h["pawns"] > 6
                    ]
                    if helpers:
                        h = max(helpers, key=lambda x: x["pawns"])
                        return (1, h["id"], f["id"])

        # ===============================
        # 勝ち筋管理（終盤）
        # ===============================
        my_cnt = len(my_forts)
        enemy_cnt = len(enemy_forts)

        if self.step > 300:
            if my_cnt < enemy_cnt:
                # 負けてる → 多点同時攻撃
                for f in my_forts:
                    for n in f["neighbors"]:
                        if forts[n]["team"] != team and f["pawns"] > 10:
                            return (1, f["id"], n)
            else:
                # 勝ってる → 守る
                for f in my_forts:
                    if f["level"] < 5 and f["pawns"] > f["capacity"] * 0.9:
                        return (2, f["id"], 0)

        # ===============================
        # 通常：弱点集中攻撃
        # ===============================
        targets = sorted(
            enemy_forts,
            key=lambda f: predicted[f["id"]]
        )
        for tgt in targets:
            attackers = [
                f for f in my_forts
                if tgt["id"] in f["neighbors"]
                and f["pawns"] > 6
                and self.cooldown[f["id"]] <= self.step
            ]
            if attackers:
                a = max(attackers, key=lambda f: f["pawns"])
                self.cooldown[a["id"]] = self.step + 10
                return (1, a["id"], tgt["id"])

        return (0, 0, 0)

    # ===============================
    # 内部関数
    # ===============================
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
            team, kind, _, to, _ = p
            if team == forts[to]["team"]:
                pred[to] += 1
            else:
                pred[to] -= 1 if kind == 1 else 0.7
        return pred
