import streamlit as st

st.title("投票証明画像の集計ツール")

uploaded_files = st.file_uploader("証明画像をアップロード", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    st.write(f"{len(uploaded_files)} 枚の画像がアップロードされました！")
import streamlit as st
import easyocr
import re
from PIL import Image, ImageEnhance
import pandas as pd

reader = easyocr.Reader(['ja'])

st.title("投票証明画像の集計ツール")

uploaded_files = st.file_uploader("証明画像をアップロード", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    raw_data = []

    for file in uploaded_files:
        img = Image.open(file)
        enhancer = ImageEnhance.Contrast(img)
        img_enhanced = enhancer.enhance(2.0)

        ocr_result = reader.readtext(img_enhanced)
        account = None
        votes = None
        proof_id = None

        for _, text, _ in ocr_result:
            if "@" in text:
                account = text.strip()
            match_votes = re.search(r"(\d+)\s*票", text)
            if match_votes:
                votes = int(match_votes.group(1))
            match_proof = re.search(r"#\d{6,}", text)
            if match_proof:
                proof_id = match_proof.group(0)

        raw_data.append({
            "アカウント名": account,
            "投票数": votes,
            "証明番号": proof_id
        })

    df = pd.DataFrame(raw_data)

    st.subheader("🔍 OCR読み取り結果")
    st.dataframe(df)

    # 重複チェック
    if df["証明番号"].notna().any():
        df_unique = df.drop_duplicates(subset=["証明番号"])
        st.write("✅ 証明番号で重複削除しました")
    else:
        df_unique = df.drop_duplicates(subset=["アカウント名"])
        st.write("✅ アカウント名で重複削除しました")

    st.subheader("📊 集計結果")
    summary = df_unique.groupby("アカウント名")["投票数"].sum().reset_index()
    st.dataframe(summary)

    total_votes = summary["投票数"].sum()
    st.write(f"🔢 総投票数: {total_votes}票")
