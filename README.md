# タイムラプス動画作成ツール

このツールは、連続した画像ファイルからタイムラプス動画を作成します。画像には日時情報が透かしとして追加されます。

## 機能

- 連続した画像からタイムラプス動画を作成
- ファイル名から日時情報を取得し、画像に表示
- 半透明の背景付きテキストオーバーレイ
- 処理の進捗状況をリアルタイム表示
- 環境変数による設定のカスタマイズ

## 必要条件

- Python 3.6以上
- FFmpeg（PATHに追加されていること）
- 必要なPythonパッケージ:
  - Pillow (PIL)
  - tqdm
  - python-dotenv

## インストール方法

1. このリポジトリをクローンまたはダウンロードします
2. 必要なパッケージをインストールします:

    ```bash
    pip install -r requirements.txt
    ```

3. FFmpegをインストールして、PATHに追加します

## 設定方法

1. `.env.example` ファイルを `.env` にコピーします
2. `.env` ファイル内の設定を必要に応じて変更します:

```conf
# 画像が保存されているフォルダ
TIMELAPSE_IMAGE_FOLDER=C:\your\images\folder

# 一時的に使用するフォルダ（処理後に削除されます）
TIMELAPSE_TEMP_FOLDER=C:\your\temp\folder

# 出力先ディレクトリ
TIMELAPSE_OUTPUT_DIR=C:\your\output\folder

# 使用するフォントのパス
TIMELAPSE_FONT_PATH=C:/Windows/Fonts/your_font.ttf

# 作成する動画のFPS（フレームレート）
TIMELAPSE_FPS=24
```

## 使用方法

スクリプトを実行するだけです

```bash
python make_timelapse.py
```

スクリプトは以下の処理を実行します:

1. 設定された画像フォルダから連続画像を読み込み
2. 各画像にファイル名から抽出した日時情報を追加
3. FFmpegを使用してタイムラプス動画を生成
4. 処理が完了すると、出力先に動画ファイルが作成されます

## 注意事項

- 画像ファイル名は `YYYYMMDD_HHMMSS.jpg` の形式である必要があります
- 処理中に作成される一時ファイルは、処理完了後に自動的に削除されます
- エラーが発生した場合は、ログファイル `timelapse_creation.log` を確認してください
