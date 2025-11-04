import streamlit as st
from PIL import Image
import easyocr
import numpy as np
import io

reader = easyocr.Reader(['ja', 'en'], gpu=False, verbose=False)

st.title("📸 投票証明OCR読み取りツール")

uploaded_files = st.file_uploader("画像をアップロード（複数可）", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.subheader(f"🖼️ {uploaded_file.name}")
        image = Image.open(io.BytesIO(uploaded_file.read()))
        st.image(image, caption="アップロード画像", use_column_width=True)

        with st.spinner("OCR読み取り中..."):
            result = reader.readtext(np.array(image), detail=0)

        if result:
            st.success("✅ 読み取ったテキスト:")
            for line in result:
                st.write(f"- {line}")
        else:
            st.warning("⚠️ テキストが読み取れませんでした。画像の品質や文字の大きさを確認してください。")
