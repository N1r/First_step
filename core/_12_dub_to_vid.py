import platform
import subprocess
import os
import sys
import time

import cv2
import numpy as np
from rich.console import Console
from rich import print as rprint

from core._1_ytdlp import find_video_files
from core.asr_backend.audio_preprocess import normalize_audio_volume
from core.utils import *
from core.utils.models import *

console = Console()

# ============= 文件路径配置 =============
OUTPUT_DIR = "output"
DUB_VIDEO = f"{OUTPUT_DIR}/output_dub.mp4"
FINAL_VIDEO = f"{OUTPUT_DIR}/output_dub_final.mp4"
DUB_SUB_FILE = f'{OUTPUT_DIR}/dub.srt'
DUB_AUDIO = f'{OUTPUT_DIR}/dub.mp3'

# Logo 路径 (请确保文件存在，或者修改为你实际的路径)
# 注意：如果路径中包含反斜杠，请使用 r"" 或双反斜杠
LOGO_PATH = r"core/logo1.png"  # 建议使用相对路径，或者改为你提供的绝对路径

# 片头片尾配置
OPEN_CLIP = "video/open.mp4"
END_CLIP = "video/end.mp4"

# ============= 字幕样式配置 (来自代码2) =============
# 字体配置
FONT_NAME = 'Arial'
TRANS_FONT_NAME = 'Source Han Sans SC'
if platform.system() == 'Linux':
    FONT_NAME = 'NotoSansCJK-Regular'
    TRANS_FONT_NAME = 'NotoSansCJK-Regular'
elif platform.system() == 'Darwin':
    FONT_NAME = 'Arial Unicode MS'
    TRANS_FONT_NAME = 'Arial Unicode MS'

# 字幕大小与位置
TRANS_FONT_SIZE = 26
TRANS_MARGIN_V = 35

# 颜色配置
TRANS_FONT_COLOR = '&H00FFFF'    # 青色文字
TRANS_OUTLINE_COLOR = '&H00202020' # 黑色描边
TRANS_OUTLINE_WIDTH = 25.0        # 描边宽度
TRANS_BACK_COLOR = '&H66000000'  # 深灰色背景，约 40% 透明度

def build_subtitle_style(font_size, font_name, font_color, outline_color, outline_width, back_color, margin_v):
    """构建字幕样式字符串"""
    return (
        f"FontSize={font_size},FontName={font_name},"
        f"PrimaryColour={font_color},OutlineColour={outline_color},"
        f"OutlineWidth={outline_width},BackColour={back_color},"
        f"BorderStyle=3,Alignment=2,MarginV={margin_v},"
        f"Shadow=1,MarginL=50,MarginR=50"
    )

def merge_video_audio():
    """Merge video and audio, add subtitles/logo, and concatenate clips"""
    VIDEO_FILE = find_video_files()
    background_file = _BACKGROUND_AUDIO_FILE
    
    # 1. 处理不烧录字幕的情况 (生成黑屏占位符)
    if not load_key("burn_subtitles"):
        rprint("[bold yellow]Warning: A 0-second black video will be generated as a placeholder as subtitles are not burned in.[/bold yellow]")
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(DUB_VIDEO, fourcc, 1, (1920, 1080))
        out.write(frame)
        out.release()
        rprint("[bold green]Placeholder video has been generated.[/bold green]")
        return

    # 2. 准备音频和视频信息
    # Normalize dub audio
    normalized_dub_audio = 'output/normalized_dub.wav'
    normalize_audio_volume(DUB_AUDIO, normalized_dub_audio)
    
    video = cv2.VideoCapture(VIDEO_FILE)
    TARGET_WIDTH = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    TARGET_HEIGHT = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video.release()
    rprint(f"[bold green]Video resolution: {TARGET_WIDTH}x{TARGET_HEIGHT}[/bold green]")
    
    # 3. 构建字幕样式
    # 这里使用的是配音字幕(DUB_SUB_FILE)，应用第二个代码中的样式
    sub_style = build_subtitle_style(
        TRANS_FONT_SIZE, TRANS_FONT_NAME, TRANS_FONT_COLOR,
        TRANS_OUTLINE_COLOR, TRANS_OUTLINE_WIDTH, TRANS_BACK_COLOR, TRANS_MARGIN_V
    )
    
    # 4. 构建 FFmpeg Filter Complex
    # 输入顺序: [0]原视频, [1]背景音, [2]配音, [3]Logo图片
    
    # 检查 Logo 是否存在
    has_logo = os.path.exists(LOGO_PATH)
    if not has_logo:
        rprint(f"[bold yellow]Warning: Logo file not found at {LOGO_PATH}. Skipping logo.[/bold yellow]")

    # 视频滤镜链
    # a. 缩放和填充视频
    video_filter = (
        f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2[v_scaled];"
    )
    
    # b. 添加字幕
    video_filter += (
        f"[v_scaled]subtitles={DUB_SUB_FILE}:force_style='{sub_style}'[v_sub];"
    )
    
    # c. 添加 Logo (如果存在)
    if has_logo:
        # Logo 缩放到宽度 300，覆盖在右上角 (W-w-20:20)
        video_filter += f"[3:v]scale=300:-1[logo];[v_sub][logo]overlay=W-w-20:20[v_out]"
    else:
        video_filter += f"[v_sub]copy[v_out]" # 如果没logo，直接把字幕后的视频作为输出

    # 音频滤镜链 (混合背景音和配音)
    audio_filter = f"[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=3[a_out]"

    # 组合完整滤镜
    full_filter_complex = video_filter + ";" + audio_filter

    # 5. 构建 FFmpeg 命令
    cmd = [
        'ffmpeg', '-y', 
        '-i', VIDEO_FILE,           # Input 0: Video
        '-i', background_file,      # Input 1: Bg Audio
        '-i', normalized_dub_audio  # Input 2: Dub Audio
    ]
    
    if has_logo:
        cmd.extend(['-i', LOGO_PATH]) # Input 3: Logo

    cmd.extend(['-filter_complex', full_filter_complex])

    if load_key("ffmpeg_gpu"):
        rprint("[bold green]Using GPU acceleration...[/bold green]")
        # 注意: map 这里要对应上面滤镜的输出标签 [v_out] 和 [a_out]
        cmd.extend(['-map', '[v_out]', '-map', '[a_out]', '-c:v', 'h264_nvenc'])
    else:
        cmd.extend(['-map', '[v_out]', '-map', '[a_out]', '-c:v', 'libx264'])
    
    cmd.extend(['-c:a', 'aac', '-b:a', '192k', DUB_VIDEO])
    
    rprint("🎬 Start merging video, audio, subtitles and logo...")
    subprocess.run(cmd, check=True)
    rprint(f"[bold green]Video and audio successfully merged into {DUB_VIDEO}[/bold green]")

    # ============= 6. 拼接片头 + 主片 + 片尾 (新增逻辑) =============
    
    # 检查片头片尾文件是否存在
    files_to_concat = []
    #if os.path.exists(OPEN_CLIP): files_to_concat.append(OPEN_CLIP)
    files_to_concat.append(DUB_VIDEO)
    if os.path.exists(END_CLIP): files_to_concat.append(END_CLIP)

    if len(files_to_concat) > 1:
        rprint("🎬 Start concatenating clips (Open + Main + End)...")
        concat_list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
        temp_files = []

        try:
            # 统一转码所有部分以确保拼接顺畅
            for i, input_file in enumerate(files_to_concat):
                temp_file = os.path.join(OUTPUT_DIR, f"temp_{i}.mp4")
                temp_files.append(temp_file)
                
                # 转码参数: 统一分辨率、帧率、采样率
                transcode_cmd = [
                    "ffmpeg", "-y", "-i", input_file,
                    "-c:v", "h264_nvenc" if load_key("ffmpeg_gpu") else "libx264",
                    "-pix_fmt", "yuv420p",
                    "-vf", f"scale={TARGET_WIDTH}:{TARGET_HEIGHT},setsar=1:1",
                    "-r", "30", "-g", "60",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                    temp_file
                ]
                # 隐藏详细日志，除非出错
                subprocess.run(transcode_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                rprint(f"  Processed clip {i+1}/{len(files_to_concat)}: {input_file}")

            # 写入拼接列表
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for tf in temp_files:
                    f.write(f"file '{os.path.abspath(tf)}'\n")

            # 执行拼接
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",
                FINAL_VIDEO
            ]
            subprocess.run(concat_cmd, check=True)
            rprint(f"\n✅ All done! Final video: {FINAL_VIDEO}")

        except subprocess.CalledProcessError as e:
            rprint(f"[bold red]❌ Concatenation failed: {e}[/bold red]")
        finally:
            # 清理临时文件
            if os.path.exists(concat_list_path): os.remove(concat_list_path)
            for temp_file in temp_files:
                if os.path.exists(temp_file): os.remove(temp_file)
    else:
        rprint(f"[bold green]No open/end clips found. Output is {DUB_VIDEO}[/bold green]")

if __name__ == '__main__':
    merge_video_audio()