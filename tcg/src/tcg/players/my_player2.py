from tcg.controller import Controller
from collections import deque

FORTRESS_LIMIT = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}
SPECIAL_FORTS = [4, 7]


class Myplayer2(Controller):
    def __init__(self):
        super().__init__()
        self.step = 0

    def team_name(self):
        return "Kensei v2"

    def update(self, info):
        team, state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        CENTER_HOLD = 14
        
        deg = [(len(state[i][5]), i) for i in range(12)]
        deg.sort(reverse=True)
        CENTERS = [deg[0][1], deg[1][1]]
        

        def has_adjacent_neutral(mf):
                for nb in state[mf][5]:
                      if state[nb][0] == 0:
                            return True
                return False
        # ---- 自分の砦とターゲットを作る ----
        my_forts = []
        targets = []
        for i in range(12):
            if state[i][0] == team:
                my_forts.append(i)
            else:
                targets.append(i)


        # ======================================================
        #  四角砦（特殊砦）奪取：中立でも敵でも最優先
        # ======================================================
        for t in SPECIAL_FORTS:
            if state[t][0] != team:  # 中立 or 敵
                tgt_owner = state[t][0]
                tgt_pawn = state[t][3]

                for mf in my_forts:
                    mf_state = state[mf]
                    my_pawn = mf_state[3]
                    to_set = mf_state[5]

                    if t in to_set:
                        # 追加：中央が薄いなら出兵しない（中央を守る）
                        if mf in CENTERS and my_pawn < CENTER_HOLD:
                            continue

                        # 中立
                        if tgt_owner == 0 and my_pawn * 0.5 > tgt_pawn:
                            return (1, mf, t)
                        # 敵
                        if tgt_owner != 0 and my_pawn * 0.25 > tgt_pawn:
                            return (1, mf, t)

        # ======================================================
        #  単独で奪取可能な通常砦（中立 or 敵）
        # ======================================================
        for t in targets:
            if t in SPECIAL_FORTS:
                continue

            tgt_owner = state[t][0]
            tgt_pawn = state[t][3]

            for mf in my_forts:
                mf_state = state[mf]
                my_pawn = mf_state[3]
                to_set = mf_state[5]

                if t in to_set:
                    # 追加：中央が薄いなら出兵しない（中央を守る）
                    if mf in CENTERS and my_pawn < CENTER_HOLD:
                        continue

                    # 中立
                    if tgt_owner == 0 and my_pawn * 0.45 > tgt_pawn:
                        return (1, mf, t)
                    # 敵
                    if tgt_owner != 0:
                            # 追加：隣接中立があるなら敵を後回し
                            if has_adjacent_neutral(mf):
                                continue
                            if my_pawn * 0.25 > tgt_pawn:
                                return (1, mf, t)
                                
        # ======================================================
        #  複数の味方の合計で落とせる砦（ 中立）
        # ======================================================
        for t in targets:
            if state[t][0] != 0:
                continue  # 中立のみ

            tgt_pawn = state[t][3]
            total = 0
            first_sender = None

            for mf in my_forts:
                mf_state = state[mf]
                if t in mf_state[5]:
                    if mf in CENTERS and mf_state[3] < CENTER_HOLD:
                        continue

                    total += mf_state[3] // 2
                    if first_sender is None:
                        first_sender = mf

            if first_sender is not None and total * 0.7 > tgt_pawn:
                return (1, first_sender, t)

        # ======================================================
        # 中央砦の保護
        #  - 中央砦 = 接続数（len(to_set)）が多い上位2つ
        #  - 中央が薄い(<=8)なら、攻撃より前に最優先で増援
        # ======================================================

        for c in CENTERS:
            if state[c][0] == team and state[c][3] <= 8:
                best = None
                best_pawn = -1
                for mf in my_forts:
                    if mf == c:
                        continue
                    if c in state[mf][5] and state[mf][3] > 10:
                        if state[mf][3] > best_pawn:
                            best_pawn = state[mf][3]
                            best = mf
                if best is not None:
                    return (1, best, c)

        # ======================================================
        #  複数の味方の合計で落とせる砦（ 敵）
        # ======================================================
        for t in targets:
            if state[t][0] == 0:
                continue

            tgt_pawn = state[t][3]
            total = 0
            first_sender = None  # senders[0] 相当（同じ意味）

            for mf in my_forts:
                mf_state = state[mf]
                if t in mf_state[5]:
                    # 追加：中央が薄いなら「合計攻撃の送信元」にしない
                    if mf in CENTERS and mf_state[3] < CENTER_HOLD:
                        continue

                    total += mf_state[3] // 2
                    if first_sender is None:
                        first_sender = mf

            if first_sender is not None and total * 0.7 > tgt_pawn:
                return (1, first_sender, t)

        # ======================================================
        #  強化
        # ======================================================
        for mf in my_forts:
            mf_state = state[mf]
            level = mf_state[2]
            pawn = mf_state[3]
            if pawn >= FORTRESS_LIMIT[level] and level < 5:
                return (2, mf, 0)

        # ======================================================
        #  前線（＝中立 or 敵 と隣接している味方拠点）
        # ======================================================
        frontline = []
        for mf in my_forts:
            to_set = state[mf][5]
            for nb in to_set:
                if state[nb][0] != team:
                    frontline.append(mf)
                    break

        # ======================================================
        # 前線に向けた増援（BFSルート、距離制限なし）
        # ======================================================
        if frontline:
            #_weak_front = min(frontline, key=lambda x: state[x][3])

            INF = 10**9
            dist = [INF] * 12
            next_step = [None] * 12

            q = deque()
            for f in frontline:
                dist[f] = 0
                q.append(f)

            while q:
                cur = q.popleft()
                cur_d = dist[cur] + 1
                for nb in state[cur][5]:
                    if dist[nb] == INF:
                        dist[nb] = cur_d
                        next_step[nb] = cur
                        q.append(nb)

            for mf in my_forts:
                if dist[mf] != INF and dist[mf] > 0:
                    if state[mf][3] > 5:
                        return (1, mf, next_step[mf])

        return (0, 0, 0)



