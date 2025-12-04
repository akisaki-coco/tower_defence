import pygame

from tcg.game import Game
from tcg.players.sample_random import RandomPlayer
from tcg.players.claude_player import ClaudePlayer
from tcg.players.machined_player import MachinedPlayer
from tcg.players.AI import AIPlayer

if __name__ == "__main__":
    # ClaudePlayer vs RandomPlayer で対戦
    print("===  AIPlayer(Blue) vs MachinedPlayer (Red) ===")

    # デフォルト: ウィンドウ表示あり
    Game(AIPlayer(), MachinedPlayer()).run()

    # ウィンドウ表示なし（高速実行）の場合:
    #Game(AIPlayer(), RandomPlayer(), window=False).run()

    pygame.quit()
