from pathlib import Path
import subprocess

def main():
    # --- 設定 ---
    clip_folder = Path('clip')
    overlay_image = Path('img/layer.png')
    
    # レイヤー画像の判定。
    if not overlay_image.exists():
        print(f"編集をスキップします。")
        return

    # 動画ファイル取得
    video_files = sorted(list(clip_folder.glob('*.mp4')) + list(clip_folder.glob('*.mov')))

    # 各動画に画像を重ねる
    for video_path in video_files:
        # 一時的な出力パス作成
        temp_output_path = video_path.with_name(f"temp_{video_path.name}")
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-i', str(overlay_image),
            '-filter_complex', 'overlay=0:0',
            '-codec:a', 'copy',
            '-y',
            str(temp_output_path)
        ]
        try:
            # 編集開始
            print(f"{video_path.name} を編集中。")
            subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            # 上書き保存
            temp_output_path.replace(video_path)
        finally:
            # 一時ファイルの削除
            if temp_output_path.exists():
                temp_output_path.unlink()

    print("すべての動画の処理が完了しました。")

if __name__ == '__main__':
    main()
