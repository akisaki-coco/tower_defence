import random
from tcg.config import fortress_limit
from .gemini_analysis import GameAnalysis
from .gemini_utils import get_travel_time, get_neighbors

class GeminiStrategy:
    def __init__(self):
        self.step = 0
        
    def get_best_move(self, analysis: GameAnalysis):
        self.step += 1
        
        # 1. Identify critical defense needs
        # Check all my fortresses. If predicted state is Enemy, we need help.
        defense_requests = []
        for f in analysis.my_fortresses:
            pred_team, pred_troops = analysis.predict_state(f.id, 200)
            if pred_team != 1:
                # We are going to lose this!
                # How much do we need?
                # pred_troops is the enemy troops there.
                # We need to overcome that.
                needed = pred_troops # This is roughly damage needed
                defense_requests.append((f.id, needed))
                
        # 2. Identify upgrade opportunities
        upgrade_candidates = []
        for f in analysis.my_fortresses:
            if f.upgrade_timer == -1 and f.level < 5:
                cost = fortress_limit[f.level] // 2
                if f.troops >= cost:
                    # Check safety
                    # If we spend cost, do we survive?
                    # Simulate: remove cost, then predict.
                    # Hack: just check if current threat level is high enough
                    # Or check if neighbors are enemies.
                    
                    # Simple safety: If any neighbor is enemy, require higher buffer.
                    has_enemy_neighbor = any(analysis.fortresses[n].is_enemy() for n in f.neighbors)
                    
                    safe = True
                    if has_enemy_neighbor:
                        # If frontline, only upgrade if we are dominating
                        if f.troops < cost * 2:
                            safe = False
                    
                    # Also check if we are in the defense_requests list
                    if any(req[0] == f.id for req in defense_requests):
                        safe = False
                        
                    if safe:
                        upgrade_candidates.append(f.id)

        # 3. Identify expansion/attack targets
        # Targets: Neutral or Enemy neighbors of my fortresses
        attack_candidates = []
        for f in analysis.my_fortresses:
            # Can we send troops?
            sending_amount = f.troops // 2
            if sending_amount < 1: continue
            
            for n_id in f.neighbors:
                target = analysis.fortresses[n_id]
                if target.is_mine(): continue
                
                # Calculate effectiveness
                # Travel time
                dist_steps = get_travel_time(f.id, n_id, f.kind)
                
                # Predict target state at arrival
                pred_team, pred_troops = analysis.predict_state(n_id, dist_steps)
                
                # Damage we deal
                dmg = sending_amount * (0.65 if f.kind == 0 else 0.95)
                
                if pred_team != 1:
                    # It's enemy or neutral
                    # If dmg > pred_troops, we take it!
                    if dmg > pred_troops + 2: # +2 buffer
                        score = 100
                        if target.is_neutral():
                            score += 50 # Easy expansion
                        else:
                            score += 100 # Kill enemy
                            
                        # Distance penalty (prefer closer)
                        score -= dist_steps * 0.1
                        
                        attack_candidates.append((score, f.id, n_id))
                    else:
                        # We can't take it alone.
                        # But maybe we should soften it up?
                        # Only if we are overflowing
                        if f.troops >= f.cap() * 0.9:
                             attack_candidates.append((10, f.id, n_id))

        # 4. Balance / Reinforce
        # If we have a defense request, try to fulfill it
        reinforce_moves = []
        for req_id, needed in defense_requests:
            target = analysis.fortresses[req_id]
            for n_id in target.neighbors:
                neighbor = analysis.fortresses[n_id]
                if neighbor.is_mine():
                    # Can neighbor help?
                    sending = neighbor.troops // 2
                    if sending > 0:
                        reinforce_moves.append((neighbor.id, req_id))
        
        # Decision Logic
        
        # Priority 1: Upgrade (if safe) - Long term investment
        # But don't upgrade if we desperately need troops for defense?
        # We already checked safety.
        if upgrade_candidates:
            # Pick the one with highest level (get to lvl 5 fast) or lowest?
            # Lower level is cheaper. Higher level gives more production.
            # Let's pick random to avoid stuck
            return 2, upgrade_candidates[0], 0
            
        # Priority 2: Defend
        if reinforce_moves:
            # Pick best reinforce?
            src, dst = reinforce_moves[0]
            return 1, src, dst
            
        # Priority 3: Attack / Expand
        if attack_candidates:
            attack_candidates.sort(key=lambda x: x[0], reverse=True)
            _, src, dst = attack_candidates[0]
            return 1, src, dst
            
        # Priority 4: Forwarding (Balance)
        # If a node is full, send to a neighbor that is not full, preferably towards enemy
        for f in analysis.my_fortresses:
            if f.troops >= f.cap() * 0.8:
                # Find best neighbor
                best_n = -1
                best_score = -999
                
                for n_id in f.neighbors:
                    n = analysis.fortresses[n_id]
                    score = 0
                    if n.is_mine():
                        if n.troops < n.cap() * 0.5:
                            score += 50
                    else:
                        # Enemy/Neutral neighbor
                        # If we are full, attacking is better than wasting production
                        score += 20
                        
                    if score > best_score:
                        best_score = score
                        best_n = n_id
                
                if best_n != -1:
                    return 1, f.id, best_n
                    
        return 0, 0, 0
