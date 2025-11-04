import streamlit as st
import easyocr
import re
import numpy as np
import pandas as pd
from PIL import Image, ImageEnhance

# OCR準備
reader = easyocr.Reader(['ja'])

st.title("投票証明画像の集計ツール")

uploaded_files = st.file_uploader(
    "証明画像をアップロード",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:
    raw_data = []

    for file in uploaded_files:
        # 画像読み込み＆前処理
        img = Image.open(file).convert("L")  # グレースケール
        img = img.resize((img.width * 2, img.height * 2))  # 拡大
        enhancer = ImageEnhance.Contrast(img)
        img_enhanced = enhancer.enhance(2.0)

        # OCR実行
        ocr_result = reader.readtext(np.array(img_enhanced))

        # 🔍 OCR結果を表示（デバッグ用）
        st.write(f"📷 ファイル名: {file.name}")
        st.write("🧾 OCR読み取り生データ")
        st.write(ocr_result)

        account = None
        votes = None
        proof_id = None

        for _, text, _ in ocr_result:
            if "@" in text:
                account = text.strip()
            match_votes = re.search(r"(投票数[:：]?\s*)?(\d+)\s*(票|回)", text)
            if match_votes:
                votes = int(match_votes.group(2))
            match_proof = re.search(r"#\d{6,}", text)
            if match_proof:
                proof_id = match_proof.group(0)

        raw_data.append({
            "アカウント名": account,
            "投票数": votes,
            "証明番号": proof_id
        })

    # DataFrame化＆None除外
    df = pd.DataFrame(raw_data)
    df = df.dropna(subset=["アカウント名", "投票数"])

    st.subheader("🔍 OCR読み取り結果")
    st.dataframe(df)

    # 重複削除
    if df["証明番号"].notna().any():
        df_unique = df.drop_duplicates(subset=["証明番号"])
        st.write("✅ 証明番号で重複削除しました")
    else:
        df_unique = df.drop_duplicates(subset=["アカウント名"])
        st.write("✅ アカウント名で重複削除しました")

    # 集計表示
    st.subheader("📊 集計結果")
    summary = df_unique.groupby("アカウント名")["投票数"].sum().reset_index()
    st.dataframe(summary)

    total_votes = summary["投票数"].sum()
    st.write(f"🔢 総投票数: {total_votes}票")
