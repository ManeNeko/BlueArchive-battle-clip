from pathlib import Path
import subprocess
import mimetypes
import cv2
import numpy as np

# --- 設定 ---
CLIP_DIR = Path('clip')
MOVIES_DIR = Path('movies')
REF_IMG_PATH_0 = Path('img/0.png')
REF_IMG_PATH_1 = Path('img/1.png')
FRAME_SKIP_SECONDS = 2 # n秒置きにフレームをチェック
THRESHOLD = 0.99  # 一致判定の閾値

# トリミング
def img_trim(img, t=0, b=0.03, l=0.80, r=1.0):
    h, w = img.shape[0:2]
    t = int(h * t)
    b = int(h * b)
    l = int(w * l)
    r = int(w * r)
    return img[t:b, l:r]

# 2つの画像を比較し、類似度を返す。
def match(img1, img2):
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2
    mae = np.mean(np.abs(gray1.astype(np.float32) - gray2.astype(np.float32)))
    similarity = 1.0 - (mae / 255.0)
    return similarity

# 指定フレームを読み込み、トリミングして返す。
def frame_crop(mov, frame):
    mov.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ret, frame = mov.read()
    if not ret:
        return None
    return img_trim(frame)

# 開始/終了フレームを探索：directionには「1 or -1」を入れる。
def lookup(mov, frame, direction, frame_skip, img, frame_total):
    frame_skip = frame_skip * direction
    # 範囲絞込み。
    while (0 < frame < frame_total) and (abs(frame_skip) >1):
        # フレームを取得し判定
        frame_img = frame_crop(mov, frame)
        is_match  = match(frame_img, img)
        if is_match >= THRESHOLD:
            # マッチしたら、スキップを半分にして、フレームを戻し、再度ループ。
            frame_skip -= frame_skip // 2
            frame -= frame_skip
        else:
            # ロード画面とマッチするまでスキップ。
            frame = frame + frame_skip
            frame = min(frame_total,max(0,frame))
    # 範囲外ならそのまま返す。
    if (frame <= 1) or (frame >=frame_total):
            return min(frame_total,max(0,frame))
    # なんとなく10フレ戻した後、1フレ単位で確認し厳密な境界を調べる。
    frame = frame - (10 * direction)
    for _ in range(100):
        # 上と同じ処理。
        frame_img = frame_crop(mov, frame)
        is_match  = match(frame_img, img)
        if is_match >= THRESHOLD:
            return frame
        frame += direction
    return min(frame_total,max(0,frame))

# カット編集
def export_clips(video_path, frames, fps):
    # 始点,終点のフレームを渡し、切り抜き。
    for i, (s_frame, e_frame) in enumerate(frames):
        count = len(list(CLIP_DIR.glob('*'))) + 1
        name  = CLIP_DIR / f"{count:04d}.mp4"
        s = s_frame / fps
        e = e_frame / fps
        
        print(f" ・{name} を作成中。")
        cmd = [
            "ffmpeg", "-i", str(video_path),
            "-ss", str(s), "-to", str(e),
            "-y", str(name), "-loglevel", "error"
        ]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"Error creating clip {name}.")


# 切り抜きフレームを探索
def process_video(video_path, img_battle, img_load):
    frames = []
    mov = cv2.VideoCapture(str(video_path))

    # 動画情報
    fps = mov.get(cv2.CAP_PROP_FPS)
    frame_total = int(mov.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_skip  = int(FRAME_SKIP_SECONDS * fps)

    print(f"{video_path}")

    img = 0
    clip = 0
    frame = 0
    print("切り抜き範囲を探索中...")
    while frame < frame_total:
        # フレームを取得し判定
        frame_img = frame_crop(mov, frame)
        if img == 0:
            is_match = match(frame_img, img_battle)
        else:
            is_match = match(frame_img, img_load)
        
        # 厳密な境界を調べる
        if is_match >= THRESHOLD:
            if img == 0:
                s_frame = lookup(mov, max(0,frame-1), -1, frame_skip, img_load , frame_total) +1
                frames.append([s_frame,0])
                #print("s ",s_frame)
                img = 1
            else:
                e_frame = lookup(mov, frame -frame_skip, +1, frame_skip, img_load , frame_total) -1
                frames[-1][1] = e_frame
                #print("e ",e_frame)
                clip += 1
                print(f" ・{clip}個目：s={s_frame},e={e_frame}")
                frame = e_frame + 1
                img = 0
        else:
            frame += frame_skip
    if frames and frames[-1][1] == 0:
        frames[-1][1] = frame_total
        print(f" ・{clip+1}個目：s={frames[-1][0]},e={frame_total}")
    mov.release()
    return [fps,frames]

# --- 実行用 ---
def main():
    CLIP_DIR.mkdir(exist_ok=True)
    
    # 比較用画像
    img_battle = img_trim(cv2.imread(str(REF_IMG_PATH_0)))
    img_load   = img_trim(cv2.imread(str(REF_IMG_PATH_1)))

    # 動画取得
    movies = []
    for file in MOVIES_DIR.glob('*'):
        mime, _ = mimetypes.guess_type(file)
        if mime and mime.startswith("video"):
            movies.append(file)
            
    print(f"{len(movies)}件の動画ファイルを処理します。")
    # クリップ作成
    for path in movies:
        print("---")
        fps ,frames = process_video(path, img_battle, img_load)
        if not frames:
            break
        print(f"{len(frames)}個のクリップを作成します！")
        export_clips(path, frames, fps)

if __name__ == '__main__':
    main()
