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
from collections import deque
import math

fortress_limit = [10, 20, 30, 40, 50]

class KOMATSU(Controller):
    """戦略Oを改良したAI"""

    def __init__(self):
        super().__init__()
        self.step = 0
        self.memory = {"last_attack_step": {}, "last_sent_edge": {}}
        self.min_garrison = 2
        self.attack_cooldown = 5
        self.reinforce_radius = 2
        self.capture_margin = 1
        self.edge_cooldown = 3

    def team_name(self):
        return "KOMATSU_PLUS"

    # ========================
    # 補助関数
    # ========================

    def shortest_path(self, start):
        """BFSで距離と親を返す"""
        prev = {start: None}
        dist = {start: 0}
        q = deque([start])
        while q:
            u = q.popleft()
            for v in self.state[u][5]:
                if v not in dist:
                    dist[v] = dist[u] + 1
                    prev[v] = u
                    q.append(v)
        return prev, dist

    def can_capture_single(self, src_hp, dst_hp):
        """単独で攻略可能か"""
        return src_hp // 2 > dst_hp

    def nearby_friends(self, target, max_depth=2):
        """ターゲットから一定距離以内の味方砦をリストアップ"""
        _, dist = self.shortest_path(target)
        friends = []
        for i, fort in enumerate(self.state):
            if fort[0] != self.team:
                continue
            d = dist.get(i, 999)
            if d <= max_depth:
                friends.append((d, -fort[3], i))
        friends.sort()
        return [t[2] for t in friends]

    def edge_allowed(self, src, dst):
        """同じ辺での往復送信を制限"""
        last = self.memory["last_sent_edge"].get((src, dst), -99999)
        last_rev = self.memory["last_sent_edge"].get((dst, src), -99999)
        return self.step - last >= self.edge_cooldown and self.step - last_rev >= self.edge_cooldown

    def record_edge(self, src, dst):
        self.memory["last_sent_edge"][(src, dst)] = self.step

    # ========================
    # メイン戦略
    # ========================

    def update(self, info):
        self.team, self.state, self.moving, self.spawning, self.done = info
        self.step += 1

        my_indices = [i for i, f in enumerate(self.state) if f[0] == self.team]
        enemy_indices = [i for i, f in enumerate(self.state) if f[0] != self.team]

        # 1. 即時攻略
        immediate = []
        for src in my_indices:
            src_hp = self.state[src][3]
            if src_hp <= self.min_garrison:
                continue
            for dst in self.state[src][5]:
                if self.state[dst][0] == self.team:
                    continue
                if self.can_capture_single(src_hp, self.state[dst][3]) and self.edge_allowed(src, dst):
                    immediate.append((self.state[dst][3], -src_hp, src, dst))
        if immediate:
            immediate.sort()
            _, _, src, dst = immediate[0]
            self.record_edge(src, dst)
            return 1, src, dst

        # 2. 協調攻撃
        coop_candidates = []
        for dst in enemy_indices:
            dst_hp = self.state[dst][3]
            sources = self.nearby_friends(dst, self.reinforce_radius)
            potential = sum(max(0, (self.state[i][3] - self.min_garrison) // 2) for i in sources)
            if potential > dst_hp + self.capture_margin:
                coop_candidates.append((dst_hp, len(sources), dst, sources))
        if coop_candidates:
            coop_candidates.sort()
            _, _, dst, sources = coop_candidates[0]
            for s in sorted(sources, key=lambda i: -self.state[i][3]):
                if self.edge_allowed(s, dst):
                    self.record_edge(s, dst)
                    return 1, s, dst

        # 3. アップグレード
        upgrades = []
        for idx in my_indices:
            level = self.state[idx][2]
            hp = self.state[idx][3]
            if level >= 5:
                continue
            if hp >= math.ceil(fortress_limit[level - 1] / 2):
                adjacent_enemy = any(self.state[n][0] != self.team for n in self.state[idx][5])
                score = 0 if adjacent_enemy else 1
                upgrades.append((score, -hp, idx))
        if upgrades:
            upgrades.sort()
            return 2, upgrades[0][2], upgrades[0][2]

        # 4. 前線援軍
        weak = [i for i in my_indices
        if self.state[i][3] < fortress_limit[self.state[i][2] - 1] * 0.45]

        strong = []
        for i in my_indices:
            hp = self.state[i][3]
            level = self.state[i][2]
            
            adjacent_enemy = any(self.state[n][0] != self.team for n in self.state[i][5])
            if adjacent_enemy:
              continue


        # ★ アップグレード可能なら援軍に出さない
            if level < 5 and hp >= math.ceil(fortress_limit[level - 1] / 2):
              continue

            if hp > self.min_garrison * 2:
              strong.append(i)

        strong = sorted(strong, key=lambda i: -self.state[i][3])

        for src in strong:
            send = (self.state[src][3] - self.min_garrison) // 2
            if send <= 0:
                continue
            for dst in self.state[src][5]:
                if dst in weak and self.edge_allowed(src, dst):
                    self.record_edge(src, dst)
                    return 1, src, dst

        # 5. 待機
        return 0, 0, 0

