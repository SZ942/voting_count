# streamlit_app.py

import streamlit as st
from PIL import Image
import easyocr
import io

# OCRリーダーの初期化（日本語と英語を対象）
reader = easyocr.Reader(['ja', 'en'], gpu=False)

st.title("📸 投票証明OCR読み取りツール")

# 複数画像アップロード
uploaded_files = st.file_uploader("画像をアップロード（複数可）", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.subheader(f"🖼️ {uploaded_file.name}")
        image = Image.open(uploaded_file)
        st.image(image, caption="アップロード画像", use_column_width=True)

        # OCR読み取り
        with st.spinner("OCR読み取り中..."):
            result = reader.readtext(np.array(image), detail=0)

        # 結果表示
        if result:
            st.success("✅ 読み取ったテキスト:")
            for line in result:
                st.write(f"- {line}")
        else:
            st.warning("⚠️ テキストが読み取れませんでした。画像の品質や文字の大きさを確認してください。")
