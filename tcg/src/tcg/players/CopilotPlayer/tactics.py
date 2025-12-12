"""
Tactics Module - 高度な戦術とパターン

特定の状況に対する戦術的パターンを定義
"""

from typing import List, Tuple, Set


class TacticalPatterns:
    """戦術パターンライブラリ"""
    
    # グラフの隣接関係
    ADJACENCY = [
        [1, 3, 4],      # 0
        [0, 2, 4],      # 1
        [1, 4, 5],      # 2
        [0, 4, 6, 7],   # 3
        [0, 1, 2, 3, 5, 6, 7, 8],  # 4: 中央ハブ
        [2, 4, 7, 8],   # 5
        [3, 4, 7, 9],   # 6
        [3, 4, 5, 6, 8, 9, 10, 11],  # 7: 中央ハブ
        [4, 5, 7, 11],  # 8
        [6, 7, 10],     # 9
        [7, 9, 11],     # 10
        [7, 8, 10],     # 11
    ]
    
    # 戦略的要塞グループ
    TOP_FORTRESSES = [0, 1, 2]
    TOP_MID_FORTRESSES = [3, 4, 5]
    BOTTOM_MID_FORTRESSES = [6, 7, 8]
    BOTTOM_FORTRESSES = [9, 10, 11]
    CENTRAL_HUBS = [4, 7]
    
    @staticmethod
    def detect_pincer_attack_opportunity(state: List, team: int) -> List[Tuple]:
        """
        挟撃攻撃の機会を検出
        
        複数の要塞から1つの敵要塞を同時に攻撃できる状況
        """
        opportunities = []
        enemy_team = 2 if team == 1 else 1
        
        for target in range(12):
            if state[target][0] != enemy_team:
                continue
            
            # この敵要塞に隣接する味方要塞を探す
            adjacent_allies = []
            for ally in range(12):
                if state[ally][0] == team:
                    if target in TacticalPatterns.ADJACENCY[ally]:
                        adjacent_allies.append(ally)
            
            # 2つ以上の味方要塞から攻撃できる場合
            if len(adjacent_allies) >= 2:
                # 両方の要塞が十分な部隊を持っているか
                total_troops = sum(state[ally][3] for ally in adjacent_allies)
                target_troops = state[target][3]
                
                if total_troops > target_troops * 1.5:
                    opportunities.append((target, adjacent_allies, total_troops))
        
        return opportunities
    
    @staticmethod
    def detect_breakthrough_opportunity(state: List, team: int) -> List[Tuple]:
        """
        突破の機会を検出
        
        敵の防御線を突破して後方に進出できる状況
        """
        opportunities = []
        enemy_team = 2 if team == 1 else 1
        
        for my_fort in range(12):
            if state[my_fort][0] != team:
                continue
            
            # 隣接する弱い敵要塞を探す
            for neighbor in TacticalPatterns.ADJACENCY[my_fort]:
                if state[neighbor][0] == enemy_team and state[neighbor][3] < 8:
                    # この要塞を突破すると、さらに奥の要塞にアクセスできるか
                    second_layer = TacticalPatterns.ADJACENCY[neighbor]
                    valuable_targets = [
                        t for t in second_layer
                        if t not in TacticalPatterns.ADJACENCY[my_fort]
                    ]
                    
                    if valuable_targets:
                        opportunities.append((my_fort, neighbor, valuable_targets))
        
        return opportunities
    
    @staticmethod
    def detect_encirclement_danger(state: List, team: int) -> List[int]:
        """
        包囲される危険がある味方要塞を検出
        """
        endangered = []
        enemy_team = 2 if team == 1 else 1
        
        for my_fort in range(12):
            if state[my_fort][0] != team:
                continue
            
            neighbors = TacticalPatterns.ADJACENCY[my_fort]
            enemy_count = sum(1 for n in neighbors if state[n][0] == enemy_team)
            ally_count = sum(1 for n in neighbors if state[n][0] == team)
            
            # 敵に多く囲まれ、味方の援軍ルートが少ない
            if enemy_count >= 2 and ally_count <= 1:
                endangered.append(my_fort)
        
        return endangered
    
    @staticmethod
    def find_supply_line(state: List, team: int, from_id: int, to_id: int) -> List[int]:
        """
        2つの要塞間の補給線（最短パス）を探索
        
        BFSで味方要塞のみを経由する最短パスを見つける
        """
        if from_id == to_id:
            return [from_id]
        
        queue = [(from_id, [from_id])]
        visited = {from_id}
        
        while queue:
            current, path = queue.pop(0)
            
            for neighbor in TacticalPatterns.ADJACENCY[current]:
                if neighbor in visited:
                    continue
                
                if state[neighbor][0] != team and neighbor != to_id:
                    continue
                
                new_path = path + [neighbor]
                
                if neighbor == to_id:
                    return new_path
                
                visited.add(neighbor)
                queue.append((neighbor, new_path))
        
        return []  # パスが見つからない
    
    @staticmethod
    def calculate_control_zones(state: List, team: int) -> Set[int]:
        """
        支配圏を計算
        
        味方要塞と、その隣接する中立/敵要塞を含む
        """
        control_zone = set()
        
        for i in range(12):
            if state[i][0] == team:
                control_zone.add(i)
                # 隣接する要塞も影響圏に含める
                for neighbor in TacticalPatterns.ADJACENCY[i]:
                    control_zone.add(neighbor)
        
        return control_zone
    
    @staticmethod
    def identify_choke_points(state: List, team: int) -> List[int]:
        """
        チョークポイント（戦略的要衝）を特定
        
        制圧すると敵の動きを大きく制限できる要塞
        """
        choke_points = []
        enemy_team = 2 if team == 1 else 1
        
        # 中央ハブは常にチョークポイント
        for hub in TacticalPatterns.CENTRAL_HUBS:
            if state[hub][0] != team:
                choke_points.append(hub)
        
        # 敵陣と味方陣を分断する位置にある要塞
        for i in range(12):
            if state[i][0] == 0:  # 中立
                neighbors = TacticalPatterns.ADJACENCY[i]
                ally_neighbors = sum(1 for n in neighbors if state[n][0] == team)
                enemy_neighbors = sum(1 for n in neighbors if state[n][0] == enemy_team)
                
                # 両陣営に隣接している中立要塞はチョークポイント
                if ally_neighbors > 0 and enemy_neighbors > 0:
                    choke_points.append(i)
        
        return choke_points
    
    @staticmethod
    def detect_expansion_corridors(state: List, team: int) -> List[List[int]]:
        """
        拡張回廊を検出
        
        連続する中立要塞の鎖で、制圧すると大きな領域拡大になる
        """
        corridors = []
        visited = set()
        
        for start in range(12):
            if state[start][0] != 0 or start in visited:
                continue
            
            # BFSで連結する中立要塞を探す
            corridor = []
            queue = [start]
            local_visited = {start}
            
            while queue:
                current = queue.pop(0)
                corridor.append(current)
                visited.add(current)
                
                for neighbor in TacticalPatterns.ADJACENCY[current]:
                    if neighbor not in local_visited and state[neighbor][0] == 0:
                        local_visited.add(neighbor)
                        queue.append(neighbor)
            
            # 2つ以上の中立要塞が連結している場合
            if len(corridor) >= 2:
                # 味方に隣接しているか確認
                adjacent_to_ally = any(
                    any(state[n][0] == team for n in TacticalPatterns.ADJACENCY[fort])
                    for fort in corridor
                )
                if adjacent_to_ally:
                    corridors.append(corridor)
        
        return corridors
    
    @staticmethod
    def calculate_fortress_connectivity(state: List, team: int) -> float:
        """
        要塞間の連結性を計算
        
        味方要塞がどれだけよく連結されているかのスコア
        """
        my_fortresses = [i for i in range(12) if state[i][0] == team]
        
        if len(my_fortresses) <= 1:
            return 1.0
        
        # 全ての味方要塞ペア間のパスの長さを計算
        total_connections = 0
        successful_connections = 0
        
        for i, fort1 in enumerate(my_fortresses):
            for fort2 in my_fortresses[i+1:]:
                total_connections += 1
                path = TacticalPatterns.find_supply_line(state, team, fort1, fort2)
                if path:
                    successful_connections += 1
        
        if total_connections == 0:
            return 1.0
        
        return successful_connections / total_connections
    
    @staticmethod
    def predict_enemy_next_target(state: List, team: int, moving_pawns: List) -> List[Tuple]:
        """
        敵の次の攻撃目標を予測
        
        敵の部隊配置と移動から次の攻撃を予測
        """
        enemy_team = 2 if team == 1 else 1
        predictions = []
        
        # 敵の部隊が集中している要塞を検出
        enemy_fortresses = [i for i in range(12) if state[i][0] == enemy_team]
        
        for enemy_fort in enemy_fortresses:
            troops = state[enemy_fort][3]
            
            # 部隊が多い要塞は攻撃の準備中
            if troops >= 15:
                # 隣接する味方要塞が標的の可能性
                neighbors = TacticalPatterns.ADJACENCY[enemy_fort]
                for neighbor in neighbors:
                    if state[neighbor][0] == team:
                        threat_level = troops * 0.5  # 送られる部隊は半分
                        predictions.append((neighbor, enemy_fort, threat_level))
        
        # 移動中の敵部隊から予測
        for pawn in moving_pawns:
            pawn_team, kind, from_, to, pos = pawn
            if pawn_team == enemy_team and state[to][0] == team:
                # この要塞は攻撃されている
                predictions.append((to, from_, 1.0))
        
        return predictions
