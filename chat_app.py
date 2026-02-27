import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import tempfile
import os

# 1. 网页的标题和基础设置
st.set_page_config(page_title="专属 AI 助手", page_icon="✨")
st.title("✨ 你的专属 AI 助手")
st.caption("发文字、发语音、或者一次丢多个文档给我都可以哦！")

today_date = datetime.now().strftime("%Y年%m月%d日")

persona = f"""
你现在是超洋为他女朋友专属定制的贴心AI助手。
请用温柔、友好的语气回答她的问题。
如果她问起是谁创造了你，你要回答是超洋为了方便她日常使用而专门搭建的。
请牢记：今天的真实日期是 {today_date}。
对于她上传的文档或表格，请耐心帮她提炼和解答。
"""

# 初始化历史记忆和文件防重传检测器
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()
if "processed_audios" not in st.session_state:
    st.session_state.processed_audios = set()

# --- 🚀 第一大升级：侧边栏模型切换与多模态输入 ---
with st.sidebar:
    st.header("⚙️ 引擎设置")
    selected_model = st.selectbox(
        "🧠 选择 AI 大脑版本",
        ["models/gemini-3-flash-preview", "models/gemini-3-pro-preview"]
    )

    # 检测到模型切换，重置当前对话
    if "current_model" not in st.session_state:
        st.session_state.current_model = selected_model
    elif st.session_state.current_model != selected_model:
        st.session_state.current_model = selected_model
        st.session_state.messages = []
        st.session_state.processed_files = set()
        st.session_state.processed_audios = set()
        if "chat_session" in st.session_state:
            del st.session_state.chat_session
        st.rerun()  # 刷新界面重新应用新模型

    st.header("📎 批量发送附件")
    # 开启多文件上传，并加入 Office 格式支持
    uploaded_files = st.file_uploader(
        "支持批量拖拽 (Word/Excel/PPT/PDF/图片等)",
        type=['png', 'jpg', 'jpeg', 'pdf', 'txt', 'docx', 'xlsx', 'pptx', 'csv'],
        accept_multiple_files=True
    )

    st.header("🎤 语音留言")
    # Streamlit 原生录音控件
    audio_data = st.audio_input("点击麦克风对我说")
# --------------------------------------------------

# 2. 初始化 Gemini 客户端
if "client" not in st.session_state:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.session_state.client = genai.Client(api_key=api_key)

if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.client.chats.create(
        model=st.session_state.current_model,
        config=types.GenerateContentConfig(
            system_instruction=persona
        )
    )

# 3. 渲染历史聊天记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 🚀 第二大升级：多模态智能合并发送逻辑 ---
prompt = st.chat_input("你想聊点什么呢？")

# 检查是否有刚刚录制的新语音
has_new_audio = False
if audio_data:
    audio_hash = hash(audio_data.getvalue())
    if audio_hash not in st.session_state.processed_audios:
        has_new_audio = True

# 只要触发了文字发送，或者有新录音，就启动核心处理大脑
if prompt or has_new_audio:
    contents_to_send = []
    display_message = ""

    # 步骤 A：把还没发过的新文件，统统挂载上去
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
                        # 批量上传给大模型
                        g_file = st.session_state.client.files.upload(file=tmp_file_path)
                        contents_to_send.append(g_file)
                        # 记录已发文件，防止下次聊天重复发送浪费流量
                        st.session_state.processed_files.add(file.name)
                    except Exception as e:
                        st.error(f"文件 {file.name} 解析出了一点小错：{e}")
                    finally:
                        if os.path.exists(tmp_file_path):
                            os.remove(tmp_file_path)
            display_message += f"📎 *[附件: 上传了 {len(new_files)} 个文件]*\n\n"

    # 步骤 B：把新录的语音挂载上去
    if has_new_audio:
        with st.spinner("正在倾听你的语音..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                tmp_audio.write(audio_data.getvalue())
                tmp_audio_path = tmp_audio.name
            try:
                g_audio = st.session_state.client.files.upload(file=tmp_audio_path)
                contents_to_send.append(g_audio)
                st.session_state.processed_audios.add(audio_hash)
            except Exception as e:
                st.error(f"语音发送失败：{e}")
            finally:
                if os.path.exists(tmp_audio_path):
                    os.remove(tmp_audio_path)
        display_message += "🎤 *[发送了一条语音]*\n\n"

    # 步骤 C：挂载文字内容
    if prompt:
        contents_to_send.append(prompt)
        display_message += prompt
    elif has_new_audio and not prompt:
        # 如果只发了语音没打字，自动补一句命令让模型听语音
        contents_to_send.append("请听这段语音并温柔地回复我。")

    # 步骤 D：呈现在屏幕上并发送给 Gemini
    with st.chat_message("user"):
        st.markdown(display_message)
    st.session_state.messages.append({"role": "user", "content": display_message})

    with st.chat_message("assistant"):
        try:
            # 将 [文件1, 文件2, 语音, 文本] 一次性投递给大模型
            response = st.session_state.chat_session.send_message(contents_to_send)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            if "429" in str(e):
                st.warning("哎呀，系统正在飞速运转，我需要稍作喘息，请几分钟后再对我说哦~")
            else:
                st.error(f"网络稍微打了个结：{e}")
