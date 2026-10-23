import os, re, json, shutil, subprocess, tempfile, asyncio
from pathlib import Path
import gradio as gr
from PIL import Image, ImageDraw, ImageFont
import edge_tts

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
W, H = 1280, 720

def get_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/msyh.ttc"
    ]
    for p in candidates:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

def wrap_text(text, max_chars=24):
    result = []
    for para in text.splitlines():
        while len(para) > max_chars:
            result.append(para[:max_chars])
            para = para[max_chars:]
        if para: result.append(para)
    return result

def make_scene_image(title, narration, index, total, style, outpath):
    # Built-in, no-key visual fallback: designed cinematic title-card scenes.
    # Plug in an image-generation provider later for true AI-generated imagery.
    img = Image.new("RGB", (W, H), (16, 24, 42))
    px = img.load()
    for y in range(H):
        for x in range(W):
            t = y / H
            if style == "anime":
                c1, c2 = (27, 20, 70), (12, 120, 150)
            else:
                c1, c2 = (30, 34, 42), (115, 73, 53)
            px[x,y] = tuple(int(c1[k]*(1-t)+c2[k]*t) for k in range(3))
    d = ImageDraw.Draw(img, "RGBA")
    # Abstract cinematic shapes, horizon, lights
    for j in range(10):
        x = (index*113 + j*157) % W
        y = 90 + (j*61) % 390
        r = 18 + (j % 4)*12
        d.ellipse((x-r,y-r,x+r,y+r), fill=(100,210,255,35 if style=="anime" else 18))
    d.rectangle((0, H-150, W, H), fill=(0,0,0,125))
    d.text((65, 45), f"AI VIDEO STUDIO  •  SCENE {index:02d}/{total:02d}", font=get_font(24, True), fill=(255,255,255,210))
    d.rounded_rectangle((62, 135, W-62, 410), radius=28, fill=(0,0,0,80), outline=(255,255,255,80), width=2)
    title_lines = wrap_text(title, 18)
    y = 170
    for line in title_lines[:3]:
        d.text((95,y), line, font=get_font(48, True), fill=(255,255,255,255), stroke_width=1, stroke_fill=(0,0,0,180))
        y += 66
    narr_lines = wrap_text(narration, 32)
    y = H-125
    for line in narr_lines[:2]:
        d.text((65,y), line, font=get_font(25), fill=(255,255,255,255), stroke_width=1, stroke_fill=(0,0,0,180))
        y += 36
    img.save(outpath, quality=92)

def split_story(topic, minutes, style):
    # Works without an LLM key: deterministic storyboard. Connect an LLM in a future version.
    total_seconds = int(minutes * 60)
    count = max(6, min(36, round(total_seconds / 10)))
    beats = [
        ("故事开场", f"关于{topic}的故事，从一个不寻常的瞬间开始。"),
        ("新的发现", f"主角在探索{topic}时，发现了一个意想不到的线索。"),
        ("遇到挑战", "新的困难出现了，原本的计划不得不改变。"),
        ("寻找答案", "主角整理线索，尝试从不同角度理解眼前的问题。"),
        ("关键转折", "一个关键细节改变了局面，也让真相逐渐清晰。"),
        ("团队合作", "大家分工协作，把复杂的问题拆解成可以完成的小任务。"),
        ("解决难题", "经过不断尝试，主角终于找到了可行的解决办法。"),
        ("新的可能", "这次经历带来了新的思考，也打开了更多可能。"),
        ("温暖收尾", "故事暂时告一段落，但探索和成长仍会继续。"),
    ]
    scenes=[]
    for i in range(count):
        beat = beats[i % len(beats)]
        title = beat[0] if i < len(beats) else f"{beat[0]} · {i+1}"
        narration = beat[1]
        if i >= len(beats):
            narration += f"在第{i+1}个片段中，故事继续围绕{topic}展开。"
        scenes.append({"title": title, "narration": narration})
    return scenes, total_seconds

async def make_tts(text, path, voice):
    communicate = edge_tts.Communicate(text=text, voice=voice, rate="+0%")
    await communicate.save(str(path))

def run_ffmpeg(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError("FFmpeg 执行失败：\n" + p.stderr[-2500:])

def generate(topic, style, minutes, voice, progress=gr.Progress()):
    if not topic.strip():
        raise gr.Error("请先输入视频主题。")
    if shutil.which("ffmpeg") is None:
        raise gr.Error("当前环境没有 FFmpeg。请使用本项目的 Dockerfile 或在环境中安装 FFmpeg。")
    job = OUT / re.sub(r"[^a-zA-Z0-9_-]+", "-", topic.strip())[:30]
    if job.exists(): shutil.rmtree(job)
    job.mkdir(parents=True)
    style_name = "anime" if style == "动漫" else "real"
    scenes, total_seconds = split_story(topic.strip(), minutes, style_name)
    duration = total_seconds / len(scenes)
    (job / "storyboard.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    (job / "captions.srt").write_text("", encoding="utf-8")
    parts=[]
    srt=[]
    elapsed=0.0
    for i, sc in enumerate(scenes, 1):
        progress((i-1)/len(scenes), desc=f"生成分镜 {i}/{len(scenes)}")
        image_path = job / f"scene_{i:02d}.jpg"
        audio_path = job / f"voice_{i:02d}.mp3"
        video_path = job / f"part_{i:02d}.mp4"
        make_scene_image(sc["title"], sc["narration"], i, len(scenes), style_name, image_path)
        try:
            asyncio.run(make_tts(sc["narration"], audio_path, voice))
        except Exception as e:
            raise gr.Error(f"中文配音失败。请确认运行环境可以访问网络。详细信息：{e}")
        # Burn caption into the scene image. Also create SRT for external editing.
        im=Image.open(image_path).convert("RGB")
        draw=ImageDraw.Draw(im, "RGBA")
        draw.rectangle((45, H-92, W-45, H-28), fill=(0,0,0,175))
        cap = sc["narration"][:42]
        draw.text((65,H-82), cap, font=get_font(23), fill=(255,255,255,255), stroke_width=1, stroke_fill=(0,0,0,255))
        im.save(image_path, quality=92)
        start_ms=int(elapsed*1000); end_ms=int((elapsed+duration)*1000)
        def ts(ms):
            h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
            return f"{h:02}:{m:02}:{s:02},{ms:03}"
        srt.append(f"{i}\n{ts(start_ms)} --> {ts(end_ms)}\n{cap}\n")
        run_ffmpeg(["ffmpeg","-y","-loop","1","-framerate","24","-i",str(image_path),"-i",str(audio_path),
                    "-vf",f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                    "-af",f"apad=pad_dur={duration},atrim=duration={duration}",
                    "-t",str(duration),"-r","24","-c:v","libx264","-preset","ultrafast","-c:a","aac","-b:a","128k",
                    "-shortest",str(video_path)])
        parts.append(video_path)
        elapsed += duration
    (job / "captions.srt").write_text("\n".join(srt), encoding="utf-8")
    concat = job / "concat.txt"
    concat.write_text("\n".join("file '"+str(p).replace("'","'\\''")+"'" for p in parts), encoding="utf-8")
    final = job / "final_video.mp4"
    run_ffmpeg(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(final)])
    progress(1, desc="完成")
    return str(final), str(job / "storyboard.json"), str(job / "captions.srt")

with gr.Blocks(title="AI 视频工坊", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎬 AI 视频工坊\n输入主题，自动生成分镜、中文配音、字幕并合成 MP4。\n\n**当前免费版说明：**内置的是风格化场景卡片和镜头分段，不是 AI 生成的真实人物动态画面。")
    topic = gr.Textbox(label="视频主题", placeholder="例如：未来城市里，两个 AI 助手合作解决危机", lines=2)
    with gr.Row():
        style = gr.Radio(["动漫","真人电影风格"], value="动漫", label="画风")
        minutes = gr.Slider(1, 3, value=3, step=1, label="视频时长（分钟）")
    voice = gr.Dropdown(
        choices=[
            ("晓晓 · 普通话女声","zh-CN-XiaoxiaoNeural"),
            ("云希 · 普通话男声","zh-CN-YunxiNeural"),
            ("晓伊 · 普通话女声","zh-CN-XiaoyiNeural"),
        ],
        value="zh-CN-XiaoxiaoNeural", label="中文配音"
    )
    go = gr.Button("生成视频", variant="primary")
    video = gr.Video(label="生成的 MP4")
    storyboard = gr.File(label="分镜 JSON")
    subtitles = gr.File(label="字幕 SRT")
    go.click(generate, inputs=[topic, style, minutes, voice], outputs=[video, storyboard, subtitles])
    gr.Markdown("### 后续升级\n- 接入大语言模型：自动创作更丰富的剧情和分镜。\n- 接入图像生成 API：为每个镜头生成真实独立画面。\n- 接入文生视频/图生视频 API：生成真正动态的角色与场景。\n\n请勿把 API 密钥写进代码仓库；部署时使用平台的 Secrets/环境变量。")

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT","7860")))
