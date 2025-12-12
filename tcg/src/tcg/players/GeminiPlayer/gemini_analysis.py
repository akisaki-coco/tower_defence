import math
from tcg.config import pos_fortress, fortress_limit, fortress_cool
from .gemini_utils import get_travel_time, get_neighbors

class FortressState:
    def __init__(self, id, state_list):
        self.id = id
        self.team = state_list[0] # 0: Neutral, 1: Me, 2: Enemy
        self.kind = state_list[1]
        self.level = state_list[2]
        self.troops = state_list[3]
        self.upgrade_timer = state_list[4]
        self.neighbors = state_list[5]
        
    def is_mine(self):
        return self.team == 1
        
    def is_enemy(self):
        return self.team == 2
        
    def is_neutral(self):
        return self.team == 0
    
    def production_rate(self):
        if self.team == 0: return 0 # Neutrals don't produce? Wait, user said they do.
        # User said: "最初は中立勢力が砦を保持しており、それらの勢力もプレイヤーと同じように兵士の増加が行われます。"
        # So Neutrals DO produce.
        cool = fortress_cool[self.kind][self.level]
        if cool == 0: return 0
        return 1.0 / cool

    def cap(self):
        return fortress_limit[self.level]

class GameAnalysis:
    def __init__(self, info):
        self.team_id, self.raw_state, self.pawns, self.spawn_points, self.done = info
        self.fortresses = [FortressState(i, s) for i, s in enumerate(self.raw_state)]
        self.my_fortresses = [f for f in self.fortresses if f.is_mine()]
        self.enemy_fortresses = [f for f in self.fortresses if f.is_enemy()]
        self.neutral_fortresses = [f for f in self.fortresses if f.is_neutral()]
        
        self.incoming_allies = [[] for _ in range(12)] # List of (arrival_time, count, kind)
        self.incoming_enemies = [[] for _ in range(12)]
        
        self.process_pawns()
        
    def process_pawns(self):
        for p in self.pawns:
            # Game passes [team, kind, from_, to, [x, y]]
            team = p[0]
            kind = p[1]
            from_id = p[2]
            to_id = p[3]
            pos = p[4]
            x, y = pos
            
            count = 1 # Each entry is 1 pawn unit
            
            # Calculate distance to target
            tx, ty = pos_fortress[to_id]
            dist = math.sqrt((x - tx)**2 + (y - ty)**2)
            
            # Effective distance to arrival (radius 45)
            eff_dist = max(0, dist - 45)
            
            speed = 1.5 if kind == 0 else 1.0
            time_steps = int(math.ceil(eff_dist / speed))
            
            if team == 1:
                self.incoming_allies[to_id].append((time_steps, count, kind))
            elif team == 2:
                self.incoming_enemies[to_id].append((time_steps, count, kind))
                
        # Sort by arrival time
        for i in range(12):
            self.incoming_allies[i].sort(key=lambda x: x[0])
            self.incoming_enemies[i].sort(key=lambda x: x[0])

    def predict_state(self, fortress_id, time_horizon):
        """
        Predict the state of a fortress after time_horizon steps.
        Returns: (predicted_team, predicted_troops)
        This is a simplified simulation.
        """
        f = self.fortresses[fortress_id]
        current_team = f.team
        current_troops = f.troops
        
        # Events: (time, type, amount, kind)
        # type: 0=production, 1=ally_arrival, 2=enemy_arrival
        events = []
        
        # Add arrivals
        for t, amt, kind in self.incoming_allies[fortress_id]:
            if t <= time_horizon:
                events.append((t, 1, amt, kind))
                
        for t, amt, kind in self.incoming_enemies[fortress_id]:
            if t <= time_horizon:
                events.append((t, 2, amt, kind))
                
        # Sort events
        events.sort(key=lambda x: x[0])
        
        last_time = 0
        
        for t, type, amt, kind in events:
            # Production until this event
            dt = t - last_time
            if current_team != 0 or True: # Neutrals also produce
                # Production logic
                # We need to know the rate.
                # Assuming level doesn't change (ignoring upgrades for prediction)
                cool = fortress_cool[f.kind][f.level]
                if cool > 0:
                    # How many produced?
                    # This is tricky because it's discrete.
                    # Approximate:
                    produced = dt / cool
                    # Cap check
                    cap = fortress_limit[f.level]
                    if current_troops < cap:
                        current_troops = min(cap, current_troops + produced)
            
            last_time = t
            
            # Handle event
            if type == 1: # Ally arrival
                if current_team == 1:
                    current_troops += amt
                else:
                    # Combat
                    dmg = amt * (0.65 if kind == 0 else 0.95)
                    current_troops -= dmg
                    if current_troops < 0:
                        current_team = 1
                        current_troops = -current_troops # Remainder becomes ours? 
                        # Wait, game logic: if < 0, team changes, troops = 0?
                        # No, "if self.state[to][3] < 0: self.state[to] = [team, ... 1, 0, ...]"
                        # So troops reset to 0.
                        # But wait, if I attack with 100 and they have 10, I should have troops left.
                        # The game logic says:
                        # state[to][3] -= damage
                        # if state[to][3] < 0: state[to] = ... troops=0
                        # So the attacker LOSES all troops upon impact, dealing damage.
                        # If damage > defenders, the fortress is taken and starts with 0 troops.
                        # This is very important. Attacking troops are CONSUMED.
                        current_troops = 0
                        
            elif type == 2: # Enemy arrival
                if current_team == 2:
                    current_troops += amt
                else:
                    dmg = amt * (0.65 if kind == 0 else 0.95)
                    current_troops -= dmg
                    if current_troops < 0:
                        current_team = 2
                        current_troops = 0
                        
        # Final production until horizon
        dt = time_horizon - last_time
        if dt > 0:
             cool = fortress_cool[f.kind][f.level]
             if cool > 0:
                produced = dt / cool
                cap = fortress_limit[f.level]
                if current_troops < cap:
                    current_troops = min(cap, current_troops + produced)
                    
        return current_team, current_troops

    def get_threat_level(self, fortress_id):
        """
        Calculate threat level for a fortress.
        Positive: We are safe.
        Negative: We are in danger.
        """
        # Look ahead 200 steps (approx travel time across map)
        team, troops = self.predict_state(fortress_id, 300)
        if team == 1:
            return troops
        else:
            return -troops # Negative means enemy controls it
