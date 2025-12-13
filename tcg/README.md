12/13：加筆修正ずみ

Territory Conquering Game
=========================
この実験では、陣取りゲームのAIプレイヤーを開発します。 

## 実験の準備

1. まずuvをインストールします。[uv](https://docs.astral.sh/uv/getting-started/installation/)を参考にしましょう。

2. リポジトリをクローンし、必要なライブラリをインストール:
```bash
git clone -b latest https://github.com/akisaki-coco/tower_defence.git
cd tcg
uv sync
```

3. ゲームの実行:
```bash
uv run python src/main.py
```

## 実験内容

src/tcg/players以下のファイルを参考にして独自のAIプレイヤーを実装してください。
