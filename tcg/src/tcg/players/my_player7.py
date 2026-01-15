from tcg.controller import Controller
from collections import defaultdict

class Myplayer7(Controller):
    def __init__(self):
        super().__init__()
        self.step = 0
        self.CAPACITY = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}
        self.cooldown = defaultdict(int)

    def team_name(self):
        return "Late_Bloomer_Lv4"  # レベル4から本気出す

    def update(self, info):
        my_team, raw_state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        forts = self._parse_state(raw_state)
        predicted = self._predict_future(forts, moving_pawns)

        my_forts = [f for f in forts if f["team"] == my_team]
        active_forts = [f for f in my_forts if self.cooldown[f["id"]] <= self.step]

        # ======================================================
        # 1. 緊急防衛 (Emergency Defense)
        # ======================================================
        # これは死守します。ただし、レベル4未満の拠点は「自分の身を守る」だけで精一杯とし、
        # 他への救援は「レベル4以上の余裕ある拠点」のみが行うように制限します。
        for target in my_forts:
            if predicted[target["id"]] < target["capacity"] * 0.2:
                helpers = [
                    f for f in active_forts
                    if target["id"] in f["neighbors"]
                    and f["id"] != target["id"]
                    and f["level"] >= 4  # 【変更点】救援出すのはLv4以上だけ
                    and f["pawns"] > f["capacity"] * 0.5 
                ]
                if helpers:
                    helper = max(helpers, key=lambda x: x["pawns"])
                    self.cooldown[helper["id"]] = self.step + 5
                    return (1, helper["id"], target["id"])

        # ======================================================
        # 2. 最優先：アップグレード (Upgrade Logic)
        # ======================================================
        # レベル4未満なら、何をおいてもアップグレードを目指します。
        for f in active_forts:
            if f["level"] < 5:
                cost = self.CAPACITY[f["level"]] // 2
                # コストが払えて、かつ「今すぐ死なない」なら即座に投資
                if f["pawns"] >= cost + 2:
                    self.cooldown[f["id"]] = self.step + 10
                    return (2, f["id"], 0)

        # ======================================================
        # 3. レベル別行動ロジック (Level-based Strategy)
        # ======================================================
        for f in active_forts:
            current_pawns = f["pawns"]
            cap = f["capacity"]
            lvl = f["level"]

            # 行動を開始する「しきい値」を決定
            if lvl < 4:
                # レベル4未満：
                # 兵があふれる寸前(100%)になるまで動かない。
                # あふれるとゲームのルールで兵が消滅するので、その直前だけ排出する。
                threshold = cap
            else:
                # レベル4以上：
                # キャパの80%が溜まったら積極的に動き出す。
                threshold = cap * 0.8

            # しきい値を超えていなければ何もしない（待機して兵を貯める）
            if current_pawns < threshold:
                continue

            # --- ここから下は「動く」と決めた場合のロジック ---

            neighbors = f["neighbors"]

            # A. 味方への支援 (Reinforce)
            # レベル4以上の拠点から、まだ育っていない味方(Lv<4)へ兵を「輸出」して育てる
            allies = [n for n in neighbors if forts[n]["team"] == my_team]
            weak_allies = [
                n for n in allies 
                if forts[n]["level"] < 4 and forts[n]["pawns"] < forts[n]["capacity"] * 0.8
            ]
            
            if weak_allies:
                # 一番レベルが低い味方を優先して手伝う
                target_id = min(weak_allies, key=lambda x: (forts[x]["level"], forts[x]["pawns"]))
                self.cooldown[f["id"]] = self.step + 5
                return (1, f["id"], target_id)

            # B. 攻撃 / 拡張 (Attack / Expansion)
            # 支援先がない場合、攻撃に出る
            enemies = [n for n in neighbors if forts[n]["team"] != my_team]
            if enemies:
                # 勝てる相手を探す
                # Lv4以上なら多少強気に(1.2倍)、Lv4未満の緊急排出なら確実な相手(2.0倍)を選ぶ
                safety_margin = 1.2 if lvl >= 4 else 2.0
                
                targets = []
                for eid in enemies:
                    enemy_strength = predicted[eid]
                    # 自分の放出量(半分) * 攻撃減衰(0.65) > 敵兵力 * マージン
                    my_power = (current_pawns // 2) * 0.65
                    if my_power > enemy_strength * safety_margin:
                        targets.append(eid)
                
                if targets:
                    # 一番弱い敵を狙う
                    target_id = min(targets, key=lambda x: predicted[x])
                    self.cooldown[f["id"]] = self.step + 10
                    return (1, f["id"], target_id)

        # 何もしない
        return (0, 0, 0)

    # ----------------------------------------------------------
    # ユーティリティ
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
