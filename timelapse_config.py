"""
タイムラプス作成用の設定ファイル
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# 設定のデフォルト値
DEFAULT_CONFIG = {
    "IMAGE_FOLDER": "./input_images",
    "TEMP_FOLDER": "./temp_labeled",
    "OUTPUT_VIDEO_DIR": "./output",
    "FONT_PATH": "./assets/fonts/arial.ttf",
    "FPS": 24
}

# 環境変数から設定を読み込み、デフォルト値を使用
def get_config():
    config = {
        "IMAGE_FOLDER": os.getenv("TIMELAPSE_IMAGE_FOLDER", DEFAULT_CONFIG["IMAGE_FOLDER"]),
        "TEMP_FOLDER": os.getenv("TIMELAPSE_TEMP_FOLDER", DEFAULT_CONFIG["TEMP_FOLDER"]),
        "OUTPUT_VIDEO_DIR": os.getenv("TIMELAPSE_OUTPUT_DIR", DEFAULT_CONFIG["OUTPUT_VIDEO_DIR"]),
        "FONT_PATH": os.getenv("TIMELAPSE_FONT_PATH", DEFAULT_CONFIG["FONT_PATH"]),
        "FPS": int(os.getenv("TIMELAPSE_FPS", DEFAULT_CONFIG["FPS"]))
    }
    
    # パスオブジェクトに変換
    config["IMAGE_FOLDER"] = Path(config["IMAGE_FOLDER"])
    config["TEMP_FOLDER"] = Path(config["TEMP_FOLDER"])
    config["OUTPUT_VIDEO_DIR"] = Path(config["OUTPUT_VIDEO_DIR"])
    
    return config