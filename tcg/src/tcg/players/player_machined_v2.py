from tcg.controller import Controller
import random

class MachinedPlayerv2(Controller):
    """
    テンプレートAIプレイヤー + Economy & Late Burst Strategy
    """

    # 防御的な設定（多くの部隊を溜められる）
    fortress_limit = [10, 10, 20, 30, 40, 50]

    # FORTRESS_IMPORTANCEの設定
    FORTRESS_IMPORTANCE = {
        0: 10, 1: 10, 2: 10,      # 上側エリア
        3: 1, 4: 10, 5: 1,     # 中央上
        6: 4, 7: 10, 8: 1,     # 中央下
        9: 10, 10: 10, 11: 10     # 下側エリア
    }

    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        self.prev_team_state = None
        self.attacking_fort = None
        self.target_fort = None

    def team_name(self) -> str:
        return "Machined Player V2"
    
    def get_fort_strength(self, kind, pawns):
        """
        部隊の強さを計算（種類補正あり）
        Kind 1 (強化砦) は係数 0.95 (強い)、通常は 0.65 として計算
        """
        multiplier = 0.95 if kind == 1 else 0.65
        return pawns * multiplier
    
    def count_enemy_neighbors(self, fort_id, state):
        """指定された要塞に隣接する敵要塞の数を数える"""
        neighbors = state[fort_id][5]
        return sum(1 for n in neighbors if state[n][0] == 2)

    def update(self, info) -> tuple[int, int, int]:
        team, state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        actions = []
        
        # 自分の要塞を取得
        my_fortresses = [i for i in range(12) if state[i][0] == 1]
        
        # === 0. 経済完成チェック (Global Economy Check) ===
        # 戦略：安全な通常砦がすべてLv5になるまでは、無茶な拡張（特にKind1への攻撃）を控える
        economy_not_ready = False
        for i in my_fortresses:
            neighbors = state[i][5]
            has_enemy = any(state[n][0] == 2 for n in neighbors)
            # 安全(敵が隣接していない)、かつ通常砦(Kind 0)、かつレベル5未満なら「準備未完了」
            if not has_enemy and state[i][1] == 0 and state[i][2] < 5:
                economy_not_ready = True
                break

        # === 1. 緊急防御: 最優先 (戦力ベース改良版) ===
        under_attack = {}
        incoming_threats = {}
        
        for pawn in moving_pawns:
            pawn_team, kind, from_, to, pos = pawn
            # 距離計算
            distance = 1.0 if isinstance(pos, (list, tuple)) else max(1.0, 100 - float(pos))

            if pawn_team == 2 and state[to][0] == 1:
                if to not in under_attack:
                    under_attack[to] = []
                under_attack[to].append((from_, pos))

                # 脅威度を「戦力」ベースで計算
                threat_power = self.get_fort_strength(kind, 10) 
                threat = threat_power / distance
                incoming_threats[to] = incoming_threats.get(to, 0) + threat

        # 防御が必要な要塞への支援
        for target_fort, total_threat in incoming_threats.items():
            my_fort_info = state[target_fort]
            # 現在の守備隊の戦力を計算
            current_defenders_power = self.get_fort_strength(my_fort_info[1], my_fort_info[3])

            if current_defenders_power < total_threat * 1.2:
                neighbors = state[target_fort][5]
                for my_fort in neighbors:
                    supporter_info = state[my_fort]
                    supporter_power = self.get_fort_strength(supporter_info[1], supporter_info[3])
                    
                    if (supporter_info[0] == 1 and supporter_power >= 5):
                        priority = 200 + total_threat * 10
                        actions.append((priority, 1, my_fort, target_fort))


        # === 2. アップグレード戦略（既存ロジック維持 + Economy優先）===
        # 経済未完成なら、安全な砦のアップグレードを非常に高く優先する
        upgrade_base_priority = 300 if economy_not_ready else 100

        for my_fort in my_fortresses:
            level = state[my_fort][2]
            troops = state[my_fort][3]
            max_troops = self.fortress_limit[level]
            enemy_neighbors = self.count_enemy_neighbors(my_fort, state)
            
            # 安全な場所ならLv5まで最優先で上げる
            if enemy_neighbors == 0 and level < 5:
                 if state[my_fort][4] == -1 and troops >= max_troops * 0.4:
                    priority = upgrade_base_priority + 50 + level * 10
                    actions.append((priority, 2, my_fort, 0))
            # 敵が近くにいる場合などは既存のロジック
            elif state[my_fort][4] == -1 and level < 4 and troops >= max_troops * 0.5:
                    importance = self.FORTRESS_IMPORTANCE.get(my_fort, 5)
                    priority = 100 + importance + level * 10
                    actions.append((priority, 2, my_fort, 0))


        # === 3. 敵要塞・中立要塞への戦略的攻撃 (改良版) ===
        for my_fort in my_fortresses:
            info = state[my_fort]
            sending_pawns = info[3] // 2  # 送る兵数は現在の半分と仮定
            if sending_pawns < 3: continue

            # 自軍の攻撃力を計算
            my_attack_power = self.get_fort_strength(info[1], sending_pawns)
            
            neighbors = info[5]
            for neighbor in neighbors:
                target_info = state[neighbor]
                target_team = target_info[0]
                target_pawns = target_info[3]
                target_kind = target_info[1]

                # 味方への攻撃はスキップ
                if target_team == 1: continue

                # 勝算計算 (Victory Threshold)
                victory_threshold = target_pawns + 2.0
                if target_team == 2: 
                    victory_threshold += 3.0 # 敵の場合はさらに余裕を持つ
                
                # 実際の戦力比較
                is_winnable = (sending_pawns > target_pawns) and (my_attack_power > victory_threshold)

                # 溢れそうな場合は無理やり攻撃することもある
                is_overflowing = info[3] >= self.fortress_limit[info[2]] * 0.9
                if is_overflowing and target_team == 2:
                    is_winnable = True

                if is_winnable:
                    score = 0
                    
                    # 基本スコア
                    if target_team == 0: # 中立
                        score = 100 - target_pawns
                    elif target_team == 2: # 敵
                        score = 200
                        if target_pawns < 5: score += 50
                    
                    # ★★★ 強化砦（Kind 1）ボーナス ★★★
                    if target_kind == 1:
                        if economy_not_ready:
                            # 経済未完成なら、無理せず通常の砦と同じ扱い
                            score += 50
                        else:
                            # 経済完了なら全力で取りに行く (Late Burst)
                            score += 500
                            if target_team == 2: score += 100
                    
                    # 優先度算出
                    priority = 100 + score
                    actions.append((priority, 1, my_fort, neighbor))

        # === 4. 部隊の戦略的再配置（バケツリレー）===
        # (既存のロジックが優秀なので、そのまま利用しつつ少し調整)
        for my_fort in my_fortresses:
            level = state[my_fort][2]
            troops = state[my_fort][3]
            max_troops = self.fortress_limit[level]
            enemy_neighbors = self.count_enemy_neighbors(my_fort, state)
            
            has_enemy_neighbor = enemy_neighbors > 0
            threshold = 0.9 if has_enemy_neighbor else 0.4
            
            if troops > max_troops * threshold: 
                neighbors = state[my_fort][5]
                best_target = None
                best_priority = 0
                
                for neighbor in neighbors:
                    if state[neighbor][0] == 1: # 味方のみ
                        neighbor_enemy_count = self.count_enemy_neighbors(neighbor, state)
                        
                        priority = 0
                        # 前線への輸送
                        if neighbor_enemy_count > 0:
                             priority = 500 if troops >= max_troops * 0.9 else 60
                        # 強化砦(Kind 1)への集結 (Economy完了後)
                        elif state[neighbor][1] == 1 and not economy_not_ready:
                             priority = 400
                        
                        if priority > best_priority:
                            best_priority = priority
                            best_target = neighbor

                # 溢れ防止の緊急移動
                if best_target is None and troops >= max_troops * 0.9:
                     for neighbor in neighbors:
                         if state[neighbor][0] == 1:
                             best_target = neighbor
                             best_priority = 300
                             break

                if best_target is not None:
                    # 優先度に微小なランダム値を加える
                    randomized_priority = best_priority + random.uniform(0, 0.1)
                    actions.append((randomized_priority, 1, my_fort, best_target))

        # 最も優先度の高いアクションを実行
        if actions:
            actions.sort(reverse=True, key=lambda x: x[0])
            _, command, subject, to = actions[0]
            
            # デバッグ出力 (必要に応じて)
            # if self.step < 500:
            #     print(f"Action: {command} from {subject} to {to}, Prio: {actions[0][0]}")
            
            return command, subject, to

        return 0, 0, 0
