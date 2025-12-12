#!/usr/bin/env python3
"""
簡単な動作確認スクリプト

CopilotPlayerが正しくインポートできるかをチェック
"""

import sys
import os

# パスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

def test_imports():
    """モジュールのインポートテスト"""
    print("Testing imports...")
    
    try:
        from tcg.players.CopilotPlayer import CopilotPlayer
        print("✓ CopilotPlayer imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import CopilotPlayer: {e}")
        return False
    
    try:
        from tcg.players.CopilotPlayer.evaluator import FortressEvaluator
        print("✓ FortressEvaluator imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import FortressEvaluator: {e}")
        return False
    
    try:
        from tcg.players.CopilotPlayer.strategy import StrategyEngine
        print("✓ StrategyEngine imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import StrategyEngine: {e}")
        return False
    
    try:
        from tcg.players.CopilotPlayer.optimizer import ActionOptimizer
        print("✓ ActionOptimizer imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import ActionOptimizer: {e}")
        return False
    
    try:
        from tcg.players.CopilotPlayer.tactics import TacticalPatterns
        print("✓ TacticalPatterns imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import TacticalPatterns: {e}")
        return False
    
    try:
        from tcg.players.CopilotPlayer.exploits import GameExploits
        print("✓ GameExploits imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import GameExploits: {e}")
        return False
    
    return True


def test_instantiation():
    """クラスのインスタンス化テスト"""
    print("\nTesting instantiation...")
    
    try:
        from tcg.players.CopilotPlayer import CopilotPlayer
        player = CopilotPlayer()
        print(f"✓ CopilotPlayer instantiated: {player.team_name()}")
        return True
    except Exception as e:
        print(f"✗ Failed to instantiate CopilotPlayer: {e}")
        return False


def test_basic_functionality():
    """基本機能のテスト"""
    print("\nTesting basic functionality...")
    
    try:
        from tcg.players.CopilotPlayer import CopilotPlayer
        
        player = CopilotPlayer()
        
        # ダミーの状態を作成
        dummy_state = [
            [1, 0, 1, 10, -1, [1, 3, 4]],
            [0, 0, 2, 20, -1, [0, 2, 4]],
            [2, 0, 1, 10, -1, [1, 4, 5]],
            [0, 0, 2, 20, -1, [0, 4, 6, 7]],
            [0, 1, 3, 30, -1, [0, 1, 2, 3, 5, 6, 7, 8]],
            [0, 0, 2, 20, -1, [2, 4, 7, 8]],
            [0, 0, 2, 20, -1, [3, 4, 7, 9]],
            [0, 1, 3, 30, -1, [3, 4, 5, 6, 8, 9, 10, 11]],
            [0, 0, 2, 20, -1, [4, 5, 7, 11]],
            [0, 0, 1, 10, -1, [6, 7, 10]],
            [1, 0, 2, 20, -1, [7, 9, 11]],
            [0, 0, 1, 10, -1, [7, 8, 10]],
        ]
        
        dummy_info = [1, dummy_state, [], [], False]
        
        # updateメソッドを呼び出し
        command, subject, to = player.update(dummy_info)
        
        print(f"✓ Update returned: command={command}, subject={subject}, to={to}")
        
        # 結果の検証
        if isinstance(command, int) and isinstance(subject, int) and isinstance(to, int):
            print("✓ Return values are correct type")
            return True
        else:
            print("✗ Return values have incorrect type")
            return False
            
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メインテスト"""
    print("=" * 60)
    print("CopilotPlayer - Quick Verification Test")
    print("=" * 60)
    
    results = []
    
    # インポートテスト
    results.append(("Import Test", test_imports()))
    
    # インスタンス化テスト
    results.append(("Instantiation Test", test_instantiation()))
    
    # 基本機能テスト
    results.append(("Basic Functionality Test", test_basic_functionality()))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "PASSED" if passed else "FAILED"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! CopilotPlayer is ready to use.")
        print("\nNext steps:")
        print("1. Run demo: uv run python -m tcg.players.CopilotPlayer.demo_main")
        print("2. Or edit src/main.py to use CopilotPlayer")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
