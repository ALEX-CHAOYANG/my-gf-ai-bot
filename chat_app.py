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

# 1. 初始化变量
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()
if "processed_audios" not in st.session_state:
    st.session_state.processed_audios = set()
if "current_model" not in st.session_state:
    st.session_state.current_model = "models/gemini-2.0-flash-exp" # 默认模型
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.client.chats.create(
        model=st.session_state.current_model,
        config=types.GenerateContentConfig(system_instruction=persona)
    )

# --- 🚀 左侧边栏：仅保留附件功能 ---
with st.sidebar:
    st.header("📎 附件百宝箱")
    st.caption("把需要我看的文档或图片扔进这里")
    uploaded_files = st.file_uploader(
        "上传文件", 
        type=['png', 'jpg', 'jpeg', 'pdf', 'txt', 'docx', 'xlsx', 'pptx', 'csv'],
        accept_multiple_files=True,
        label_visibility="collapsed" 
    )

# --- 🚀 主界面顶部 ---
st.title("✨ 你的专属 AI 助手")
st.caption("发文字、发语音、或者传文件，我都在这里。")

# --- 🚀 渲染历史聊天记录 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "audio_bytes" in msg and msg["audio_bytes"]:
            st.audio(msg["audio_bytes"], format="audio/wav")

# --- 🚀 UI 布局调整：动态垫片 ---
spacer_height = "55vh" if not st.session_state.messages else "2vh"
st.markdown(f'<div style="height: {spacer_height};"></div>', unsafe_allow_html=True)

# CSS 优化：让按钮看起来像带文字的标签，去掉多余边框
st.markdown("""
<style>
div[data-testid="stPopover"] button {
    border: 1px solid #f0f2f6 !important;
    background: #ffffff !important;
    border-radius: 20px !important;
    padding: 2px 12px !important;
    font-size: 14px !important;
    color: #555 !important;
}
div[data-testid="stPopover"] button:hover {
    border-color: #ff4b4b !important;
    color: #ff4b4b !important;
}
/* 隐藏下拉箭头 */
div[data-testid="stPopover"] button svg {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# --- 🚀 核心排版：带文字的图标按钮栏 ---
col_left, col_mid, col_right = st.columns([2, 5, 2])

with col_left:
    # ⚙️ 旁边增加“模型选择”
    with st.popover("⚙️ 模型选择"):
        st.caption("切换大脑引擎")
        selected_model = st.radio(
            "选择模型",
            ["models/gemini-2.0-flash-exp", "models/gemini-2.0-pro-exp-02-05"],
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
    # 🎤 旁边增加“语音输入”
    with st.popover("🎤 语音输入"):
        st.caption("点击下方开始说话")
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

    # 1. 处理文件
    if uploaded_files:
        new_files = [f for f in uploaded_files if f.name not in st.session_state.processed_files]
        if new_files:
            with st.spinner(f"正在读取文件..."):
                for file in new_files:
                    file_ext = file.name.split('.')[-1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
                        tmp_file.write(file.getvalue())
                        tmp_file_path = tmp_file.name
                    try:
                        g_file = st.session_state.client.files.upload(file=tmp_file_path)
                        contents_to_send.append(g_file)
                        st.session_state.processed_files.add(file.name)
                    except Exception:
                        pass
                    finally:
                        if os.path.exists(tmp_file_path):
                            os.remove(tmp_file_path)
            display_message += f"📎 *[已上传 {len(new_files)} 个附件]*\n\n"

    # 2. 处理语音
    if has_new_audio:
        with st.spinner("处理语音中..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                tmp_audio.write(audio_bytes)
                tmp_audio_path = tmp_audio.name
            try:
                g_audio = st.session_state.client.files.upload(file=tmp_audio_path)
                contents_to_send.append(g_audio)
                st.session_state.processed_audios.add(audio_hash)
            except Exception:
                st.error("系统提示：An error has occurred, please try again.")
            finally:
                if os.path.exists(tmp_audio_path):
                    os.remove(tmp_audio_path)
        display_message += "🎤 *[发送了一条语音]*\n\n"

    # 3. 处理文字
    if prompt:
        contents_to_send.append(prompt)
        display_message += prompt
    elif has_new_audio:
        contents_to_send.append("请听这段语音。")

    # 渲染与请求
    if contents_to_send:
        with st.chat_message("user"):
            st.markdown(display_message)
            if has_new_audio:
                st.audio(audio_bytes, format="audio/wav")
        
        st.session_state.messages.append({
            "role": "user", 
            "content": display_message,
            "audio_bytes": audio_bytes if has_new_audio else None
        })

        with st.chat_message("assistant"):
            try:
                response = st.session_state.chat_session.send_message(contents_to_send)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception:
                st.error("系统提示：An error has occurred, please try again.")
