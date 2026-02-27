import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import tempfile
import os

# 1. 网页的标题和基础设置
st.set_page_config(page_title="专属 AI 助手", page_icon="✨")
st.title("✨ 你的专属 AI 助手")
st.caption("有什么问题，或者有想让我看的图片、文档，随时发给我吧！")

today_date = datetime.now().strftime("%Y年%m月%d日")

persona = f"""
你现在是朝阳为他女朋友专属定制的贴心AI助手。
请用温柔、友好的语气回答她的问题。
如果她问起是谁创造了你，你要回答是朝阳为了方便她日常使用而专门搭建的。
请牢记：今天的真实日期是 {today_date}。
"""

# 2. 初始化 Gemini 客户端
if "client" not in st.session_state:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.session_state.client = genai.Client(api_key=api_key)
    
    st.session_state.chat_session = st.session_state.client.chats.create(
        model="models/gemini-3-flash-preview",
        config=types.GenerateContentConfig(
            system_instruction=persona
        )
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 🚀 新增：侧边栏文件上传区 ---
with st.sidebar:
    st.header("📎 发送附件")
    st.markdown("支持上传图片 (JPG/PNG) 或文档 (PDF/TXT)")
    
    # 文件上传控件
    uploaded_file = st.file_uploader("拖拽或点击选择文件", type=['png', 'jpg', 'jpeg', 'pdf', 'txt'])
    
    # 状态管理：确保同一个文件只被上传给大模型一次
    if uploaded_file and ("processed_file_name" not in st.session_state or st.session_state.processed_file_name != uploaded_file.name):
        with st.spinner("正在努力接收文件中..."):
            try:
                # 将 Streamlit 内存中的文件临时保存到本地硬盘
                file_extension = uploaded_file.name.split('.')[-1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                # 上传文件给 Gemini 服务器
                gemini_file = st.session_state.client.files.upload(file=tmp_file_path)
                
                # 把处理好的文件放入“待发送区”
                st.session_state.pending_file = gemini_file
                st.session_state.processed_file_name = uploaded_file.name
                
                st.success("✅ 文件已就绪！在右边输入你的问题发送吧。")
            except Exception as e:
                st.error(f"文件处理出现小插曲：{e}")
            finally:
                # 无论成功失败，清理本地的临时文件
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)

    # 如果用户点 'x' 删除了文件，我们也要清空待发送区
    elif not uploaded_file:
        if "pending_file" in st.session_state:
            del st.session_state.pending_file
        if "processed_file_name" in st.session_state:
            del st.session_state.processed_file_name
# -----------------------------------

# 3. 渲染历史聊天记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 接收输入并发送
if prompt := st.chat_input("你想聊点什么呢？"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        try:
            # --- 🚀 新增核心逻辑：判断是否带有附件 ---
            if "pending_file" in st.session_state:
                # 如果有等待发送的文件，把文件和文字打包一起发过去
                contents_to_send = [st.session_state.pending_file, prompt]
                # 发送完就清空待发送区，避免下次没传文件时重复发送
                del st.session_state.pending_file 
            else:
                # 正常纯文本对话
                contents_to_send = prompt
            # ----------------------------------------

            response = st.session_state.chat_session.send_message(contents_to_send)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            if "429" in str(e):
                st.warning("哎呀，现在聊天太火爆啦，我需要休息一小会儿，几分钟后再来找我哦~")
            else:
                st.error(f"连接似乎有点小问题：{e}")
