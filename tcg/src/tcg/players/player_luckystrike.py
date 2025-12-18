from tcg.controller import Controller
from tcg.config import fortress_limit


class LuckyStrikePlayer(Controller):
    """
    LuckyStrikePlayer v4.1
    - 初期砦は最速 Lv5（兵は絶対動かさない）
    - 初動では外周(0,2,9,11)には絶対に行かない
    - 中央(3,4,5 / 6,7,8)を最優先で取りに行く
    - 初動の自陣→自陣送りを禁止
    - 溢れ兵は中央方向へ流す
    - fallbackで絶対硬直しない
    """

    def __init__(self):
        super().__init__()
        self.step = 0
        self.initial = None
        self.initial_done = False
        self.initialized = False

        self.central_targets = []
        self.avoid_early = []

    def team_name(self) -> str:
        return "LuckyStrike"


    # ---------- basic helpers ----------
    def is_mine(self, s, i): return s[i][0] == 1
    def is_enemy(self, s, i): return s[i][0] == 2
    def is_neutral(self, s, i): return s[i][0] == 0
    def neigh(self, s, i): return s[i][5]

    def atk_after_move(self, s, src):
        return s[src][3] / 2

    def can_take_neutral(self, s, src, dst):
        return self.atk_after_move(s, src) > s[dst][3] * 0.95

    def can_take_enemy(self, s, src, dst):
        return self.atk_after_move(s, src) > s[dst][3] * 1.10


    # ---------- movement validator ----------
    def valid(self, s, src, dst,
              allow_neutral=True, allow_enemy=True, allow_self=True,
              forbid_initial=False):

        if not self.is_mine(s, src):
            return False
        if dst not in self.neigh(s, src):
            return False
        if s[src][3] < 2:
            return False

        if forbid_initial and src == self.initial and not self.initial_done:
            return False

        # 自陣送りは allow_self で管理
        if self.is_mine(s, dst):
            return allow_self

        if self.is_neutral(s, dst) and allow_neutral:
            return self.can_take_neutral(s, src, dst)

        if self.is_enemy(s, dst) and allow_enemy:
            return self.can_take_enemy(s, src, dst)

        return False


    # ---------- 初期砦 & サイド判定 ----------
    def detect_initial(self, s):
        # Lv2 & 20兵の砦を最優先
        for i in range(12):
            if self.is_mine(s, i) and s[i][2] == 2 and s[i][3] == 20:
                self.initial = i
                break

        # fallback
        if self.initial is None:
            my_list = [i for i in range(12) if self.is_mine(s, i)]
            if my_list:
                self.initial = my_list[0]

        # 上か下かの判定
        if self.initial in [0, 1, 2]:
            # 上スタート
            self.central_targets = [3, 4, 5]
            self.avoid_early = [9, 10, 11]
        else:
            # 下スタート
            self.central_targets = [6, 7, 8]
            self.avoid_early = [0, 1, 2]

        self.initialized = True


    # ---------- Main ----------
    def update(self, info):
        team, s, moving, spawn, done = info
        self.step += 1

        # 初期セットアップ
        if not self.initialized:
            self.detect_initial(s)

        my_forts = [i for i in range(12) if self.is_mine(s, i)]
        my_sorted = sorted(my_forts, key=lambda x: -s[x][3])

        # ------------------------------
        # 1) 初期砦：Lv5になるまで絶対動かさない
        # ------------------------------
        if self.initial is not None and not self.initial_done:
            lv = s[self.initial][2]

            if not self.is_mine(s, self.initial):
                # 初期拠点が奪われた → 緊急リセット
                self.initialized = False
                self.initial = None
                return 0, 0, 0

            if lv < 5:
                if s[self.initial][4] == -1:
                    cap = fortress_limit[lv]
                    if s[self.initial][3] >= cap * 0.45:
                        return 2, self.initial, 0
            else:
                self.initial_done = True


        # ------------------------------
        # 2) Early phase：中央以外は絶対いかない
        # ------------------------------
        EARLY = 9000
        if self.step < EARLY:
            # 2-1) 中央取り
            for tgt in self.central_targets:
                if self.is_neutral(s, tgt):
                    for src in my_sorted:
                        if self.valid(s, src, tgt,
                                      allow_neutral=True, allow_enemy=False,
                                      allow_self=False,
                                      forbid_initial=True):

                            if tgt in self.avoid_early:
                                continue

                            return 1, src, tgt

            # 2-2) 周辺中立（avoid_early は通さない）
            for src in my_sorted:
                if s[src][3] < 3:
                    continue
                for nei in self.neigh(s, src):
                    if nei in self.avoid_early:
                        continue
                    if self.is_neutral(s, nei) and self.valid(
                            s, src, nei,
                            allow_neutral=True, allow_enemy=False,
                            allow_self=False,
                            forbid_initial=True):

                        return 1, src, nei


        # ------------------------------
        # 3) 中盤：中央拠点周辺の拠点をアップグレード
        # ------------------------------
        if self.initial_done or self.step >= EARLY:
            for ct in self.central_targets:
                for nb in self.neigh(s, ct):
                    if self.is_mine(s, nb):
                        lv = s[nb][2]
                        if lv < 4 and s[nb][4] == -1:
                            cap = fortress_limit[lv]
                            if s[nb][3] >= cap * 0.50:
                                return 2, nb, 0


        # ------------------------------
        # 4) 中立制圧（優先：中央 → その他）
        # ------------------------------
        neutral_list = []

        # まず中央隣接
        for ct in self.central_targets:
            for nb in self.neigh(s, ct):
                if self.is_neutral(s, nb):
                    neutral_list.append(nb)

        # 次にその他
        for i in range(12):
            if self.is_neutral(s, i) and i not in neutral_list:
                neutral_list.append(i)

        for tgt in neutral_list:
            for src in my_sorted:
                if tgt in self.avoid_early:
                    continue
                if self.valid(s, src, tgt, forbid_initial=True):
                    return 1, src, tgt


        # ------------------------------
        # 5) 敵の弱点を突く
        # ------------------------------
        for src in my_sorted:
            if s[src][3] < 4:
                continue
            for nei in self.neigh(s, src):
                if self.is_enemy(s, nei) and self.valid(
                        s, src, nei,
                        allow_neutral=False, allow_enemy=True,
                        forbid_initial=True):
                    return 1, src, nei


        # ------------------------------
        # 6) 溢れ兵 → 中央方向に流す
        # ------------------------------
        for src in my_sorted:
            lv = s[src][2]
            cap = fortress_limit[lv]
            if s[src][3] >= cap * 0.65:
                neighbors_sorted = sorted(
                    self.neigh(s, src),
                    key=lambda x: (0 if x in self.central_targets else 1)
                )
                for nei in neighbors_sorted:
                    if nei in self.avoid_early:
                        continue
                    if self.valid(s, src, nei, forbid_initial=True):
                        return 1, src, nei


        # ------------------------------
        # 7) fallback（必ず硬直回避）
        # ------------------------------
        for src in my_sorted:
            for nei in self.neigh(s, src):
                if nei in self.avoid_early:
                    continue
                if self.valid(s, src, nei, forbid_initial=True):
                    return 1, src, nei

        return 0, 0, 0

