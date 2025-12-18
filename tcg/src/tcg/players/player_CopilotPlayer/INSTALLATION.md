# CopilotPlayer - インストールとテストガイド

## 📁 作成されたファイル

```
src/tcg/players/CopilotPlayer/
├── __init__.py          # パッケージ初期化
├── player.py            # メインAIクラス
├── evaluator.py         # 要塞評価システム
├── strategy.py          # 戦略決定エンジン
├── optimizer.py         # 行動最適化
├── tactics.py           # 高度な戦術パターン
├── exploits.py          # ゲームメカニクスの最適化
├── README.md            # 詳細ドキュメント
├── demo_main.py         # デモスクリプト
├── test_copilot.py      # テストスクリプト
├── example_usage.py     # 使用例
└── INSTALLATION.md      # このファイル
```

## 🚀 クイックスタート

### 方法1: デモスクリプトを実行

```bash
cd src
uv run python -m tcg.players.CopilotPlayer.demo_main
```

### 方法2: main.pyで使用

`src/main.py`を以下のように編集：

```python
import pygame
from tcg.game import Game
from tcg.players.CopilotPlayer import CopilotPlayer
from tcg.players.sample_random import RandomPlayer

if __name__ == "__main__":
    Game(CopilotPlayer(), RandomPlayer()).run()
    pygame.quit()
```

そして実行：

```bash
uv run python src/main.py
```

### 方法3: Pythonインタラクティブシェルで

```python
from tcg.game import Game
from tcg.players.CopilotPlayer import CopilotPlayer
from tcg.players.sample_random import RandomPlayer

# 1試合実行
Game(CopilotPlayer(), RandomPlayer()).run()

# ウィンドウなしで10試合実行
for i in range(10):
    result = Game(CopilotPlayer(), RandomPlayer(), window=False).run()
    print(f"Game {i+1}: {result}")
```

## 🎮 テスト方法

### 基本テスト

```bash
cd src/tcg/players/CopilotPlayer
uv run python test_copilot.py
```

### カスタムテスト

```python
from tcg.game import Game
from tcg.players.CopilotPlayer import CopilotPlayer
from tcg.players.claude_player import ClaudePlayer

# CopilotPlayer vs ClaudePlayer
Game(CopilotPlayer(), ClaudePlayer()).run()
```

## 📊 期待される性能

- **vs RandomPlayer**: 勝率 90%+ 期待
- **vs ClaudePlayer**: 勝率 70%+ 期待
- **vs 他のAI**: 高度な戦略により優位

## 🔧 トラブルシューティング

### インポートエラーが出る場合

```bash
# 仮想環境が正しくアクティベートされているか確認
uv sync

# Pythonパスを確認
cd src
python -c "import sys; print(sys.path)"
```

### ゲームが起動しない場合

```bash
# pygameがインストールされているか確認
uv pip list | grep pygame

# 再インストール
uv sync --force
```

## 🎯 CopilotPlayerの特徴

### 1. 多次元要塞評価
- グラフ中心性（次数、近接）
- 戦術的価値（前線、孤立度）
- 経済的価値（生産効率）
- 軍事的価値（戦力）

### 2. 高度な戦略
- **序盤**: 中立要塞の高速制圧
- **中盤**: 経済成長と軍事拡大
- **終盤**: 総力戦、決定的攻撃

### 3. 戦術パターン
- 挟撃攻撃の検出
- 突破機会の特定
- チョークポイント制圧
- 包囲回避

### 4. ゲームメカニクス最適化
- 生産タイミングの活用
- オーバーフロー回避
- 投資回収時間の計算
- 正確な戦闘予測

## 📈 パフォーマンスチューニング

### パラメータ調整

`player.py`内の定数を調整：

```python
class CopilotPlayer(Controller):
    # ゲームフェーズの閾値
    EARLY_GAME_THRESHOLD = 3000  # 序盤の終了
    MID_GAME_THRESHOLD = 15000   # 中盤の終了
```

### 戦略の重み調整

`strategy.py`と`evaluator.py`内の各種スコアリング係数を調整して、
AIの行動を微調整できます。

## 🎓 アルゴリズムの詳細

### 計算量
- **評価**: O(n²) - 要塞数が12なので高速
- **戦略生成**: O(n³) - 全ての要塞ペアを考慮
- **最適化**: O(m log m) - アクション数でソート

### 主要アルゴリズム
- **BFS**: 最短パス探索
- **貪欲法**: 各ターンで最適行動
- **動的評価**: リアルタイム戦況分析
- **ヒューリスティック探索**: 評価関数ベース

## 💡 使用上のヒント

1. **序盤の重要性**: 中立要塞の制圧が勝敗を分ける
2. **中央制圧**: 要塞4と7は最重要ハブ
3. **経済vs軍事**: 状況に応じたバランス
4. **防御の重要性**: 攻撃だけでなく防御も考慮

## 📝 ログとデバッグ

デバッグモードを有効にする場合（将来の拡張）：

```python
copilot = CopilotPlayer()
copilot.debug = True  # デバッグ出力を有効化
```

## 🤝 貢献とカスタマイズ

独自の戦略を追加する場合：

1. `strategy.py`に新しいメソッドを追加
2. `decide_actions()`で呼び出し
3. テストして調整

## 📚 参考資料

- [CLAUDE.md](../../../../CLAUDE.md) - ゲーム仕様
- [README.md](./README.md) - CopilotPlayerの詳細
- [ゲームルール](../../../../README.md)

## ⚠️ 既知の制限

- 完全な先読みは実装していない（計算コストが高いため）
- 確率的要素は考慮していない（部隊移動の正確なタイミング）
- マルチプレイヤー（3人以上）には対応していない

## 🎉 成功のサイン

以下が表示されればCopilotPlayerは正しく動作しています：

```
=== CopilotPlayer (Blue) vs RandomPlayer (Red) ===
... ゲーム実行 ...
Winner: CopilotPlayer
```

楽しんでください！🚀
