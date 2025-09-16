from pathlib import Path
import subprocess

def main():
    # --- 設定 ---
    CLIP_FOLDER = Path('clip')
    OUTPUT_VIDEO = Path('切り抜きまとめ.mp4')
    OUTPUT_TIMESTAMPS = Path('タイムスタンプ.txt')
    FILE_LIST_TEMP = Path('concat_list.txt') # ffmpeg用の一時ファイル

    # 動画ファイル取得
    video_files = sorted(list(CLIP_FOLDER.glob('*.mp4')) + list(CLIP_FOLDER.glob('*.mov')))
    if not video_files:
        print(f"'{CLIP_FOLDER}'内に動画ファイルがありません。")
        return
    print(f"{len(video_files)}件の動画ファイルを連結します。")

    # 連結、タイムスタンプ作成
    timestamps = []
    total_seconds = 0
    for i, video_path in enumerate(video_files):
        # タイムスタンプ作成
        seconds = int(round(total_seconds))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        timestamp = f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
        timestamps.append(f"{timestamp} {i + 1}")

        # 次のタイムスタンプ用に、現在の動画尺を取得
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
        duration_str = result.stdout.strip()
        duration = float(duration_str)

        # 秒数を合計に追加
        total_seconds += duration

    # タイムスタンプを出力
    OUTPUT_TIMESTAMPS.write_text('\n'.join(timestamps), encoding='utf-8')
    print("タイムスタンプを作成しました。")

    # 動画を連結
    # 一時ファイル作成
    concat_content = "\n".join([f"file '{path.as_posix()}'" for path in video_files])
    FILE_LIST_TEMP.write_text(concat_content, encoding='utf-8')
    
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(FILE_LIST_TEMP),
        '-c', 'copy',
        '-y',
        str(OUTPUT_VIDEO)
    ]
    try:
        # 動画を連結
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print(f"動画の連結が完了しました。")
    finally:
        # 一時ファイルの削除
        if FILE_LIST_TEMP.exists():
            FILE_LIST_TEMP.unlink()

if __name__ == '__main__':
    main()
