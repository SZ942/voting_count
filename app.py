import streamlit as st
import pytesseract
import re
import numpy as np
import pandas as pd
from PIL import Image, ImageEnhance

st.title("投票証明画像の集計ツール")

uploaded_files = st.file_uploader(
    "証明画像をアップロード",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:
    raw_data = []

    for file in uploaded_files:
        try:
            # 画像読み込み＆前処理
            img = Image.open(file).convert("L")
            img = img.resize((img.width * 2, img.height * 2))
            enhancer = ImageEnhance.Contrast(img)
            img_enhanced = enhancer.enhance(2.0)

            # OCR実行
            text = pytesseract.image_to_string(img_enhanced, lang="jpn")

            # OCR結果表示（デバッグ用）
            st.write(f"📷 ファイル名: {file.name}")
            st.write("🧾 OCR読み取り生テキスト")
            st.text(text)

            account = None
            votes = None
            proof_id = None

            for line in text.splitlines():
                if "@" in line:
                    account = line.strip()
                match_votes = re.search(r"(投票数[:：]?\s*)?(\d+)\s*(票|回)", line)
                if match_votes:
                    votes = int(match_votes.group(2))
                match_proof = re.search(r"#\d{6,}", line)
                if match_proof:
                    proof_id = match_proof.group(0)

            if account and votes:
                raw_data.append({
                    "アカウント名": account,
                    "投票数": votes,
                    "証明番号": proof_id
                })

        except Exception as e:
            st.error(f"{file.name} の処理中にエラーが発生しました: {e}")

    if raw_data:
        df = pd.DataFrame(raw_data)
        st.subheader("🔍 OCR読み取り結果")
        st.dataframe(df)

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
    else:
        st.warning("有効なOCRデータが取得できませんでした。画像の文字が読み取れない可能性があります。")
