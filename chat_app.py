import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import tempfile
import os
import uuid  

st.set_page_config(page_title="专属 AI 助手", page_icon="✨")

# ==========================================
# 🔐 0. 门禁系统：账号密码登录
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("✨ 专属 AI 助手")
    st.caption("这里是私人专属空间，请输入通行证哦~")
    
    with st.form("login_form"):
        username = st.text_input("账号")
        password = st.text_input("密码", type="password") 
        submit = st.form_submit_button("登录进入")
        
        if submit:
            if username == "lichaoyang" and password == "86126748":
                st.session_state.logged_in = True
                st.rerun() 
            else:
                st.error("账号或密码不对哦，请再试一次~")
    
    st.stop() 

# ==========================================
# 下方为原有的核心应用程序（登录后可见）
# ==========================================

today_date = datetime.now().strftime("%Y年%m月%d日")
persona = f"""
你现在是朝阳为他女朋友专属定制的贴心AI助手。
请用温柔、友好的语气回答她的问题。
如果她问起是谁创造了你，你要回答是朝阳专门搭建的。
请牢记：今天的真实日期是 {today_date}。
"""

# ==========================================
# 1. 核心升级：多会话状态管理
# ==========================================
if "conversations" not in st.session_state:
    init_id = str(uuid.uuid4())
    st.session_state.conversations = {
        init_id: {
            "title": "新对话",
            "messages": [],
            "processed_files": set(),
            "processed_audios": set(),
            "model": "models/gemini-3-flash-preview",
            "chat_session": None
        }
    }
    st.session_state.current_chat_id = init_id

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

curr_chat_id = st.session_state.current_chat_id
curr_chat = st.session_state.conversations[curr_chat_id]

if curr_chat["chat_session"] is None:
    curr_chat["chat_session"] = st.session_state.client.chats.create(
        model=curr_chat["model"],
        config=types.GenerateContentConfig(system_instruction=persona)
    )

# --- 🚀 左侧边栏：多对话列表与附件专区 ---
with st.sidebar:
    if st.button("📝 发起新对话", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.conversations[new_id] = {
            "title": "新对话",
            "messages": [],
            "processed_files": set(),
            "processed_audios": set(),
            "model": curr_chat["model"], 
            "chat_session": None
        }
        st.session_state.current_chat_id = new_id
        st.rerun()
    
    st.write("")
    st.caption("对话列表")
    
    chat_items = list(st.session_state.conversations.items())
    for cid, c_data in reversed(chat_items):
        btn_label = f"👉 {c_data['title']}" if cid == curr_chat_id else f"💬 {c_data['title']}"
        if st.button(btn_label, key=cid, use_container_width=True):
            st.session_state.current_chat_id = cid
            st.rerun()

    st.divider()

    st.header("📎 附件百宝箱")
    st.caption("把 Word/Excel/PPT/图片 扔进这里吧")
    uploaded_files = st.file_uploader(
        "上传文件", 
        type=['png', 'jpg', 'jpeg', 'pdf', 'txt', 'docx', 'xlsx', 'pptx', 'csv'],
        accept_multiple_files=True,
        label_visibility="collapsed" 
    )
    
    st.write("")
    st.write("")
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# --- 🚀 主界面顶部 ---
st.title("✨ 你的专属 AI 助手")
st.caption("发文字、发语音、或者传文件，我都在这里。")

# --- 🚀 渲染当前会话的历史聊天记录 ---
for msg in curr_chat["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "audio_bytes" in msg and msg["audio_bytes"]:
            st.audio(msg["audio_bytes"], format="audio/wav")

# --- 🚀 UI 布局调整：动态垫片 ---
spacer_height = "55vh" if not curr_chat["messages"] else "2vh"
st.markdown(f'<div style="height: {spacer_height};"></div>', unsafe_allow_html=True)

# CSS：保持图标纯净感
st.markdown("""
<style>
div[data-testid="stPopover"] button {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    font-size: 28px !important; 
    padding: 0 !important;
}
div[data-testid="stPopover"] button svg {
    display: none !important; 
}
div[data-testid="stPopover"] button:hover {
    background: transparent !important;
    transform: scale(1.1);
    transition: all 0.2s;
}
</style>
""", unsafe_allow_html=True)

# --- 🚀 核心排版：输入框上方的图标栏 ---
col_left, col_mid, col_right = st.columns([1, 8, 1])

with col_left:
    with st.popover("⚙️"):
        st.caption("切换大脑引擎")
        selected_model = st.radio(
            "选择模型",
            ["models/gemini-3-flash-preview", "models/gemini-3-pro-preview"],
            index=0 if "flash" in curr_chat["model"] else 1,
            label_visibility="collapsed"
        )
        if selected_model != curr_chat["model"]:
            curr_chat["model"] = selected_model
            curr_chat["messages"] = []
            curr_chat["chat_session"] = st.session_state.client.chats.create(
                model=curr_chat["model"],
                config=types.GenerateContentConfig(system_instruction=persona)
            )
            st.rerun()

with col_right:
    with st.popover("🎤"):
        st.caption("点击下方录音")
        audio_data = st.audio_input("录音", label_visibility="collapsed")

prompt = st.chat_input("你想聊点什么呢？")

# --- 🚀 发送逻辑处理 ---
has_new_audio = False
audio_bytes = None
if audio_data:
    audio_bytes = audio_data.getvalue()
    audio_hash = hash(audio_bytes)
    if audio_hash not in curr_chat["processed_audios"]:
        has_new_audio = True

if prompt or has_new_audio:
    contents_to_send = []
    display_message = ""

    if uploaded_files:
        new_files = [f for f in uploaded_files if f.name not in curr_chat["processed_files"]]
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
                        curr_chat["processed_files"].add(file.name)
                    except Exception:
                        pass
                    finally:
                        if os.path.exists(tmp_file_path):
                            os.remove(tmp_file_path)
            display_message += f"📎 *[附件: 已上传 {len(new_files)} 个文件]*\n\n"

    if has_new_audio:
        with st.spinner("处理语音中..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                tmp_audio.write(audio_bytes)
                tmp_audio_path = tmp_audio.name
            try:
                g_audio = st.session_state.client.files.upload(file=tmp_audio_path)
                contents_to_send.append(g_audio)
                curr_chat["processed_audios"].add(audio_hash)
            except Exception:
                st.error("系统提示：An error has occurred, please try again.")
            finally:
                if os.path.exists(tmp_audio_path):
                    os.remove(tmp_audio_path)
        display_message += "🎤 *[发送了一条语音]*\n\n"

    if prompt:
        contents_to_send.append(prompt)
        display_message += prompt
        if curr_chat["title"] == "新对话":
            curr_chat["title"] = prompt[:10] + ("..." if len(prompt) > 10 else "")
    elif has_new_audio and not prompt:
        contents_to_send.append("请听这段语音。")
        if curr_chat["title"] == "新对话":
            curr_chat["title"] = "🎤 语音对话"

    # ==========================================
    # 🚨 核心修复区：防卡死机制
    # ==========================================
    if contents_to_send:
        with st.chat_message("user"):
            st.markdown(display_message)
            if has_new_audio:
                st.audio(audio_bytes, format="audio/wav")
        
        # 先把用户的话存入记忆
        curr_chat["messages"].append({
            "role": "user", 
            "content": display_message,
            "audio_bytes": audio_bytes if has_new_audio else None
        })

        with st.chat_message("assistant"):
            try:
                response = curr_chat["chat_session"].send_message(contents_to_send)
                st.markdown(response.text)
                curr_chat["messages"].append({"role": "assistant", "content": response.text})
                st.rerun() 
            except Exception as e:
                # 【关键修复】如果回复失败，把刚才存进去的“用户提问”从记忆里撤回！
                if curr_chat["messages"]:
                    curr_chat["messages"].pop()
                st.error(f"系统提示：An error has occurred, please try again. (暗号：{e})")
