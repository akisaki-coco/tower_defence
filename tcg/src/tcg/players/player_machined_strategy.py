from tcg.controller import Controller
import random

# tcg.config がない場合は、クラス内の fortress_limit を使用します

class MachinedPlayerStrategy(Controller):
    """
    Complete Economy & Late Burst Strategy を統合した MachinedPlayer
    """

    # 防御的な設定（レベルごとの最大兵数）
    fortress_limit = [10, 10, 20, 30, 40, 50]

    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        self.core_zone = None 

    def team_name(self) -> str:
        return "Machined Economy Burst"
    
    def get_fort_strength(self, fort_info):
        """部隊の強さを計算（種類補正あり）"""
        kind = fort_info[1]
        pawns = fort_info[3]
        multiplier = 0.95 if kind == 1 else 0.65
        return pawns * multiplier

    def update(self, info) -> tuple[int, int, int]:
        """
        戦略的な判断でコマンドを選択
        """
        team, state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        # 自分のチームIDに合わせて調整（自分が1なら敵は2、自分が2なら敵は1）
        my_team = team
        enemy_team = 2 if team == 1 else 1

        # 自分の砦リスト
        my_forts = [i for i in range(12) if state[i][0] == my_team]

        # --- 0. コア・ゾーン定義 ---
        if self.core_zone is None:
            self.core_zone = set()
            for i in my_forts:
                self.core_zone.add(i)
                for neighbor in state[i][5]:
                    self.core_zone.add(neighbor)

        # --- 1. 経済完成チェック (Global Economy Check) ---
        # 「安全なのにまだレベル5じゃない砦」が1つでもあるか？
        economy_not_ready = False
        for i in my_forts:
            neighbors = state[i][5]
            # 隣接に敵がいるか確認
            has_enemy = any(state[n][0] == enemy_team for n in neighbors)
            
            # 安全、かつ通常砦(kind=0)、かつレベル5未満なら「準備未完了」
            if not has_enemy and state[i][1] == 0 and state[i][2] < 5:
                economy_not_ready = True
                break
        
        is_early_game = self.step < 2000
        actions = [] 

        # 全砦について行動を検討
        for i in my_forts:
            info_fort = state[i]
            neighbors = info_fort[5]
            
            has_enemy_neighbor = any(state[n][0] == enemy_team for n in neighbors)
            current_level = info_fort[2]
            
            # fortress_limit はクラス変数を使用
            max_pawns = self.fortress_limit[current_level]
            upgrade_cost = max_pawns // 2
            
            current_pawns = info_fort[3]
            current_kind = info_fort[1]
            
            is_overflowing = current_pawns >= max_pawns * 0.9
            sending_pawns = current_pawns // 2 # 攻撃/移動時に送る兵数
            
            # 自分の攻撃力計算
            # 便宜上、第4引数に兵数を入れて計算
            my_attack_power = self.get_fort_strength([0, current_kind, 0, sending_pawns, 0, 0])

            # ========================================================
            # 2. アップグレード (最優先)
            # ========================================================
            # 安全な場所なら、レベル5になるまで他のことは一切しない（内政フェーズ）
            if not has_enemy_neighbor and current_level < 5:
                # 工事中でなければ
                if info_fort[4] == -1: 
                    if current_pawns >= upgrade_cost:
                        # 即座にアップグレード実行（returnしてこのターンはこれに決定）
                        return 2, i, 0
                    else:
                        continue # 資金(兵士)を貯めるため何もしない

            # ========================================================
            # 3. 攻撃判定 (Attack Logic)
            # ========================================================
            best_target = None
            best_score = -999

            if sending_pawns >= 3: 
                for n in neighbors:
                    target = state[n]
                    target_team = target[0]
                    target_pawns = target[3]
                    target_kind = target[1]
                    
                    # 序盤は中央(4, 7)の中立には手を出さない
                    if is_early_game and n in [4, 7] and target_team == 0:
                        continue
                    
                    # 味方への攻撃はスキップ
                    if target_team == my_team:
                        continue

                    # 勝算計算
                    victory_threshold = target_pawns + 2.0
                    if target_team == enemy_team: 
                        victory_threshold += 3.0
                    
                    is_winnable = (sending_pawns > target_pawns) and (my_attack_power > victory_threshold)
                    
                    allow_attack = is_winnable
                    # 溢れそうで敵なら無理やりでも攻撃許可
                    if is_overflowing and target_team == enemy_team: 
                        allow_attack = True 
                    
                    if not allow_attack: 
                        continue

                    # --- スコア計算 ---
                    score = 0
                    if target_team == 0: # 中立
                        score = 100 - target_pawns
                        # 序盤で隣接が多いところは攻めにくいのでスコア下げ
                        if is_early_game and len(state[n][5]) >= 4: 
                            score -= 50
                    elif target_team == enemy_team: # 敵
                        score = 200
                        if target_pawns < 5: score += 50
                        if is_overflowing: score += 1000

                    # ★★★ 強化砦(kind=1)ボーナス ★★★
                    if target_kind == 1:
                        # 経済が完成していないなら、無理に狙わず通常の砦と同じ扱い
                        if economy_not_ready:
                            score += 50
                        # 経済完了！全力で取りに行く（バースト）
                        else:
                            score += 500
                            if target_team == enemy_team: score += 100

                    if score > best_score:
                        best_score = score
                        best_target = n

            if best_target is not None:
                # 行動リストに追加 (優先度, コマンドID, 元, 先)
                actions.append((best_score, 1, i, best_target))
            
            # ========================================================
            # 4. バケツリレー (Logistics / 移動)
            # ========================================================
            # 前線なら90%、後方なら40%で移動開始
            threshold = 0.9 if has_enemy_neighbor else 0.4
            
            if current_pawns > max_pawns * threshold:
                for n in neighbors:
                    target_n = state[n]
                    
                    # 味方への輸送のみ
                    if target_n[0] == my_team: 
                        if is_early_game and n in [4, 7]: continue

                        # 輸送許可判定
                        is_allowed = False
                        if n in self.core_zone: is_allowed = True
                        elif target_n[1] == 1: is_allowed = True # 強化砦へ送る
                        elif current_kind == 1: is_allowed = True
                        
                        if not is_allowed: continue

                        # 優先度
                        priority = 0
                        # 移動先の隣に敵がいるか（前線か）
                        is_frontline = any(state[nn][0] == enemy_team for nn in target_n[5])
                        target_is_hub = (target_n[1] == 1)

                        if is_frontline:
                            priority = 500 if is_overflowing else 60
                        
                        elif target_is_hub:
                            # 強化砦（ハブ）へ送る
                            priority = 1000 if is_overflowing else 55
                        
                        elif is_overflowing:
                            priority = 300
                        
                        if priority > 0:
                            actions.append((priority, 1, i, n))

        # 最も優先度の高いアクションを実行
        if actions:
            # 優先度順にソート（高い順）
            actions.sort(key=lambda x: x[0], reverse=True)
            # (優先度, コマンド, 元, 先)
            return actions[0][1], actions[0][2], actions[0][3]

        # 何もすることがない場合
        return 0, 0, 0
