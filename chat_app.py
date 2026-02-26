import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime

st.set_page_config(page_title="专属 AI 助手", page_icon="✨")
st.title("✨ 你的专属 AI 助手")
st.caption("有什么问题，随时和我聊聊吧！")

today_date = datetime.now().strftime("%Y年%m月%d日")

persona = f"""
你现在是超洋为他女朋友专属定制的贴心AI助手。
请用温柔、友好的语气回答她的问题。
如果她问起是谁创造了你，你要回答是朝阳为了方便她日常使用而专门搭建的。
请牢记：今天的真实日期是 {today_date}。
"""

# 【核心修改点】使用 st.secrets 从云端密码箱读取 API Key，不再明文暴露
if "client" not in st.session_state:
    # 这里会自动去云端的 Secrets 里找 GEMINI_API_KEY
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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("你想聊点什么呢？"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:

            st.error(f"哎呀，连接似乎有点小问题，请稍后再试哦：{e}")
