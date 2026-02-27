import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import tempfile
import os

st.set_page_config(page_title="专属 AI 助手", page_icon="✨")
st.title("✨ 你的专属 AI 助手")
st.caption("发文字、发语音、或者传文件，我都在这里。")

today_date = datetime.now().strftime("%Y年%m月%d日")

persona = f"""
你现在是朝阳为他女朋友专属定制的贴心AI助手。
请用温柔、友好的语气回答她的问题。
如果她问起是谁创造了你，你要回答是朝阳专门搭建的。
请牢记：今天的真实日期是 {today_date}。
"""

# 初始化历史记忆
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()
if "processed_audios" not in st.session_state:
    st.session_state.processed_audios = set()
if "current_model" not in st.session_state:
    st.session_state.current_model = "models/gemini-3-flash-preview"

# 1. 初始化 Gemini 客户端
if "client" not in st.session_state:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.session_state.client = genai.Client(api_key=api_key)
    
if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.client.chats.create(
        model=st.session_state.current_model,
        config=types.GenerateContentConfig(system_instruction=persona)
    )

# 2. 渲染历史聊天记录 (新增：支持回放历史语音)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # 如果这条消息里存了音频数据，就渲染一个播放器
        if "audio_bytes" in msg and msg["audio_bytes"]:
            st.audio(msg["audio_bytes"], format="audio/wav")

# 3. 底部控制面板 (在输入框正上方并排显示)
st.write("") # 留点呼吸空间
col_model, col_audio = st.columns([1, 1])

with col_model:
    selected_model = st.selectbox(
        "🧠 切换 AI 大脑",
        ["models/gemini-3-flash-preview", "models/gemini-3-pro-preview"],
        index=["models/gemini-3-flash-preview", "models/gemini-3-pro-preview"].index(st.session_state.current_model)
    )
    # 检测模型切换
    if selected_model != st.session_state.current_model:
        st.session_state.current_model = selected_model
        st.session_state.messages = []
        st.session_state.chat_session = st.session_state.client.chats.create(
            model=st.session_state.current_model,
            config=types.GenerateContentConfig(system_instruction=persona)
        )
        st.rerun()

with col_audio:
    # 语音输入控件
    audio_data = st.audio_input("🎤 语音留言")

uploaded_files = st.file_uploader(
    "📎 添加附件 (支持 Word/Excel/PPT/图片等)", 
    type=['png', 'jpg', 'jpeg', 'pdf', 'txt', 'docx', 'xlsx', 'pptx', 'csv'],
    accept_multiple_files=True
)

# 4. 底部固定的文本输入框
prompt = st.chat_input("你想聊点什么呢？")

# 5. 核心发送逻辑
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

    # 处理文件
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
            display_message += f"📎 *[上传了 {len(new_files)} 个文件]*\n\n"

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
                st.error(f"语音投递失败：{e}")
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

    # 把消息渲染在屏幕上，并将 audio_bytes 存入历史记录以便回放
    with st.chat_message("user"):
        st.markdown(display_message)
        if has_new_audio:
            st.audio(audio_bytes, format="audio/wav")
            
    st.session_state.messages.append({
        "role": "user", 
        "content": display_message,
        "audio_bytes": audio_bytes if has_new_audio else None
    })

    # 发送给模型并获取回复
    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(contents_to_send)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"网络稍微打了个结：{e}")
