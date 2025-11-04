import streamlit as st
import pandas as pd
import easyocr
from PIL import Image
import io

st.title("📊 投票証明OCRアプリ")

# OCR reader（日本語＋韓国語＋英語）
reader = easyocr.Reader(['ja', 'ko', 'en'])

uploaded_files = st.file_uploader(
    "投票証明画像をアップロード",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

data = []

def parse_text(text):
    account = ""
    proof_id = ""

    for line in text.split("\n"):
        if "@" in line:  # アカウント名抽出例
            account = line.strip()
        if "ID" in line or "No" in line:  # 証明番号抽出例
            proof_id = line.replace("ID", "").replace("No", "").strip()
    return account, proof_id

if uploaded_files:
    for file in uploaded_files:
        image = Image.open(file)
        
        # OCR
        result = reader.readtext(np.array(image), detail=0)
        text = "\n".join(result)

        account, proof_id = parse_text(text)

        data.append({
            "画像名": file.name,
            "アカウント名": account,
            "証明番号": proof_id,
            "OCR全文": text
        })

    df = pd.DataFrame(data)

    # 重複チェック
    df["重複(アカウント)"] = df.duplicated(subset=["アカウント名"], keep=False)
    df["重複(証明番号)"] = df.duplicated(subset=["証明番号"], keep=False)

    st.write("📋 OCR結果")
    st.dataframe(df)

    # 集計
    st.write("📈 集計結果")
    st.metric("総画像数", len(df))
    st.metric("重複アカウント", df["重複(アカウント)"].sum())
    st.metric("重複証明番号", df["重複(証明番号)"].sum())

    # CSVダウンロード
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="CSVダウンロード",
        data=csv,
        file_name="vote_results.csv",
        mime="text/csv"
    )