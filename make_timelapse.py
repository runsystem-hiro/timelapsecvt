import subprocess
import logging
from pathlib import Path
from datetime import datetime
import shutil
import sys
import time
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm  # 進捗バー表示用
import re  # 正規表現サポート追加

# 設定モジュールをインポート
from timelapse_config import get_config

# 設定を読み込む
config = get_config()

# ログの設定
script_dir = Path(__file__).parent
logging.basicConfig(filename=script_dir / 'timelapse_creation.log', level=logging.INFO,
                   format='%(asctime)s %(levelname)s:%(message)s', encoding='utf-8')

def format_datetime_from_filename(filename):
    try:
        # ファイル名から日時情報を抽出
        dt = datetime.strptime(filename.stem, "%Y%m%d_%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M")  # 読みやすい書式
    except ValueError as e:
        logging.warning(f"ファイル名から日時を取得できませんでした: {filename}, エラー: {e}")
        return ""

def add_text_with_pil(input_image, output_image, text):
    """PILを使用して画像にテキストを追加する"""
    try:
        # 画像を開く
        img = Image.open(input_image)
        
        # 描画オブジェクトを作成
        draw = ImageDraw.Draw(img)
        
        # フォントを設定
        try:
            font = ImageFont.truetype(config["FONT_PATH"], 24)
        except OSError:
            # フォントが見つからない場合はデフォルトフォントを使用
            font = ImageFont.load_default()
            logging.warning(f"指定したフォントが見つからないため、デフォルトフォントを使用します: {config['FONT_PATH']}")
        
        # テキストサイズを取得 - PILのバージョンによって異なるメソッドを使用
        try:
            # PIL 9.0.0以降
            if hasattr(font, "getbbox"):
                bbox = font.getbbox(text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            # PIL 8.0.0以前
            elif hasattr(draw, "textsize"):
                text_width, text_height = draw.textsize(text, font=font)
            else:
                # 安全でシンプルな方法 - 適当な値を使用
                text_width, text_height = len(text) * 12, 24
        except Exception:
            # どのメソッドも失敗した場合
            text_width, text_height = len(text) * 12, 24
        
        # テキスト背景の描画
        margin = 5
        x = 10
        y = img.height - text_height - 10 - margin
        
        # 背景の半透明黒ボックス
        # 注: PIL 9.0以前は直接半透明を描画できないので、新しい画像を作成して合成
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        draw_overlay.rectangle(
            [(x - margin, y - margin), (x + text_width + margin, y + text_height + margin)],
            fill=(0, 0, 0, 128)
        )
        
        # RGBに変換して合成
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)
        
        # テキストの描画
        draw = ImageDraw.Draw(img)
        draw.text((x, y), text, font=font, fill=(255, 255, 255))
        
        # RGBに変換して保存
        img = img.convert('RGB')
        img.save(output_image, 'JPEG')
        
        return True
    except Exception as e:
        logging.error(f"PILによるテキスト描画中にエラーが発生しました: {e}")
        return False

def overlay_text_on_images(image_folder: Path, temp_folder: Path):
    # 一時フォルダを作成
    temp_folder.mkdir(parents=True, exist_ok=True)
    
    # JPGファイルを取得してソート
    jpg_files = sorted(image_folder.glob('*.jpg'))
    if not jpg_files:
        logging.warning("画像ファイルが見つかりませんでした。")
        raise FileNotFoundError(f"画像ファイルが存在しません: {image_folder}")

    print(f"画像処理を開始します: 合計 {len(jpg_files)} 枚の画像")
    
    # tqdmで進捗バーを表示
    for index, file in tqdm(enumerate(jpg_files), total=len(jpg_files), desc="画像処理中"):
        text = format_datetime_from_filename(file)
        output_file = temp_folder / f"frame_{index:06d}.jpg"
        
        # PILを使用してテキストを追加
        success = add_text_with_pil(file, output_file, text)
        
        if not success:
            logging.error(f"画像処理に失敗: {file}")
            print(f"\n画像処理に失敗しました: {file}")
            raise RuntimeError(f"画像の処理に失敗しました: {file}")
            
    print(f"画像処理が完了しました: {len(jpg_files)}枚の画像にテキストを合成")
    logging.info(f"{len(jpg_files)}個の画像にテキストを合成しました。")

class FFmpegProgressParser:
    """FFmpegの出力からリアルタイムで進捗を解析するクラス"""
    def __init__(self, total_frames):
        self.total_frames = total_frames
        self.current_frame = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        # 正規表現パターンを事前にコンパイル
        self.frame_pattern = re.compile(r'frame=\s*(\d+)')
        
    def update(self, line):
        if "frame=" in line:
            try:
                # 正規表現を使用して数字を抽出
                match = self.frame_pattern.search(line)
                if match:
                    self.current_frame = int(match.group(1))
                    
                    # 進捗率を計算
                    progress = self.current_frame / self.total_frames * 100
                    
                    # 現在の処理速度を計算（1秒ごとに更新）
                    current_time = time.time()
                    if current_time - self.last_update_time >= 1.0:
                        elapsed = current_time - self.start_time
                        fps = self.current_frame / elapsed if elapsed > 0 else 0
                        eta = (self.total_frames - self.current_frame) / fps if fps > 0 else 0
                        
                        # ターミナルの同じ行を更新するためにキャリッジリターンを使用
                        sys.stdout.write(f"\r動画作成中: {progress:.1f}% (フレーム {self.current_frame}/{self.total_frames}) FPS: {fps:.1f} 残り時間: {eta:.1f}秒    ")
                        sys.stdout.flush()
                        self.last_update_time = current_time
            except (ValueError, IndexError) as e:
                logging.debug(f"進捗解析エラー: {e}, 行: {line}")

def create_timelapse(temp_folder: Path, output_video: Path, fps: int = None):
    # FPSが指定されていない場合は設定から取得
    if fps is None:
        fps = config["FPS"]
        
    # 出力先のディレクトリが存在しない場合は作成
    output_video.parent.mkdir(parents=True, exist_ok=True)
    
    # すでにファイルが存在する場合は別名で保存
    if output_video.exists():
        base_name = output_video.stem
        extension = output_video.suffix
        counter = 1
        while output_video.exists():
            output_video = output_video.with_name(f"{base_name}_{counter}{extension}")
            counter += 1
        logging.info(f"既存ファイルを避けるため、出力ファイル名を変更しました: {output_video}")

    # 処理するフレーム数をカウント
    frame_files = list(temp_folder.glob('frame_*.jpg'))
    total_frames = len(frame_files)
    
    if total_frames == 0:
        logging.error("処理するフレームがありません。")
        raise FileNotFoundError("処理するフレームが見つかりません。")

    print(f"\n動画作成を開始します: 合計 {total_frames} フレーム")
    
    try:
        # ffmpegコマンドを準備（プログレス情報を有効化）
        cmd = [
            'ffmpeg',
            '-framerate', str(fps),
            '-i', str(temp_folder / 'frame_%06d.jpg'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-y',  # 既存ファイルを上書き
            str(output_video)
        ]
        
        # 進捗パーサーを初期化
        progress_parser = FFmpegProgressParser(total_frames)
        
        # サブプロセスを開始
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1  # ラインバッファリング
        )
        
        # FFmpegはほとんどの情報を標準エラー出力に書き込むため、
        # 標準エラー出力からリアルタイムに進捗情報を読み取る
        while process.poll() is None:
            stderr_line = process.stderr.readline()
            if stderr_line:
                progress_parser.update(stderr_line)
                
                # デバッグ用にログに出力
                if "error" in stderr_line.lower():
                    logging.error(f"FFmpeg出力: {stderr_line.strip()}")
        
        # 処理完了を待機
        return_code = process.wait()
        
        # 残りの出力を読み取り（エラーチェック用）
        remaining_output = process.stderr.read()
        if remaining_output and "error" in remaining_output.lower():
            logging.error(f"FFmpeg残りの出力: {remaining_output}")
        
        # エラーチェック
        if return_code != 0:
            logging.error(f"FFmpegがエラーコード {return_code} で終了しました")
            raise subprocess.CalledProcessError(return_code, cmd)
        
        # 処理が完了したことを表示
        sys.stdout.write("\r動画作成: 100% 完了しました!                                              \n")
        sys.stdout.flush()
        
        logging.info(f"動画を作成しました: {output_video}")
        
    except subprocess.CalledProcessError as e:
        logging.error(f"動画作成中にffmpegでエラーが発生しました: {e}")
        raise
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {e}")
        raise
        
    return output_video

def main():
    # 設定から値を取得
    image_folder = config["IMAGE_FOLDER"]
    temp_folder = config["TEMP_FOLDER"]
    
    # 出力ファイル名の構築
    output_video = config["OUTPUT_VIDEO_DIR"] / f'timelapse_{image_folder.name}.mp4'
    
    try:
        # PILがインストールされているか確認
        try:
            import PIL
            print(f"PIL/Pillowバージョン: {PIL.__version__}")
        except ImportError:
            print("エラー: PILライブラリがインストールされていません。'pip install Pillow' でインストールしてください。")
            return
        
        # FFmpegがインストールされているか確認
        try:
            process = subprocess.run(['ffmpeg', '-version'], 
                                   check=True, 
                                   capture_output=True, 
                                   text=True)
            ffmpeg_version = process.stdout.split('\n')[0]
            print(f"FFmpegバージョン: {ffmpeg_version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logging.error("FFmpegがインストールされていないか、PATHに設定されていません。")
            print("エラー: FFmpegがインストールされていないか、PATHに設定されていません。")
            return

        # 処理開始時刻を記録
        start_time = time.time()
        
        # 処理実行
        print(f"タイムラプス動画の作成を開始します: {image_folder}")
        overlay_text_on_images(image_folder, temp_folder)
        final_output = create_timelapse(temp_folder, output_video)
        
        # 総処理時間を計算
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(elapsed_time, 60)
        
        print(f"\nタイムラプス動画が作成されました: {final_output}")
        print(f"処理時間: {int(minutes)}分 {seconds:.1f}秒")
        
    except FileNotFoundError as e:
        print(f"ファイルが見つかりません: {e}")
    except subprocess.CalledProcessError as e:
        print(f"コマンド実行エラー: {e}")
        print(f"詳細: {e.stderr if hasattr(e, 'stderr') else '情報なし'}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        print("詳細はログを確認してください。")
    finally:
        # 一時フォルダが残っている場合のみ削除
        if temp_folder.exists():
            try:
                shutil.rmtree(temp_folder)
                logging.info(f"一時フォルダを削除しました: {temp_folder}")
            except PermissionError:
                logging.warning(f"一時フォルダの削除に失敗しました: {temp_folder}")
                print(f"警告: 一時フォルダの削除に失敗しました: {temp_folder}")

if __name__ == "__main__":
    main()