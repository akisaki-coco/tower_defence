import math
from tcg.controller import Controller

class ver2(Controller):
    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        self.CAPACITIES = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}
        self.action_cooldowns = {}

    def team_name(self) -> str:
        return "Tactical_Coop_v2"

    def update(self, info) -> tuple[int, int, int]:
        my_team_id, raw_state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        # 1. データの整理（移動中の兵をシミュレートに加える）
        forts = self._parse_state(raw_state)
        predicted_pawns = self._predict_future(forts, moving_pawns, my_team_id)
        
        my_forts = [f for f in forts if f["team"] == my_team_id]
        targets = [f for f in forts if f["team"] != my_team_id] # 敵 or 中立

        # --------------------------------------------------
        # 戦略1: 【集中攻撃】 複数拠点から一斉に攻める
        # --------------------------------------------------
        # 落とせそうなターゲットを優先順位（中立 > 弱い敵 > 四角）でソート
        targets.sort(key=lambda x: (x["team"] != 0, x["pawns"], x["kind"] == 0))

        for target in targets:
            tid = target["id"]
            # そのターゲットに兵を送れる味方を探す
            attackers = [f for f in my_forts if tid in f["neighbors"]]
            
            if not attackers: continue

            # 攻撃に参加できる総兵力を計算（各砦の半分を送る想定）
            total_attack_power = sum(f["pawns"] // 2 for f in attackers)
            
            # 現在の敵兵 + すでに向かっている敵援軍（予測）を上回れるか？
            needed = predicted_pawns[tid] + 2 # 少し余裕を持つ
            
            if total_attack_power > needed:
                # 連携発動！まだクールダウン中でない味方から順に一人ずつ命令を出す
                for f in attackers:
                    if self.action_cooldowns.get(f["id"], 0) <= self.step and f["pawns"] > 5:
                        self.action_cooldowns[f["id"]] = self.step + 12
                        return 1, f["id"], tid

        # --------------------------------------------------
        # 戦略2: 【緊急防衛・補給】 狙われている味方を助ける
        # --------------------------------------------------
        for mf in my_forts:
            if predicted_pawns[mf["id"]] < 2: # 予測で落ちそうな味方拠点
                supporters = [f for f in my_forts if mf["id"] in f["neighbors"] and f["id"] != mf["id"]]
                for s in supporters:
                    if s["pawns"] > 10 and self.action_cooldowns.get(s["id"], 0) <= self.step:
                        self.action_cooldowns[s["id"]] = self.step + 8
                        return 1, s["id"], mf["id"]

        # --------------------------------------------------
        # 戦略3: 【内政】 アップグレード
        # --------------------------------------------------
        for mf in my_forts:
            if mf["level"] < 5 and not mf["is_upgrading"]:
                if mf["pawns"] > mf["capacity"] * 0.7:
                    # 周囲にすぐ攻めてきそうな敵がいなければ
                    if not any(forts[n]["team"] not in [0, my_team_id] for n in mf["neighbors"]):
                        return 2, mf["id"], 0

        return 0, 0, 0

    def _parse_state(self, raw_state):
        parsed = []
        for i, data in enumerate(raw_state):
            parsed.append({
                "id": i, "team": data[0], "kind": data[1], "level": data[2],
                "pawns": data[3], "is_upgrading": data[4] > 0, "neighbors": data[5],
                "capacity": self.CAPACITIES.get(data[2], 10)
            })
        return parsed

    def _predict_future(self, forts, moving_pawns, my_team):
        """移動中の兵を考慮した未来の兵数予測（簡易版）"""
        predictions = [f["pawns"] for f in forts]
        for p in moving_pawns:
            p_team, p_kind, p_from, p_to, p_pos = p
            damage = 0.95 if p_kind == 1 else 0.65
            if p_team == forts[p_to]["team"]:
                predictions[p_to] += 1
            else:
                predictions[p_to] -= damage
        return predictions
