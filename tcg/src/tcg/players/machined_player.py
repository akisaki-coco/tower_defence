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


class MachinedPlayer(Controller):
    """
    テンプレートAIプレイヤー

    このクラスをベースに独自の戦略を実装してください。
    """

    # 防御的な設定（多くの部隊を溜められる）
    fortress_limit = [10, 10, 20, 30, 40, 50]

    # FORTRESS_IMPORTANCEの設定はとりあえず一緒
    FORTRESS_IMPORTANCE = {
        0: 3, 1: 4, 2: 3,      # 上側エリア
        3: 6, 4: 10, 5: 6,     # 中央上
        6: 6, 7: 10, 8: 6,     # 中央下
        9: 3, 10: 4, 11: 3     # 下側エリア
    }

    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        self.prev_team_state = None # 前のターンのチーム状態を保存する変数
        self.isAttack = False # 砦が攻撃中かどうか

    def team_name(self) -> str:
        """
        プレイヤー名を返す

        トーナメント結果の表示に使用されます。

        Returns:
            str: プレイヤー名
        """
        return "Machined Player"
    
    def update(self, info) -> tuple[int, int, int]:
        """
        戦略的な判断でコマンドを選択（改善版 - アップグレード優先）
        """
        team, state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        # 優先度付きアクションリスト
        actions = []
        considered_actions = set()  # 重複防止

        team, state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        # 前フレームから今回までで「新しく自軍になった砦」を検出
        newly_captured = set()
        current_teams = [state[i][0] for i in range(12)]

        if self.prev_team_state is not None:
            for i in range(12):
                # 0(中立) or 2(敵) から 1(自軍) になったものを新規占領とみなす
                if self.prev_team_state[i] != 1 and current_teams[i] == 1:
                    newly_captured.add(i)

        # 今回の状態を保存
        self.prev_team_state = current_teams[:]

        # 自分の要塞と敵の要塞を分類
        my_fortresses = [i for i in range(12) if state[i][0] == 1]
        enemy_fortresses = [i for i in range(12) if state[i][0] == 2]
        neutral_fortresses = [i for i in range(12) if state[i][0] == 0]

        # ゲームフェーズの判定 (取得要塞数で判断)
        my_fortress_num = len(my_fortresses)
        if my_fortress_num < 4:
            phase = "early"
        elif my_fortress_num < 7:
            phase = "mid"
        else:
            phase = "late"

        # デバッグ情報（序盤のみ表示）
        if self.step % 100 == 0 and self.step < 1000:
            print(f"\n=== Step {self.step} ({phase}) ===")
            print(f"自分の要塞数: {len(my_fortresses)}, 敵の要塞数: {len(enemy_fortresses)}, 中立: {len(neutral_fortresses)}")
            for my_fort in my_fortresses:
                level = state[my_fort][2]
                troops = state[my_fort][3]
                max_troops = self.fortress_limit[level]
                flag = " (NEW)" if my_fort in newly_captured else ""
                print(f"  要塞{my_fort}{flag}: Lv{level}, 部隊{troops}/{max_troops}, 充填率{troops/max_troops*100:.1f}%")

        # === 緊急防御: 最優先 ===
        under_attack = {}
        incoming_threats = {}
        
        for pawn in moving_pawns:
            pawn_team, kind, from_, to, pos = pawn
            # pos がリストの場合に対応（例: [x, y]）
            if isinstance(pos, (list, tuple)):
                # 進行度が別で保存されていないなら、距離計算は「ざっくり1」として扱うか、
                # もしくは x,y から距離を近似して計算する
                # ここでは安全のため固定値扱いにして、「エラーを出さずに動かす」ことを優先
                distance = 1.0
            else:
                distance = max(1.0, 100 - float(pos))

            if pawn_team == 2 and state[to][0] == 1:
                if to not in under_attack:
                    under_attack[to] = []
                under_attack[to].append((from_, pos))

                threat = kind * 10 / distance
                incoming_threats[to] = incoming_threats.get(to, 0) + threat

        # 防御が必要な要塞への支援
        for target_fort, threats in under_attack.items():
            current_defenders = state[target_fort][3]
            total_threat = incoming_threats.get(target_fort, 0)

            if current_defenders < total_threat * 1.2:
                neighbors = state[target_fort][5]
                for my_fort in neighbors:
                    action_key = (1, my_fort, target_fort)
                    if (state[my_fort][0] == 1 and 
                        state[my_fort][3] >= 5 and
                        action_key not in considered_actions):
                        priority = 200 + total_threat * 10
                        actions.append((priority, 1, my_fort, target_fort))
                        considered_actions.add(action_key)

        # === アップグレード戦略（序盤最優先）===
        # 序盤は部隊を溜めるためにアップグレードを最優先
        if phase == "early":
            upgrade_priority_base = 250  # 攻撃より優先
        elif phase == "mid":
            upgrade_priority_base = 100
        else:
            upgrade_priority_base = 70
        
        max_upgrade_level = {
            "early": 5,
            "mid": 4,
            "late": 3
        }[phase]

        # 中央の重要拠点は最優先でアップグレード
        for fort_id in [4, 7]:
            if fort_id in my_fortresses:
                level = state[fort_id][2]
                troops = state[fort_id][3]
                
                if (state[fort_id][4] == -1 and 
                    level < max_upgrade_level and
                    troops >= self.fortress_limit[level] * 0.4):  # 40%で開始
                    priority = upgrade_priority_base + 50 + level * 10
                    actions.append((priority, 2, fort_id, 0))
                    print("LAUNCH UPGRADE")
                    if self.step < 500:
                        print(f"    重要拠点アップグレード計画: 要塞{fort_id} Lv{level}→{level+1} (優先度{priority})")

        # その他の要塞のアップグレード
        for my_fort in my_fortresses:
            if my_fort not in [4, 7]:
                level = state[my_fort][2]
                troops = state[my_fort][3]
                importance = self.FORTRESS_IMPORTANCE.get(my_fort, 5)
                enemy_neighbors = self.count_enemy_neighbors(my_fort, state)
                
                # 序盤は積極的にアップグレード
                troops_threshold = self.fortress_limit[level] * (0.3 if phase == "early" else 0.5)
                
                if (state[my_fort][4] == -1 and 
                    level < max_upgrade_level and
                    troops >= troops_threshold):
                    priority = upgrade_priority_base + importance + level * 10 + enemy_neighbors * 8 + 50 # とりあえずアップグレードは高めに
                    actions.append((priority, 2, my_fort, 0)) 
                    print("LAUNCH UPGRADE")
                    if self.step < 500:
                        print(f"    アップグレード計画: 要塞{my_fort} Lv{level}→{level+1} (優先度{priority})")
        
        # # === 新規占領要塞の優先アップグレード ===
        # for fort_id in newly_captured:
        #     if fort_id in my_fortresses:
        #         level = state[fort_id][2]
        #         troops = state[fort_id][3]
        #         # まだアップグレード中でない & レベル上限以下
        #         if state[fort_id][4] == -1 and level < max_upgrade_level:
        #             # 新規占領砦は、通常よりも低いしきい値でアップグレードを開始
        #             threshold = self.fortress_limit[level] * 0.3
        #             if troops >= threshold:
        #                 # かなり高い優先度を与えて、他の行動より優先させる
        #                 priority = upgrade_priority_base + 80 + level * 10
        #                 actions.append((priority, 2, fort_id, 0))
        #                 if self.step < 2000:
        #                     print(f"    新規占領アップグレード計画: 要塞{fort_id} Lv{level}→{level+1} (優先度{priority}, 部隊{troops})")


        # === 序盤戦略: 十分な兵力が溜まってから攻撃 ===
        if phase == "early":
            for my_fort in my_fortresses:
                level = state[my_fort][2]
                troops = state[my_fort][3]
                max_troops = self.fortress_limit[level]
                
                # 収容量の90%以上溜まっている場合、収容量が10%になるまで攻撃
                if (troops >= max_troops * 0.9 and self.isAttack == False) or (troops >= 0.1 and self.isAttack == True):
                    neighbors = state[my_fort][5]
                    self.isAttack = True
                    for neighbor in neighbors:
                        action_key = (1, my_fort, neighbor)
                        # if state[neighbor][0] == 0 and action_key not in considered_actions:
                        if state[neighbor][0] == 0:
                            neutral_troops = state[neighbor][3]
                            
                            # 十分な兵力比があるか確認
                            if troops >= neutral_troops * 1.5:
                                importance = self.FORTRESS_IMPORTANCE.get(neighbor, 5)
                                ease = max(0, 30 - neutral_troops)
                                # already_attacking = self.is_already_attacking(my_fort, neighbor, spawning_pawns, moving_pawns)
                                already_attacking = False # とりあえず無視
                                
                                if not already_attacking:
                                    priority = 150 + importance * 8 + ease
                                    actions.append((priority, 1, my_fort, neighbor))
                                    # considered_actions.add(action_key)
                                    if self.step < 500:
                                        print(f"    序盤攻撃計画: {my_fort}({troops})→{neighbor}({neutral_troops}) (優先度{priority})")
                elif (troops <= 0.1 and self.isAttack == True):
                    self.isAttack = False

        # === 中立要塞への計算された攻撃（中盤以降）===
        if phase in ["mid", "late"]:
            for my_fort in my_fortresses:
                if state[my_fort][3] >= 8:
                    neighbors = state[my_fort][5]
                    for neighbor in neighbors:
                        action_key = (1, my_fort, neighbor)
                        if state[neighbor][0] == 0 and action_key not in considered_actions:
                            my_troops = state[my_fort][3]
                            neutral_troops = state[neighbor][3]
                            success_ratio = my_troops / max(neutral_troops, 1)
                            
                            if success_ratio >= 1.3:
                                importance = self.FORTRESS_IMPORTANCE.get(neighbor, 5)
                                priority = 120 + importance * 3 + int(success_ratio * 10)
                                actions.append((priority, 1, my_fort, neighbor))
                                considered_actions.add(action_key)

        # === 敵要塞への戦略的攻撃 ===
        for my_fort in my_fortresses:
            level = state[my_fort][2]
            min_troops = max(15, self.fortress_limit[level] * 0.5)
            
            if state[my_fort][3] >= min_troops:
                neighbors = state[my_fort][5]
                for neighbor in neighbors:
                    action_key = (1, my_fort, neighbor)
                    if state[neighbor][0] == 2 and action_key not in considered_actions:
                        my_troops = state[my_fort][3]
                        enemy_troops = state[neighbor][3]
                        enemy_level = state[neighbor][2]
                        
                        defense_multiplier = 1 + enemy_level * 0.15
                        adjusted_enemy_strength = enemy_troops * defense_multiplier
                        success_ratio = my_troops / max(adjusted_enemy_strength, 1)
                        
                        if success_ratio >= 2.0:  # 敵はより慎重に
                            importance = self.FORTRESS_IMPORTANCE.get(neighbor, 5)
                            weakness = max(0, 25 - enemy_troops)
                            priority = 100 + importance * 2 + weakness + int(success_ratio * 5)
                            actions.append((priority, 1, my_fort, neighbor))
                            considered_actions.add(action_key)

        # === 部隊の戦略的再配置 ===
        for my_fort in my_fortresses:
            level = state[my_fort][2]
            troops = state[my_fort][3]
            enemy_neighbors = self.count_enemy_neighbors(my_fort, state)
            
            # 後方で部隊が過剰に溜まっている場合
            if enemy_neighbors == 0 and troops >= self.fortress_limit[level] * 0.85:
                neighbors = state[my_fort][5]
                best_target = None
                best_priority = 0
                
                for neighbor in neighbors:
                    action_key = (1, my_fort, neighbor)
                    if state[neighbor][0] == 1 and action_key not in considered_actions:
                        neighbor_enemy_count = self.count_enemy_neighbors(neighbor, state)
                        neighbor_troops = state[neighbor][3]
                        neighbor_level = state[neighbor][2]
                        
                        if neighbor_enemy_count > 0:
                            troop_deficit = self.fortress_limit[neighbor_level] * 0.6 - neighbor_troops
                            if troop_deficit > 0:
                                priority = 60 + neighbor_enemy_count * 10 + troop_deficit
                                if priority > best_priority:
                                    best_priority = priority
                                    best_target = neighbor
                
                if best_target is not None:
                    action_key = (1, my_fort, best_target)
                    actions.append((best_priority, 1, my_fort, best_target))
                    considered_actions.add(action_key)

        # 最も優先度の高いアクションを実行
        if actions:
            actions.sort(reverse=True, key=lambda x: x[0])
            _, command, subject, to = actions[0]
            
            # デバッグ出力
            if self.step < 500:
                if command == 1:
                    action_type = "攻撃" if state[to][0] != 1 else "支援"
                    print(f"  → 実行: {action_type} {subject}→{to} (優先度{actions[0][0]})")
                elif command == 2:
                    print(f"  → 実行: アップグレード 要塞{subject} (優先度{actions[0][0]})")
            
            return command, subject, to

        # 何もすることがない場合
        return 0, 0, 0


    def is_already_attacking(self, from_fort, to_fort, spawning_pawns, moving_pawns):
        """指定された経路で既に攻撃部隊を送っているか確認"""
        for pawn in spawning_pawns:
            try:
                if len(pawn) == 4:
                    pawn_team, kind, pawn_from, pawn_to = pawn
                elif len(pawn) >= 5:
                    pawn_team, kind, pawn_from, pawn_to = pawn[0], pawn[1], pawn[2], pawn[3]
                else:
                    continue
                
                if pawn_team == 1 and pawn_from == from_fort and pawn_to == to_fort:
                    return True
            except (ValueError, IndexError):
                continue
        
        for pawn in moving_pawns:
            try:
                pawn_team, kind, pawn_from, pawn_to, pos = pawn
                if pawn_team == 1 and pawn_from == from_fort and pawn_to == to_fort:
                    return True
            except (ValueError, IndexError):
                continue
        
        return False


    def count_enemy_neighbors(self, fort_id, state):
        """指定された要塞に隣接する敵要塞の数を数える"""
        neighbors = state[fort_id][5]
        return sum(1 for n in neighbors if state[n][0] == 2)

    # def update(self, info) -> tuple[int, int, int]:
    #     """
    #     戦略的な判断でコマンドを選択（改善版）
    #     """
    #     team, state, moving_pawns, spawning_pawns, done = info
    #     self.step += 1

    #     # ゲームフェーズの判定
    #     if self.step < 3000:
    #         phase = "early"
    #     elif self.step < 15000:
    #         phase = "mid"
    #     else:
    #         phase = "late"

    #     # 優先度付きアクションリスト
    #     actions = []
    #     considered_actions = set()  # 重複防止

    #     # 自分の要塞と敵の要塞を分類
    #     my_fortresses = [i for i in range(12) if state[i][0] == 1]
    #     enemy_fortresses = [i for i in range(12) if state[i][0] == 2]
    #     neutral_fortresses = [i for i in range(12) if state[i][0] == 0]

    #     # === 緊急防御: 最優先 ===
    #     under_attack = {}
    #     incoming_threats = {}  # 各要塞への脅威度を計算
        
    #     for pawn in moving_pawns:
    #         pawn_team, kind, from_, to, pos = pawn
    #         if pawn_team == 2 and state[to][0] == 1:
    #             if to not in under_attack:
    #                 under_attack[to] = []
    #             under_attack[to].append((from_, pos))
                
    #             # 到着までの距離を推定
    #             distance = 100 - pos  # 簡易的な距離計算
    #             threat = kind * 10 / max(distance, 1)  # 部隊数と距離から脅威度計算
    #             incoming_threats[to] = incoming_threats.get(to, 0) + threat

    #     # 防御が必要な要塞への支援
    #     for target_fort, threats in under_attack.items():
    #         current_defenders = state[target_fort][3]
    #         total_threat = sum(kind for _, (_, pos) in zip(threats, threats))
            
    #         # 防御が不足している場合
    #         if current_defenders < total_threat * 1.2:
    #             neighbors = state[target_fort][5]
    #             for my_fort in neighbors:
    #                 action_key = (1, my_fort, target_fort)
    #                 if (state[my_fort][0] == 1 and 
    #                     state[my_fort][3] >= 5 and
    #                     action_key not in considered_actions):
    #                     priority = 200 + incoming_threats.get(target_fort, 0) * 10
    #                     actions.append((priority, 1, my_fort, target_fort))
    #                     considered_actions.add(action_key)

    #     # === 序盤戦略: 重要な中立要塞の制圧 ===
    #     if phase == "early":
    #         for my_fort in my_fortresses:
    #             if state[my_fort][3] >= 4:
    #                 neighbors = state[my_fort][5]
    #                 for neighbor in neighbors:
    #                     action_key = (1, my_fort, neighbor)
    #                     if state[neighbor][0] == 0 and action_key not in considered_actions:
    #                         importance = self.FORTRESS_IMPORTANCE.get(neighbor, 5)
    #                         ease = max(0, 30 - state[neighbor][3])
    #                         # 既に攻撃部隊を送っているか確認
    #                         already_attacking = self.is_already_attacking(my_fort, neighbor, spawning_pawns, moving_pawns)
                            
    #                         if not already_attacking:
    #                             priority = 150 + importance * 5 + ease
    #                             actions.append((priority, 1, my_fort, neighbor))
    #                             considered_actions.add(action_key)

    #     # === 中立要塞への計算された攻撃 ===
    #     for my_fort in my_fortresses:
    #         if state[my_fort][3] >= 6:
    #             neighbors = state[my_fort][5]
    #             for neighbor in neighbors:
    #                 action_key = (1, my_fort, neighbor)
    #                 if state[neighbor][0] == 0 and action_key not in considered_actions:
    #                     # 攻撃成功率を計算
    #                     my_troops = state[my_fort][3]
    #                     neutral_troops = state[neighbor][3]
                        
    #                     # 簡易的な成功判定: 自軍の部隊が相手の1.5倍以上
    #                     success_ratio = my_troops / max(neutral_troops, 1)
                        
    #                     if success_ratio >= 1.5:
    #                         importance = self.FORTRESS_IMPORTANCE.get(neighbor, 5)
    #                         priority = 120 + importance * 3 + int(success_ratio * 10)
    #                         actions.append((priority, 1, my_fort, neighbor))
    #                         considered_actions.add(action_key)

    #     # === 敵要塞への戦略的攻撃 ===
    #     for my_fort in my_fortresses:
    #         # 部隊数に応じた閾値（レベルによって変動）
    #         level = state[my_fort][2]
    #         min_troops = max(10, self.fortress_limit[level] * 0.4)
            
    #         if state[my_fort][3] >= min_troops:
    #             neighbors = state[my_fort][5]
    #             for neighbor in neighbors:
    #                 action_key = (1, my_fort, neighbor)
    #                 if state[neighbor][0] == 2 and action_key not in considered_actions:
    #                     my_troops = state[my_fort][3]
    #                     enemy_troops = state[neighbor][3]
    #                     enemy_level = state[neighbor][2]
                        
    #                     # 攻撃成功の見込み計算
    #                     # 敵の要塞レベルとターレット数を考慮
    #                     defense_multiplier = 1 + enemy_level * 0.15
    #                     adjusted_enemy_strength = enemy_troops * defense_multiplier
                        
    #                     success_ratio = my_troops / max(adjusted_enemy_strength, 1)
                        
    #                     if success_ratio >= 1.8:  # より慎重な攻撃
    #                         importance = self.FORTRESS_IMPORTANCE.get(neighbor, 5)
    #                         weakness = max(0, 25 - enemy_troops)
    #                         priority = 100 + importance * 2 + weakness + int(success_ratio * 5)
    #                         actions.append((priority, 1, my_fort, neighbor))
    #                         considered_actions.add(action_key)

    #     # === アップグレード戦略（改善版）===
    #     upgrade_priority_base = 90 if phase == "mid" else 70
        
    #     # フェーズごとのアップグレード方針
    #     max_upgrade_level = {
    #         "early": 3,
    #         "mid": 4,
    #         "late": 5
    #     }[phase]

    #     # 中央の重要拠点は常に優先
    #     for fort_id in [4, 7]:
    #         if fort_id in my_fortresses:
    #             level = state[fort_id][2]
    #             troops = state[fort_id][3]
                
    #             if (state[fort_id][4] == -1 and 
    #                 level < max_upgrade_level and
    #                 troops >= self.fortress_limit[level] * 0.5):  # より積極的にアップグレード
    #                 priority = upgrade_priority_base + 40 + level * 8
    #                 actions.append((priority, 2, fort_id, 0))

    #     # その他の要塞のアップグレード
    #     for my_fort in my_fortresses:
    #         if my_fort not in [4, 7]:
    #             level = state[my_fort][2]
    #             troops = state[my_fort][3]
    #             importance = self.FORTRESS_IMPORTANCE.get(my_fort, 5)
    #             enemy_neighbors = self.count_enemy_neighbors(my_fort, state)
                
    #             # アップグレード条件を調整
    #             troops_threshold = self.fortress_limit[level] * (0.6 if enemy_neighbors > 0 else 0.7)
                
    #             if (state[my_fort][4] == -1 and 
    #                 level < max_upgrade_level and
    #                 troops >= troops_threshold):
    #                 priority = upgrade_priority_base + importance + level * 4 + enemy_neighbors * 8
    #                 actions.append((priority, 2, my_fort, 0))

    #     # === 部隊の戦略的再配置 ===
    #     for my_fort in my_fortresses:
    #         level = state[my_fort][2]
    #         troops = state[my_fort][3]
    #         enemy_neighbors = self.count_enemy_neighbors(my_fort, state)
            
    #         # 後方で部隊が過剰に溜まっている場合
    #         if enemy_neighbors == 0 and troops >= self.fortress_limit[level] * 0.8:
    #             neighbors = state[my_fort][5]
    #             best_target = None
    #             best_priority = 0
                
    #             for neighbor in neighbors:
    #                 action_key = (1, my_fort, neighbor)
    #                 if state[neighbor][0] == 1 and action_key not in considered_actions:
    #                     neighbor_enemy_count = self.count_enemy_neighbors(neighbor, state)
    #                     neighbor_troops = state[neighbor][3]
    #                     neighbor_level = state[neighbor][2]
                        
    #                     # 前線で部隊が不足している要塞を優先
    #                     if neighbor_enemy_count > 0:
    #                         troop_deficit = self.fortress_limit[neighbor_level] * 0.6 - neighbor_troops
    #                         if troop_deficit > 0:
    #                             priority = 60 + neighbor_enemy_count * 10 + troop_deficit
    #                             if priority > best_priority:
    #                                 best_priority = priority
    #                                 best_target = neighbor
                
    #             if best_target is not None:
    #                 action_key = (1, my_fort, best_target)
    #                 actions.append((best_priority, 1, my_fort, best_target))
    #                 considered_actions.add(action_key)

    #     # === 中盤以降の拡張戦略 ===
    #     if phase in ["mid", "late"] and len(my_fortresses) >= len(enemy_fortresses):
    #         for my_fort in my_fortresses:
    #             if state[my_fort][3] >= 8:
    #                 neighbors = state[my_fort][5]
    #                 for neighbor in neighbors:
    #                     action_key = (1, my_fort, neighbor)
    #                     if (state[neighbor][0] == 0 and 
    #                         state[neighbor][3] <= 15 and
    #                         action_key not in considered_actions):
    #                         priority = 85
    #                         actions.append((priority, 1, my_fort, neighbor))
    #                         considered_actions.add(action_key)

    #     # 最も優先度の高いアクションを実行
    #     if actions:
    #         actions.sort(reverse=True, key=lambda x: x[0])
    #         _, command, subject, to = actions[0]
    #         return command, subject, to

    #     # 何もすることがない場合
    #     return 0, 0, 0


    # def is_already_attacking(self, from_fort, to_fort, spawning_pawns, moving_pawns):
    #     """指定された経路で既に攻撃部隊を送っているか確認"""
    #     # 出発待ちの部隊をチェック
    #     for pawn in spawning_pawns:
    #         # データ構造を柔軟に処理
    #         try:
    #             if len(pawn) == 4:
    #                 pawn_team, kind, pawn_from, pawn_to = pawn
    #             elif len(pawn) >= 5:
    #                 pawn_team, kind, pawn_from, pawn_to = pawn[0], pawn[1], pawn[2], pawn[3]
    #             else:
    #                 continue
                
    #             if pawn_team == 1 and pawn_from == from_fort and pawn_to == to_fort:
    #                 return True
    #         except (ValueError, IndexError):
    #             # データ構造が想定外の場合はスキップ
    #             continue
        
    #     # 移動中の部隊をチェック
    #     for pawn in moving_pawns:
    #         try:
    #             pawn_team, kind, pawn_from, pawn_to, pos = pawn
    #             if pawn_team == 1 and pawn_from == from_fort and pawn_to == to_fort:
    #                 return True
    #         except (ValueError, IndexError):
    #             continue
        
    #     return False


    # def count_enemy_neighbors(self, fort_id, state):
    #     """指定された要塞に隣接する敵要塞の数を数える"""
    #     neighbors = state[fort_id][5]
    #     return sum(1 for n in neighbors if state[n][0] == 2)

    # # def update(self, info) -> tuple[int, int, int]:
    # #     """
    # #     毎ステップ呼ばれるメソッド

    # #     ゲームの状態を受け取り、実行するコマンドを返します。

    # #     Args:
    # #         info: ゲーム情報のタプル
    # #             - team (int): 自分 1、相手 2、中立 0
    # #             - state (list): 12個の要塞の状態
    # #                 state[i] = [team, kind, level, pawn_number, upgrade_time, [to_set]]
    # #             - moving_pawns (list): 移動中の部隊情報
    # #             - spawning_pawns (list): 出発待ちの部隊
    # #             - done (bool): ゲーム終了フラグ

    # #     Returns:
    # #         tuple[int, int, int]: (command, subject, to)
    # #             - command: 0=何もしない, 1=部隊移動, 2=アップグレード
    # #             - subject: 対象の要塞ID (0-11)
    # #             - to: 移動先の要塞ID (commandが1の場合のみ有効)
    # #     """
    # #     # ゲーム情報を展開
    # #     team, state, moving_pawns, spawning_pawns, done = info
    # #     self.step += 1

    # #     # ==========================================
    # #     # ここにあなたの戦略を実装してください
    # #     # ==========================================

    # #     # 例1: 何もしない
    # #     command, subject, to = 0, 0, 0

    # #     # 例2: 自分の要塞から敵要塞へ攻撃
    # #     # for i in range(12):
    # #     #     if state[i][0] == 1 and state[i][3] > 10:  # 自分の要塞で部隊が10以上
    # #     #         neighbors = state[i][5]  # 隣接要塞
    # #     #         enemy_neighbors = [n for n in neighbors if state[n][0] == 2]
    # #     #         if enemy_neighbors:
    # #     #             return 1, i, enemy_neighbors[0]  # 攻撃

    # #     # 例3: アップグレード
    # #     # for i in range(12):
    # #     #     if state[i][0] == 1 and state[i][4] == 0:  # 自分の要塞でアップグレード可能
    # #     #         level = state[i][2]
    # #     #         if state[i][3] >= fortress_limit[level] // 2:
    # #     #             return 2, i, 0  # アップグレード

    # #     return command, subject, to
