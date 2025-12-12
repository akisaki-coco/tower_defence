"""
player.py - Kai Player Ver.13 (敵情報表示機能付き)
"""
from tcg.controller import Controller
from .strategy import Strategy
import random

class KaiPlayer(Controller):
    def __init__(self):
        super().__init__()
        self.strategy = Strategy()
        self.step_count = 0

    def team_name(self) -> str:
        return "KaiMonitor"

    def update(self, info) -> tuple[int, int, int]:
        self.step_count += 1
        team, state, pawn, SpawnPoint, done = info

        my_fortresses = [i for i in range(12) if state[i][0] == 1]
        random.shuffle(my_fortresses)

        # 100ステップに1回、自分と敵のステータスを表示
        if self.step_count % 100 == 0:
            self.print_debug_info(state, my_fortresses)

        # --- 行動ロジック ---

        # 1. ハイエナ攻撃
        for fid in my_fortresses:
            target = self.strategy.find_easy_win(state, fid)
            if target is not None:
                print(f">>> [SNIPE] ID:{fid} -> ID:{target} (Weak Enemy!)")
                return 1, fid, target

        # 2. アップグレード
        for fid in my_fortresses:
            if self.strategy.check_upgrade(state[fid]):
                print(f"  + [UPGRADE] ID:{fid} Start Level Up")
                return 2, fid, 0

        # 3. 通常攻撃
        for fid in my_fortresses:
            target = self.strategy.find_attack_target(state, fid)
            if target is not None:
                print(f">>> [ATTACK] ID:{fid} -> ID:{target}")
                return 1, fid, target

        # 4. 後方支援
        for fid in my_fortresses:
            target = self.strategy.find_reinforce_target(state, fid)
            if target is not None:
                # print(f"    [SUPPORT] ID:{fid} -> ID:{target} (Reinforcement)") # ログ抑制
                return 1, fid, target

        return 0, 0, 0

    def print_debug_info(self, state, my_fortresses):
        HARD_LIMITS = [10, 10, 20, 30, 40, 50]
        
        # 敵の砦リストを取得 (Team ID: 2)
        enemy_fortresses = [i for i in range(12) if state[i][0] == 2]
        
        print(f"\n=== Status Report (Step {self.step_count}) ===")
        
        # --- 自分の砦 ---
        print("--- My Fortresses (Red) ---")
        if not my_fortresses:
            print("  (None)")
        for fid in sorted(my_fortresses): # ID順にソートして表示
            f = state[fid]
            level = f[2]
            pawns = f[3]
            limit = HARD_LIMITS[level] if level < len(HARD_LIMITS) else 50
            ratio = int((pawns / limit) * 100)
            status = "UPGRADING" if f[4] > 0 else "READY"
            print(f"ID:{fid:2d} | Lv:{level} | Pawns: {pawns:4.1f}/{limit} ({ratio}%) | {status}")

        # --- 敵の砦 ---
        print("--- Enemy Fortresses (Blue) ---")
        if not enemy_fortresses:
            print("  (None)")
        for fid in sorted(enemy_fortresses):
            f = state[fid]
            level = f[2]
            pawns = f[3]
            limit = HARD_LIMITS[level] if level < len(HARD_LIMITS) else 50
            ratio = int((pawns / limit) * 100)
            status = "UPGRADING" if f[4] > 0 else "READY"
            print(f"ID:{fid:2d} | Lv:{level} | Pawns: {pawns:4.1f}/{limit} ({ratio}%) | {status}")
            
        print("==========================================")
