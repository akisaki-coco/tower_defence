"""
Template AI Player

このファイルをコピーして、あなた独自のAIプレイヤーを実装してください。

使い方:
1. このファイルをコピー: cp template_player.py player_yourname.py
2. クラス名を変更: TemplatePlayer -> YourPlayerName
3. team_name() の返り値を変更
4. update() メソッドに戦略を実装
"""

from tcg.controller import Controller
from tcg.config import fortress_limit
from collections import deque


class a(Controller):
    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        # 協調攻撃は「次ターンの2手目」を予約して実行
        # plan: {"cmd": 1, "src": int, "dst": int, "expire": int}
        self.plan = None

    def team_name(self) -> str:
        return "a"

    def update(self, info):
        team, state, moving_pawns, spawning_pawns, done = info
        if done:
            return (0, 0, 0)
        self.step += 1

        N = len(state)

        # --- helpers ---
        def owner(i): return int(state[i][0])
        def kind(i): return int(state[i][1])
        def lv(i): return int(state[i][2])
        def p(i): return int(state[i][3])
        def up(i): return int(state[i][4])
        def nb(i): return list(state[i][5]) if state[i][5] else []

        SELF, ENEMY, NEUTRAL = team, (2 if team == 1 else 1), 0
        my = [i for i in range(N) if owner(i) == SELF]
        if not my:
            return (0, 0, 0)

        # ---------- BFS ----------
        def bfs(start: int):
            dist = {start: 0}
            prev = {start: None}
            q = deque([start])
            while q:
                u = q.popleft()
                for v in nb(u):
                    if v not in dist:
                        dist[v] = dist[u] + 1
                        prev[v] = u
                        q.append(v)
            return prev, dist

        def is_front(i):
            return any(owner(n) == ENEMY for n in nb(i))

        def cap(i):
            return fortress_limit[lv(i)]

        def keep(i):
            return 3 if is_front(i) else 2

        def can_upgrade(i):
            if owner(i) != SELF or lv(i) >= 5:
                return False
            if up(i) > 0:
                return False
            return p(i) >= cap(i) // 2

        def upgrade_cmd(i):
            return (2, i, 0)

        def can_send(src):
            if owner(src) != SELF or not nb(src):
                return False
            if p(src) < 2:
                return False
            after = p(src) - (p(src) // 2)
            return after >= keep(src)

        def send_power(src):
            return p(src) // 2

        def safe_move(src, dst):
           # --- 合法ルート判定（追加） ---
           # nb(src) に入っていない dst は「送れないルート」
           if dst not in nb(src):
              return (0, 0, 0)

           if 0 <= src < N and 0 <= dst < N and owner(src) == SELF and can_send(src):
              return (1, src, dst)
           return (0, 0, 0)


        # ---------- 前線アップグレ安全判定（余裕込み） ----------
        def safe_front_upgrade(i):
            if not is_front(i):
                return True
            cost = cap(i) // 2
            after_hp = p(i) - cost
            for e in nb(i):
                if owner(e) == ENEMY:
                    if (p(e) // 2) >= after_hp:
                        return False
            return True

        # ---------- 防衛必要量 ----------
        def need_reinforce(f):
            danger = 0
            for e in nb(f):
                if owner(e) == ENEMY:
                    danger = max(danger, (p(e) // 2) + 1)
            return max(0, danger - p(f))

        # ---------- 1手でtargetへ近づく ----------
        def step_toward(src: int, target: int):
            prev, dist = bfs(src)
            if target not in dist:
                return None
            cur = target
            while prev[cur] is not None and prev[cur] != src:
                cur = prev[cur]
            return cur if prev.get(cur) == src else (target if target in nb(src) else None)

        # ---------- 敵の「溢れ砦」判定（生産妨害ターゲット） ----------
        def enemy_overflow_score(dst: int):
            c = fortress_limit[lv(dst)]
            near = 1 if p(dst) >= c - 1 else 0
            return 40 * near + 8 * (lv(dst) - 1) + 2 * len(nb(dst))

        # =====================================================
        # 2)（反映）上限寸前/溢れ対策：生産停止・減衰を避ける
        # =====================================================
        def overflow_amt(i: int) -> int:
            return max(0, p(i) - cap(i))

        def near_cap(i: int) -> bool:
            # cap-1以上で「生産が止まりやすい」ので吐き出し候補
            return p(i) >= cap(i) - 1

        def waste_level(i: int) -> int:
            # 3: 溢れ（減衰しやすい）, 2: cap到達（生産停止）, 1: cap-1（生産停止寸前）, 0: 余裕
            if p(i) > cap(i):
                return 3
            if p(i) == cap(i):
                return 2
            if p(i) == cap(i) - 1:
                return 1
            return 0

        # ---------- 中盤以降は敵優先 ----------
        prefer_enemy = (self.step >= 15) or (len(my) >= N // 2)

        # =====================================================
        # 0) 予約した「協調の2手目」があれば、最優先で実行
        # =====================================================
        if self.plan is not None:
            if self.step > self.plan.get("expire", -1):
                self.plan = None
            else:
                src = self.plan["src"]
                dst = self.plan["dst"]
                if owner(dst) == ENEMY and dst in nb(src) and can_send(src):
                    self.plan = None
                    return safe_move(src, dst)
                self.plan = None

        # =====================================================
        # 1) 前線防御（距離2まで補強）
        # =====================================================
        fronts = [i for i in my if is_front(i)]
        if fronts:
            f = max(fronts, key=lambda i: need_reinforce(i))
            if need_reinforce(f) > 0:
                sources1 = [s for s in nb(f) if owner(s) == SELF and can_send(s)]
                if sources1:
                    src = max(sources1, key=lambda s: p(s))
                    return safe_move(src, f)

                candidates = []
                for src in my:
                    if not can_send(src):
                        continue
                    nxt = step_toward(src, f)
                    if nxt is None:
                        continue
                    if owner(nxt) == SELF and nxt in nb(src):
                        candidates.append((p(src), src, nxt))
                if candidates:
                    candidates.sort(reverse=True)
                    _, src, nxt = candidates[0]
                    return safe_move(src, nxt)

        # =====================================================
        # 2) アップグレード（溢れ/上限到達の砦ほど優先度↑）
        # =====================================================
        ups = [i for i in my if can_upgrade(i) and safe_front_upgrade(i)]
        if ups:
            def up_score(i):
                wl = waste_level(i)          # 0..3
                ov = overflow_amt(i)         # 0..∞
                stop = 1 if near_cap(i) else 0
                return (
                    80 * wl                 # 溢れ/生産停止を強く解消
                    + 20 * stop
                    + 5 * ov
                    + 3 * len(nb(i))
                    + (p(i) - cap(i) // 2)
                )
            i = max(ups, key=up_score)
            return upgrade_cmd(i)

        # =====================================================
        # 3)（反映）「上限寸前(>=cap-1)」も吐き出す：毎ターン1つ選んで確実に減らす
        #    ただし前線は cap-1 程度なら温存し、溢れが大きい時だけ吐き出す
        # =====================================================
        overflow_srcs = [
            i for i in my
            if can_send(i) and (
                overflow_amt(i) >= 2 or (not is_front(i) and near_cap(i))
            )
        ]
        if overflow_srcs:
            def src_key(i):
                # 優先: 溢れ>生産停止>非前線>兵数
                return (waste_level(i), overflow_amt(i), 1 if not is_front(i) else 0, p(i))

            src = max(overflow_srcs, key=src_key)
            sp = send_power(src)

            # (a) 近接の前線で補強が必要ならそこへ
            best = None
            best_score = -10**9
            for dst in nb(src):
                if owner(dst) == SELF and is_front(dst) and need_reinforce(dst) > 0:
                    score = 220 + 12 * need_reinforce(dst) + 2 * len(nb(dst))
                    if score > best_score:
                        best_score = score
                        best = dst
            if best is not None:
                return safe_move(src, best)

            # (b) 近接の敵を確殺できるなら攻撃（溢れ敵優先）
            best = None
            best_score = -10**9
            for dst in nb(src):
                if owner(dst) == ENEMY and sp > p(dst):
                    margin = sp - p(dst)
                    score = 140 + enemy_overflow_score(dst) + 3 * margin + 5 * lv(dst)
                    if score > best_score:
                        best_score = score
                        best = dst
            if best is not None:
                return safe_move(src, best)

            # (c) 近接の中立を取れるなら取る
            best = None
            best_score = -10**9
            for dst in nb(src):
                if owner(dst) == NEUTRAL and sp > p(dst):
                    margin = sp - p(dst)
                    score = 90 + 2 * len(nb(dst)) + 3 * margin
                    if score > best_score:
                        best_score = score
                        best = dst
            if best is not None:
                return safe_move(src, best)

            # (d) それ以外：前線寄り＆生産が回りそうな味方へ資源移動
            best = None
            best_score = -10**9
            for dst in nb(src):
                if owner(dst) != SELF:
                    continue
                # 受け側も cap-1 以上なら生産が止まるので少し避ける
                stop_pen = 30 if p(dst) >= cap(dst) - 1 else 0
                score = (60 if is_front(dst) else 0) + 3 * len(nb(dst)) - stop_pen - p(dst)
                if score > best_score:
                    best_score = score
                    best = dst
            if best is not None:
                return safe_move(src, best)

        # =====================================================
        # 4) 生産妨害：取れるなら「溢れ敵」最優先で叩く
        # =====================================================
        best = None
        best_score = -10**9
        for src in my:
            if not can_send(src):
                continue
            sp = send_power(src)
            for dst in nb(src):
                if owner(dst) != ENEMY:
                    continue
                if sp <= p(dst):
                    continue
                score = enemy_overflow_score(dst) + (sp - p(dst))
                if score > best_score:
                    best_score = score
                    best = (src, dst)
        if best and prefer_enemy:
            return safe_move(best[0], best[1])

        # =====================================================
        # 5) 単独攻撃（確殺）
        # =====================================================
        def best_single_attack():
            best = None
            best_score = -10**9
            for src in my:
                if not can_send(src):
                    continue
                sp = send_power(src)
                for dst in nb(src):
                    if owner(dst) != ENEMY:
                        continue
                    if sp <= p(dst):
                        continue
                    margin = sp - p(dst)
                    score = 30 + 6 * (lv(dst) - 1) + 2 * len(nb(dst)) + 3 * margin + enemy_overflow_score(dst)
                    if score > best_score:
                        best_score = score
                        best = (src, dst)
            return best

        # =====================================================
        # 6) 2砦協調（隣接）※「2手」前提で予約
        # =====================================================
        def best_two_coop_adj():
            best = None
            best_score = -10**9
            for dst in range(N):
                if owner(dst) != ENEMY:
                    continue
                friends = [s for s in nb(dst) if owner(s) == SELF and can_send(s)]
                if len(friends) < 2:
                    continue
                friends.sort(key=lambda s: p(s), reverse=True)
                s1, s2 = friends[0], friends[1]
                power2 = (p(s1) // 2) + (p(s2) // 2)
                if power2 <= p(dst):
                    continue
                margin = power2 - p(dst)
                score = 50 + 8 * (lv(dst) - 1) + 2 * len(nb(dst)) + 2 * margin + enemy_overflow_score(dst)
                if score > best_score:
                    best_score = score
                    best = (s1, s2, dst)
            return best

        # =====================================================
        # 7) 距離2協調の「準備手」
        # =====================================================
        def plan_coop_distance2_prep():
            best = None
            best_score = -10**9

            for dst in range(N):
                if owner(dst) != ENEMY:
                    continue
                adj_allies = [a for a in nb(dst) if owner(a) == SELF]
                if not adj_allies:
                    continue

                a = max(adj_allies, key=lambda x: p(x))
                if not can_send(a):
                    continue
                a_power = p(a) // 2

                if len([x for x in adj_allies if x != a and can_send(x)]) >= 1:
                    continue

                mids = [m for m in nb(dst) if owner(m) == SELF]
                for mid in mids:
                    sources = [src for src in nb(mid) if owner(src) == SELF and can_send(src) and src != a]
                    if not sources:
                        continue
                    src = max(sources, key=lambda s: p(s))

                    power_next = a_power + (p(src) // 2)
                    if power_next <= p(dst):
                        continue

                    score = 40 + 10 * (lv(dst) - 1) + 2 * len(nb(dst)) + enemy_overflow_score(dst)
                    if score > best_score:
                        best_score = score
                        best = (src, mid)

            return best

        if prefer_enemy:
            b = best_two_coop_adj()
            if b:
                s1, s2, dst = b
                self.plan = {"cmd": 1, "src": s2, "dst": dst, "expire": self.step + 1}
                return safe_move(s1, dst)

            b = best_single_attack()
            if b:
                return safe_move(b[0], b[1])

            prep = plan_coop_distance2_prep()
            if prep:
                return safe_move(prep[0], prep[1])

        # =====================================================
        # 8) 中立制圧
        # =====================================================
        best = None
        best_score = -10**9
        for src in my:
            if not can_send(src):
                continue
            sp = send_power(src)
            for dst in nb(src):
                if owner(dst) != NEUTRAL:
                    continue
                if sp <= p(dst):
                    continue
                margin = sp - p(dst)
                score = 20 + 2 * len(nb(dst)) + 3 * margin
                if score > best_score:
                    best_score = score
                    best = (src, dst)
        if best:
            return safe_move(best[0], best[1])

        # 敵優先モードでない場合でも、攻撃と準備は試す
        b = best_two_coop_adj()
        if b:
            s1, s2, dst = b
            self.plan = {"cmd": 1, "src": s2, "dst": dst, "expire": self.step + 1}
            return safe_move(s1, dst)

        b = best_single_attack()
        if b:
            return safe_move(b[0], b[1])

        prep = plan_coop_distance2_prep()
        if prep:
            return safe_move(prep[0], prep[1])

        # =====================================================
        # 9) 終盤アグレッシブ
        # =====================================================
        if self.step >= 40 or len(my) >= (N * 2) // 3:
            best = None
            best_score = -10**9
            for src in my:
                if not can_send(src):
                    continue
                sp = send_power(src)
                for dst in nb(src):
                    if owner(dst) != ENEMY:
                        continue
                    if sp <= p(dst):
                        continue
                    score = 12 * lv(dst) + 3 * len(nb(dst)) + (sp - p(dst)) + enemy_overflow_score(dst)
                    if score > best_score:
                        best_score = score
                        best = (src, dst)
            if best:
                return safe_move(best[0], best[1])

        return (0, 0, 0)


