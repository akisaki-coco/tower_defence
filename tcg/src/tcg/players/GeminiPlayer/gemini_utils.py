import math
from tcg.config import A_fortress_set, pos_fortress, fortress_limit, fortress_cool

# Reconstruct full adjacency matrix (undirected)
ADJACENCY = [[0] * 12 for _ in range(12)]
for i in range(12):
    for j in range(12):
        if A_fortress_set[i][j] == 1:
            ADJACENCY[i][j] = 1
            ADJACENCY[j][i] = 1

# Calculate distances (Euclidean) and Travel Times
# Speed: Kind 0 = 1.5, Kind 1 = 1.0
# Distance is roughly 42 * vector_length? No, let's look at game.py
# In game.py:
# kind 0: pos += vector * 1.5
# kind 1: pos += vector * 1.0
# Arrival check: distance^2 <= 45^2
# Departure: random offset, but roughly from center.
# The vectors in A_coordinate are normalized (mostly).
# Actually, let's pre-calculate travel times in steps.
# Distance between nodes in pixels:
DISTANCES = [[float('inf')] * 12 for _ in range(12)]
for i in range(12):
    for j in range(12):
        if ADJACENCY[i][j]:
            x1, y1 = pos_fortress[i]
            x2, y2 = pos_fortress[j]
            dist = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
            DISTANCES[i][j] = dist

# Travel time in steps (approximate)
# We subtract 45 (radius) from distance? No, arrival is when within 45 pixels.
# But departure is from center. So travel distance is Dist - 45.
# Let's be conservative.
TRAVEL_TIMES = {} # (from, to, kind) -> steps
for i in range(12):
    for j in range(12):
        if ADJACENCY[i][j]:
            dist = DISTANCES[i][j]
            # Effective distance to travel to hit the radius
            # But wait, the check is (x-pos[0])**2... <= 45**2.
            # So we need to reach within 45 units of the center.
            # Start is at center.
            # So travel distance is dist - 45.
            eff_dist = max(0, dist - 45)
            
            # Kind 0 speed 1.5
            steps_k0 = int(math.ceil(eff_dist / 1.5))
            # Kind 1 speed 1.0
            steps_k1 = int(math.ceil(eff_dist / 1.0))
            
            TRAVEL_TIMES[(i, j, 0)] = steps_k0
            TRAVEL_TIMES[(i, j, 1)] = steps_k1

def get_travel_time(u, v, kind):
    return TRAVEL_TIMES.get((u, v, kind), 9999)

def get_neighbors(u):
    return [v for v in range(12) if ADJACENCY[u][v]]

def get_shortest_paths():
    # Floyd-Warshall for hop counts
    dist = [[999] * 12 for _ in range(12)]
    for i in range(12):
        dist[i][i] = 0
        for j in get_neighbors(i):
            dist[i][j] = 1
            
    for k in range(12):
        for i in range(12):
            for j in range(12):
                dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])
    return dist

HOP_DISTANCES = get_shortest_paths()

def get_hop_distance(u, v):
    return HOP_DISTANCES[u][v]
