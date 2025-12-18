"""
CopilotPlayer デモスクリプト

このファイルをsrc/main.pyの内容と置き換えるか、
または直接実行してCopilotPlayerをテストしてください。
"""

import pygame

from tcg.game import Game
from tcg.players.player_CopilotPlayer import CopilotPlayer
from tcg.players.sample_random import RandomPlayer
from tcg.players.claude_player import ClaudePlayer

if __name__ == "__main__":
    print("=" * 60)
    print("CopilotPlayer - 最強タワーディフェンスAI")
    print("=" * 60)
    
    # テスト1: CopilotPlayer vs RandomPlayer
    print("\nTest 1: CopilotPlayer (Blue) vs RandomPlayer (Red)")
    print("-" * 60)
    result1 = Game(CopilotPlayer(), RandomPlayer(), window=True).run()
    print(f"Winner: {result1}")
    
    # テスト2: CopilotPlayer vs ClaudePlayer
    print("\n\nTest 2: CopilotPlayer (Blue) vs ClaudePlayer (Red)")
    print("-" * 60)
    result2 = Game(CopilotPlayer(), ClaudePlayer(), window=True).run()
    print(f"Winner: {result2}")
    
    # 複数試合テスト（ウィンドウなし）
    print("\n\nRunning multiple games (no window)...")
    print("-" * 60)
    
    copilot_wins = 0
    total_games = 10
    
    for i in range(total_games):
        result = Game(CopilotPlayer(), RandomPlayer(), window=False).run()
        if result == "CopilotPlayer":
            copilot_wins += 1
        print(f"Game {i+1}/{total_games}: Winner = {result}")
    
    print("\n" + "=" * 60)
    print(f"Final Results: CopilotPlayer won {copilot_wins}/{total_games} games")
    print(f"Win Rate: {copilot_wins/total_games*100:.1f}%")
    print("=" * 60)
    
    pygame.quit()
