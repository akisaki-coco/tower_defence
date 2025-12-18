"""
Test CopilotPlayer

CopilotPlayerのテストとデモンストレーション
"""

import sys
import os

# パスの追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from tcg.game import Game
from tcg.players.player_CopilotPlayer import CopilotPlayer
from tcg.players.sample_random import RandomPlayer
from tcg.players.claude_player import ClaudePlayer


def test_vs_random(num_games: int = 5, window: bool = True):
    """RandomPlayerに対してテスト"""
    print(f"Testing CopilotPlayer vs RandomPlayer ({num_games} games)")
    print("=" * 50)
    
    wins = 0
    losses = 0
    
    for i in range(num_games):
        print(f"\nGame {i + 1}/{num_games}")
        game = Game(CopilotPlayer(), RandomPlayer(), window=window)
        result = game.run()
        
        if result == CopilotPlayer().team_name():
            wins += 1
        else:
            losses += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {wins} wins, {losses} losses")
    print(f"Win rate: {wins / num_games * 100:.1f}%")


def test_vs_claude(num_games: int = 5, window: bool = True):
    """ClaudePlayerに対してテスト"""
    print(f"\nTesting CopilotPlayer vs ClaudePlayer ({num_games} games)")
    print("=" * 50)
    
    wins = 0
    losses = 0
    
    for i in range(num_games):
        print(f"\nGame {i + 1}/{num_games}")
        game = Game(CopilotPlayer(), ClaudePlayer(), window=window)
        result = game.run()
        
        if result == CopilotPlayer().team_name():
            wins += 1
        else:
            losses += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {wins} wins, {losses} losses")
    print(f"Win rate: {wins / num_games * 100:.1f}%")


def single_game_demo():
    """1ゲームのデモ（ウィンドウ表示）"""
    print("CopilotPlayer Demo Game")
    print("=" * 50)
    
    game = Game(CopilotPlayer(), ClaudePlayer(), window=True)
    result = game.run()
    
    print(f"\nWinner: {result}")


if __name__ == "__main__":
    # 単一ゲームのデモ
    single_game_demo()
    
    # 複数ゲームのテスト（ウィンドウなしで高速実行）
    # test_vs_random(num_games=10, window=False)
    # test_vs_claude(num_games=10, window=False)
