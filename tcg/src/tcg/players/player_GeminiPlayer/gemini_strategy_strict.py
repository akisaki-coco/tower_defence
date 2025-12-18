import random
from tcg.config import fortress_limit
from .gemini_analysis import GameAnalysis
from .gemini_utils import get_travel_time, get_neighbors

class GeminiStrategyStrict:
    def __init__(self):
        self.step = 0
        
    def get_best_move(self, analysis: GameAnalysis):
        self.step += 1
        
        # --- 1. Emergency Defense ---
        # If any of my fortresses will be captured soon, send help immediately.
        for f in analysis.my_fortresses:
            # Predict short term (e.g. 50-100 steps)
            pred_team, pred_troops = analysis.predict_state(f.id, 100)
            if pred_team != 1:
                # Need reinforcements!
                needed = pred_troops + 5
                
                # Find neighbors who can help
                best_helper = None
                best_helper_score = -999
                
                for n_id in f.neighbors:
                    n = analysis.fortresses[n_id]
                    if n.is_mine() and n.troops > 5:
                        # Can it arrive in time?
                        dist = get_travel_time(n_id, f.id, n.kind)
                        if dist < 150: # Rough check, allow slightly longer distance
                            score = n.troops - dist * 0.1
                            if score > best_helper_score:
                                best_helper_score = score
                                best_helper = n
                
                if best_helper:
                    return 1, best_helper.id, f.id

        # --- 2. Opportunistic Upgrade ---
        # Upgrade if safe and efficient
        for f in analysis.my_fortresses:
            if f.upgrade_timer == -1 and f.level < 5:
                cost = fortress_limit[f.level] // 2
                if f.troops >= cost:
                    # Safety check: Don't upgrade if under threat
                    pred_team, _ = analysis.predict_state(f.id, 300)
                    if pred_team == 1:
                        # Also check if we have enough troops remaining after cost
                        # to defend against immediate neighbors
                        remaining = f.troops - cost
                        safe = True
                        for n_id in f.neighbors:
                            n = analysis.fortresses[n_id]
                            if n.is_enemy() and n.troops > remaining:
                                safe = False
                                break
                        
                        if safe:
                            return 2, f.id, 0

        # --- 3. Coordinated Attack / Expansion ---
        # Evaluate all enemy/neutral nodes as targets
        targets = []
        for f in analysis.fortresses:
            if not f.is_mine():
                targets.append(f)
        
        best_action = None
        best_score = -float('inf')
        
        for target in targets:
            # Who can attack this target?
            attackers = []
            total_dmg = 0
            
            for n_id in target.neighbors:
                n = analysis.fortresses[n_id]
                # Minimum troops to attack:
                # Must be > 2 to send anything.
                # To avoid "trickling" (sending 1 by 1), we should require a larger batch.
                # E.g., at least 20% of capacity or absolute number like 5.
                min_attack_size = max(5, n.cap() * 0.2)
                
                if n.is_mine() and n.troops > min_attack_size: 
                    dmg = (n.troops // 2) * (0.65 if n.kind == 0 else 0.95)
                    attackers.append((n, dmg))
                    total_dmg += dmg
            
            if not attackers:
                continue
                
            # Predict target state
            # Use average travel time of attackers
            avg_dist = sum(get_travel_time(a[0].id, target.id, a[0].kind) for a in attackers) / len(attackers)
            pred_team, pred_troops = analysis.predict_state(target.id, int(avg_dist))
            
            if pred_team == 1: continue # Already ours
            
            # STRICT ATTACK CONDITION
            # User wants: My Force >= Target Force * 1.5
            # We compare total potential damage vs predicted enemy troops
            
            threshold_multiplier = 1.5
            
            if total_dmg < pred_troops * threshold_multiplier:
                # We cannot guarantee victory with current available troops.
                # Do not attack.
                continue
            
            # If we are here, we can win.
            score = 1000
            
            # Value of target
            if target.is_neutral():
                score += 500 # Expansion priority
                score -= pred_troops * 5 # Cheaper is better
            else:
                score += 800 # Enemy priority
                score += target.level * 200 # High level enemy is valuable
                score -= pred_troops * 2
            
            # Distance penalty
            score -= avg_dist
            
            if score > best_score:
                best_score = score
                # Pick the best attacker (most troops)
                # Filter attackers again to ensure we don't pick one that fell below threshold during loop (unlikely but safe)
                valid_attackers = [a for a in attackers if a[0].troops > max(5, a[0].cap() * 0.2)]
                if valid_attackers:
                    valid_attackers.sort(key=lambda x: x[0].troops, reverse=True)
                    best_action = (1, valid_attackers[0][0].id, target.id)
        
        if best_action:
            return best_action

        # --- 4. Balance / Forwarding ---
        # If no good attacks, move troops to front lines
        for f in analysis.my_fortresses:
            if f.troops > f.cap() * 0.8:
                # Find best neighbor
                best_n = None
                best_n_score = -999
                
                for n_id in f.neighbors:
                    n = analysis.fortresses[n_id]
                    if n.is_mine():
                        s = 0
                        if n.troops < n.cap() * 0.5: s += 50
                        # Check if n has enemy neighbors
                        if any(analysis.fortresses[nn].is_enemy() for nn in n.neighbors):
                            s += 100
                        
                        if s > best_n_score:
                            best_n_score = s
                            best_n = n_id
                
                if best_n is not None:
                    return 1, f.id, best_n

        return 0, 0, 0
