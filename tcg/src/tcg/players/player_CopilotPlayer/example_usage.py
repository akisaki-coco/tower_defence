"""
CopilotPlayer使用例

main.pyでCopilotPlayerを使用する例
"""

# このコードをsrc/main.pyに追加または置き換えて使用してください

from tcg.game import Game
from tcg.players.player_CopilotPlayer import CopilotPlayer
from tcg.players.sample_random import RandomPlayer
from tcg.players.claude_player import ClaudePlayer


def main():
    # 例1: CopilotPlayer vs RandomPlayer
    print("Game 1: CopilotPlayer vs RandomPlayer")
    Game(CopilotPlayer(), RandomPlayer()).run()
    
    # 例2: CopilotPlayer vs ClaudePlayer
    print("\nGame 2: CopilotPlayer vs ClaudePlayer")
    Game(CopilotPlayer(), ClaudePlayer()).run()
    
    # 例3: ウィンドウなしで高速実行（複数試合）
    print("\nRunning 10 games without window...")
    wins = 0
    for i in range(10):
        result = Game(CopilotPlayer(), RandomPlayer(), window=False).run()
        if result == "CopilotPlayer":
            wins += 1
        print(f"Game {i+1}/10 complete")
    
    print(f"\nCopilotPlayer won {wins}/10 games")


if __name__ == "__main__":
    main()
