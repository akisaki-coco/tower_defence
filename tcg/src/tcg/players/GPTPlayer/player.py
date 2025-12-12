"""GPTPlayer: aggressive-expansion AI with adaptive defense."""

from __future__ import annotations

import math
from typing import List, Tuple

from tcg.config import fortress_cool, fortress_limit, pos_fortress
from tcg.controller import Controller

Damage = {0: 0.65, 1: 0.95}
Speed = {0: 1.5, 1: 1.0}


class GPTPlayer(Controller):
    """Strong heuristic player balancing rush, upgrades, and defense."""

    # Importance based on connectivity and centrality
    FORTRESS_IMPORTANCE = {
        0: 3,
        1: 4,
        2: 3,
        3: 6,
        4: 11,
        5: 6,
        6: 6,
        7: 11,
        8: 6,
        9: 3,
        10: 4,
        11: 3,
    }

    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        self.dist = self._precompute_distances()

    def team_name(self) -> str:
        return "GPTPlayer"

    def _precompute_distances(self) -> List[List[float]]:
        dist = [[0.0 for _ in range(12)] for _ in range(12)]
        for i in range(12):
            for j in range(12):
                dx = pos_fortress[i][0] - pos_fortress[j][0]
                dy = pos_fortress[i][1] - pos_fortress[j][1]
                dist[i][j] = math.hypot(dx, dy)
        return dist

    def _travel_time(self, frm: int, to: int, kind: int) -> float:
        return self.dist[frm][to] / Speed[kind]

    def _predict_defense(self, target_state: List, travel_time: float) -> float:
        team, kind, level, pawn, _, _ = target_state
        prod_rate = fortress_cool[kind][level]
        extra = travel_time / prod_rate if prod_rate else 0.0
        # Clamp by fortress capacity to avoid overestimation
        return min(pawn + extra, fortress_limit[level])

    def _incoming_damage(self, moving_pawns: List, target: int) -> float:
        return sum(Damage[p[1]] for p in moving_pawns if p[0] == 2 and p[3] == target)

    def _enemy_neighbors(self, idx: int, state: List) -> int:
        return sum(1 for n in state[idx][5] if state[n][0] == 2)

    def _can_issue(self, command: int, subject: int, to: int, state: List) -> bool:
        if command == 2:
            return state[subject][0] == 1
        if command == 1:
            return state[subject][0] == 1 and to in state[subject][5]
        return True

    def update(self, info) -> Tuple[int, int, int]:
        team, state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        my_forts = [i for i in range(12) if state[i][0] == 1]
        enemy_forts = [i for i in range(12) if state[i][0] == 2]
        neutral_forts = [i for i in range(12) if state[i][0] == 0]

        actions: List[Tuple[float, int, int, int]] = []

        # 1) Emergency defense based on incoming projectiles
        for fort in my_forts:
            dmg_in = self._incoming_damage(moving_pawns, fort)
            if dmg_in <= 0:
                continue
            garrison = state[fort][3]
            if dmg_in > garrison * 0.6:
                neighbors = state[fort][5]
                donors = [n for n in neighbors if state[n][0] == 1 and state[n][3] >= 4]
                if donors:
                    donor = max(donors, key=lambda x: state[x][3])
                    priority = 300 + (dmg_in - garrison * 0.6)
                    actions.append((priority, 1, donor, fort))

        # 2) High-value upgrades when safe
        for fort in my_forts:
            team_id, kind, level, pawn, upgrade_time, neighbors = state[fort]
            if upgrade_time == -1 and 1 <= level <= 4:
                incoming = self._incoming_damage(moving_pawns, fort)
                if incoming < pawn * 0.4 and pawn >= fortress_limit[level] * 0.55:
                    base = 120 if fort in (4, 7) else 95
                    priority = base + self.FORTRESS_IMPORTANCE[fort] * 1.5 + level
                    actions.append((priority, 2, fort, 0))

        # 3) Capture weak neutral
        for fort in my_forts:
            team_id, kind, level, pawn, _, neighbors = state[fort]
            if pawn < 4:
                continue
            for nb in neighbors:
                if state[nb][0] != 0:
                    continue
                travel = self._travel_time(fort, nb, kind)
                attack_power = Damage[kind] * (pawn / 2)
                defense = self._predict_defense(state[nb], travel)
                if attack_power > defense * 1.05:
                    margin = attack_power - defense
                    priority = 180 + self.FORTRESS_IMPORTANCE[nb] * 2 + margin
                    actions.append((priority, 1, fort, nb))

        # 4) Strike exposed enemy neighbors
        for fort in my_forts:
            team_id, kind, level, pawn, _, neighbors = state[fort]
            if pawn < 6:
                continue
            for nb in neighbors:
                if state[nb][0] != 2:
                    continue
                travel = self._travel_time(fort, nb, kind)
                attack_power = Damage[kind] * (pawn / 2)
                defense = self._predict_defense(state[nb], travel)
                if attack_power > defense * 1.15:
                    margin = attack_power - defense
                    priority = 150 + self.FORTRESS_IMPORTANCE[nb] * 2 + margin
                    actions.append((priority, 1, fort, nb))

        # 5) Reallocate surplus from backline to frontline/neutral
        for fort in my_forts:
            team_id, kind, level, pawn, _, neighbors = state[fort]
            if self._enemy_neighbors(fort, state) == 0 and pawn > fortress_limit[level] * 0.8:
                targets = [n for n in neighbors if state[n][0] in (0, 1)]
                if not targets:
                    continue
                def desirability(t: int) -> float:
                    tension = self._enemy_neighbors(t, state)
                    return self.FORTRESS_IMPORTANCE[t] + tension * 4

                to = max(targets, key=desirability)
                priority = 110 + desirability(to)
                actions.append((priority, 1, fort, to))

        if actions:
            actions.sort(key=lambda x: x[0], reverse=True)
            _, command, subject, to = actions[0]
            if self._can_issue(command, subject, to, state):
                return command, subject, to

        return 0, 0, 0
