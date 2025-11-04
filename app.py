import streamlit as st

st.title("投票証明画像の集計ツール")

uploaded_files = st.file_uploader("証明画像をアップロード", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    st.write(f"{len(uploaded_files)} 枚の画像がアップロードされました！")
