import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import tempfile
import os

st.set_page_config(page_title="专属 AI 助手", page_icon="✨")

today_date = datetime.now().strftime("%Y年%m月%d日")
persona = f"""
你现在是朝阳为他女朋友专属定制的贴心AI助手。
请用温柔、友好的语气回答她的问题。
如果她问起是谁创造了你，你要回答是朝阳专门搭建的。
请牢记：今天的真实日期是 {today_date}。
"""

# 1. 初始化各类状态变量
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()
if "processed_audios" not in st.session_state:
    st.session_state.processed_audios = set()
if "current_model" not in st.session_state:
    st.session_state.current_model = "models/gemini-3-flash-preview"
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.client.chats.create(
        model=st.session_state.current_model,
        config=types.GenerateContentConfig(system_instruction=persona)
    )

# --- 🚀 左侧边栏：历史记录与附件专区 ---
with st.sidebar:
    st.header("💬 对话历史")
    # 提取历史记录的简略信息展示
    if not st.session_state.messages:
        st.caption("今天还没有聊天哦...")
    else:
        for msg in st.session_state.messages:
            icon = "🙋‍♀️" if msg["role"] == "user" else "✨"
            # 只截取前12个字符作为预览
            preview_text = msg["content"].replace('\n', ' ')[:12] + "..."
            st.text(f"{icon} {preview_text}")
            
    st.divider() # 分割线
    
    st.header("📎 附件百宝箱")
    st.caption("把 Word/Excel/图片 扔进这里吧")
    uploaded_files = st.file_uploader(
        "上传文件", 
        type=['png', 'jpg', 'jpeg', 'pdf', 'txt', 'docx', 'xlsx', 'pptx', 'csv'],
        accept_multiple_files=True,
        label_visibility="collapsed" # 隐藏多余的标签文本，更美观
    )

# --- 🚀 主界面顶部标题 ---
st.title("✨ 你的专属 AI 助手")
st.caption("发文字、发语音、或者传文件，我都在这里。")

# --- 🚀 渲染历史聊天记录 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "audio_bytes" in msg and msg["audio_bytes"]:
            st.audio(msg["audio_bytes"], format="audio/wav")

# 为了不被底部悬浮的输入框挡住，加一点空白
st.write("")
st.write("")
st.write("")

# --- 🚀 核心排版：输入框上方的精巧控制栏 ---
# 使用列排布，把图标推到最左和最右
col_left, col_mid, col_right = st.columns([1, 8, 1])

with col_left:
    # 悬浮弹窗：点击 ⚙️ 才会弹出模型选择
    with st.popover("⚙️"):
        st.caption("切换大脑引擎")
        selected_model = st.radio(
            "选择模型",
            ["models/gemini-3-flash-preview", "models/gemini-3-pro-preview"],
            index=0 if "flash" in st.session_state.current_model else 1,
            label_visibility="collapsed"
        )
        if selected_model != st.session_state.current_model:
            st.session_state.current_model = selected_model
            st.session_state.messages = []
            st.session_state.chat_session = st.session_state.client.chats.create(
                model=st.session_state.current_model,
                config=types.GenerateContentConfig(system_instruction=persona)
            )
            st.rerun()

with col_right:
    # 悬浮弹窗：点击 🎤 才会弹出巨大的录音框
    with st.popover("🎤"):
        st.caption("点击录音")
        audio_data = st.audio_input("录音", label_visibility="collapsed")

# 底部打字输入框
prompt = st.chat_input("你想聊点什么呢？")

# --- 🚀 发送逻辑处理 ---
has_new_audio = False
audio_bytes = None
if audio_data:
    audio_bytes = audio_data.getvalue()
    audio_hash = hash(audio_bytes)
    if audio_hash not in st.session_state.processed_audios:
        has_new_audio = True

if prompt or has_new_audio:
    contents_to_send = []
    display_message = ""

    # 处理文件附件
    if uploaded_files:
        new_files = [f for f in uploaded_files if f.name not in st.session_state.processed_files]
        if new_files:
            with st.spinner(f"正在读取 {len(new_files)} 个新文件..."):
                for file in new_files:
                    file_ext = file.name.split('.')[-1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
                        tmp_file.write(file.getvalue())
                        tmp_file_path = tmp_file.name
                    try:
                        g_file = st.session_state.client.files.upload(file=tmp_file_path)
                        contents_to_send.append(g_file)
                        st.session_state.processed_files.add(file.name)
                    except Exception as e:
                        st.error(f"解析 {file.name} 失败：{e}")
                    finally:
                        if os.path.exists(tmp_file_path):
                            os.remove(tmp_file_path)
            display_message += f"📎 *[附件: 包含 {len(new_files)} 个文件]*\n\n"

    # 处理语音
    if has_new_audio:
        with st.spinner("正在倾听你的语音..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                tmp_audio.write(audio_bytes)
                tmp_audio_path = tmp_audio.name
            try:
                g_audio = st.session_state.client.files.upload(file=tmp_audio_path)
                contents_to_send.append(g_audio)
                st.session_state.processed_audios.add(audio_hash)
            except Exception as e:
                st.error(f"哎呀，语音发送遇到小阻碍：{e}")
            finally:
                if os.path.exists(tmp_audio_path):
                    os.remove(tmp_audio_path)
        display_message += "🎤 *[发送了一条语音]*\n\n"

    # 处理文字
    if prompt:
        contents_to_send.append(prompt)
        display_message += prompt
    elif has_new_audio and not prompt:
        contents_to_send.append("请听这段语音并温柔地回复我。")

    # 渲染用户气泡
    with st.chat_message("user"):
        st.markdown(display_message)
        if has_new_audio:
            st.audio(audio_bytes, format="audio/wav")
            
    st.session_state.messages.append({
        "role": "user", 
        "content": display_message,
        "audio_bytes": audio_bytes if has_new_audio else None
    })

    # 渲染AI气泡
    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(contents_to_send)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun() # 刷新界面，让侧边栏的历史记录实时更新
        except Exception as e:
            st.error(f"系统提示：An error has occurred, please try again. 详情: {e}")
