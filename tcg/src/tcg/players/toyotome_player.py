from tcg.controller import Controller
from collections import deque

FORTRESS_LIMIT = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}
SPECIAL_FORTS = [4,7]  


class TemplatePlayer2(Controller):
    def __init__(self):
        super().__init__()
        self.step = 0

    def team_name(self):
        return "Toyotome_v2"

    def update(self, info):
        team, state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        my_forts = [i for i in range(12) if state[i][0] == team]
        targets = [i for i in range(12) if state[i][0] != team]  # 中立 + 敵 全部対象

        # ======================================================
        #  四角砦（特殊砦）奪取：中立でも敵でも最優先
        # ======================================================
        for t in SPECIAL_FORTS:
            if state[t][0] != team:  # 中立 or 敵
                tgt_pawn = state[t][3]
                for mf in my_forts:
                    my_pawn = state[mf][3]
                    if t in state[mf][5]:

                        # 中立
                        if state[t][0] == 0 and my_pawn * 0.5 > tgt_pawn:
                            return (1, mf, t)

                        # 敵
                        if state[t][0] != 0 and my_pawn * 0.25 > tgt_pawn:
                            return (1, mf, t)

        # ======================================================
        #  単独で奪取可能な通常砦（中立 or 敵）
        # ======================================================
        for t in targets:
            if t in SPECIAL_FORTS:
                continue  # 特殊砦は上で処理済み

            tgt_pawn = state[t][3]

            for mf in my_forts:
                my_pawn = state[mf][3]
                if t in state[mf][5]:

                    # 中立
                    if state[t][0] == 0 and my_pawn * 0.45 > tgt_pawn:
                        return (1, mf, t)

                    # 敵
                    if state[t][0] != 0 and my_pawn * 0.25 > tgt_pawn:
                        return (1, mf, t)

        # ======================================================
        #  複数の味方の合計で落とせる砦（中立 or 敵）
        # ======================================================
        for t in targets:
            tgt_pawn = state[t][3]
            total = 0
            senders = []

            for mf in my_forts:
                if t in state[mf][5]:
                    total += state[mf][3] * 0.5
                    senders.append(mf)
            

            if total * 0.7 > tgt_pawn:
                return (1, senders[0], t)

        for mf in my_forts:
            team, kind, level, pawn, up_time, to_set = state[mf]
            if pawn >= FORTRESS_LIMIT[level] and level < 5:
                return (2, mf, 0)

        
        # ======================================================
        #  前線（＝中立 or 敵 と隣接している味方拠点）
        # ======================================================
        frontline = []
        for mf in my_forts:
            for nb in state[mf][5]:
                if state[nb][0] != team:  # 中立 or 敵
                    frontline.append(mf)
                    break

        # ======================================================
        # 前線に向けた増援（BFSルート、距離制限なし）
        # ======================================================
        if frontline:
            weak_front = min(frontline, key=lambda x: state[x][3])

            # --- BFS 距離計算 ---
            dist = {i: float('inf') for i in range(12)}
            next_step = {i: None for i in range(12)}

            q = deque()
            for f in frontline:
                dist[f] = 0
                q.append(f)

            while q:
                cur = q.popleft()
                for nb in state[cur][5]:
                    if dist[nb] == float('inf'):
                        dist[nb] = dist[cur] + 1
                        next_step[nb] = cur
                        q.append(nb)

            # --- 増援送信 ---
            for mf in my_forts:
                if dist[mf] < float('inf') and dist[mf] > 0:
                    if state[mf][3] > 5:
                        return (1, mf, next_step[mf])

        # ======================================================
        
        return (0, 0, 0)


