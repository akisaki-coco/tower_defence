import pygame

from tcg.game import Game
from tcg.players.sample_random import RandomPlayer
from tcg.players.claude_player import ClaudePlayer
from tcg.players.player_CopilotPlayer import CopilotPlayer
from tcg.players.player_GPTPlayer.player import GPTPlayer
from tcg.players.machined_player import MachinedPlayer
from tcg.players.machined_player_legacy import MachinedPlayerLegacy
from tcg.players.AI import AIPlayer
from tcg.players.player_kai2.player import KaiPlayer
from tcg.players.player_GeminiPlayer import GeminiPlayer
from tcg.players.player_GeminiPlayer.player_2 import GeminiPlayer2

if __name__ == "__main__":
    # AIPlayer vs GeminiPlayer で対戦
    print("===  GeminiPlayer(Blue) vs GPTPlayer (Red) ===")

    # デフォルト: ウィンドウ表示あり
    Game(MachinedPlayer(), AIPlayer()).run()

    # ウィンドウ表示なし（高速実行）の場合:
    #Game(AIPlayer(), RandomPlayer(), window=False).run()

    pygame.quit()
