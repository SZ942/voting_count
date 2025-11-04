import streamlit as st
import pandas as pd
import easyocr
import re
from PIL import Image
import io
import numpy as np
import cv2 # OpenCV をインポート (画像処理・クロップ用)

# --- 設定とヘルパー関数 ---

@st.cache_resource
def load_reader():
    """
    EasyOCRリーダーをキャッシュします。
    """
    reader = easyocr.Reader(['ja', 'en'])
    return reader

def extract_info(text):
    """
    OCRテキストから日付と投票回数を抽出します。
    正規表現パターンは前回と同じです。
    """
    
    # 日付の正規表現: YYYY.MM.DD
    date_pattern = r"(\d{4}\.\d{1,2}\.\d{1,2})"
    date_match = re.search(date_pattern, text)
    date = date_match.group(0) if date_match else "N/A"

    # 投票回数の正規表現: 「投票回数」または「総使用量」の後の数字
    count_pattern = r"投票回数[:：\s]*([\d,]+)|総使用量[:：\s]*([\d,]+)"
    count_match = re.search(count_pattern, text)
    
    count = "N/A"
    if count_match:
        count = next((g for g in count_match.groups() if g is not None), "N/A")
        count = count.replace(",", "") # カンマを除去

    return date, count

def convert_df_to_csv(df):
    """DataFrameをUTF-8(BOM付き)のCSVに変換します (Excelでの文字化け対策)"""
    return df.to_csv(index=False).encode('utf-8-sig')

# --- Streamlit UI ---

st.set_page_config(page_title="画像OCR抽出アプリ", layout="wide")
st.title("🖼️ 画像OCR & データ抽出アプリ")
st.info("複数の画像ファイルをアップロードし、OCRで「日付」と「投票回数」を抽出して表を作成します。")

# 1. 画像のアップロード
uploaded_files = st.file_uploader(
    "ここに画像をドラッグ＆ドロップしてください",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

if uploaded_files:
    st.write(f"--- {len(uploaded_files)} 件のファイルを読み込みました ---")
    
    if st.button(" OCRを実行して表を作成 ", type="primary"):
        
        try:
            reader = load_reader()
        except Exception as e:
            st.error(f"EasyOCRリーダーのロードに失敗しました: {e}")
            st.stop()

        progress_bar = st.progress(0, text="処理を開始します...")
        results_data = []

        # 2. OCR処理と情報抽出
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                # 画像の読み込み (PILからNumPy配列へ)
                image_bytes = uploaded_file.getvalue()
                image = Image.open(io.BytesIO(image_bytes))
                image_np = np.array(image)
                
                # ★★★★★ 修正点: 右下の領域にクロップ ★★★★★
                # 画像の高さ(h)と幅(w)を取得
                h, w = image_np.shape[:2]
                
                # 右下の領域を切り出す (例: 高さの半分から、幅の半分から)
                # この座標は、画像のレイアウトに合わせて調整可能です
                y_start = h // 2  # 高さの真ん中
                x_start = w // 2  # 幅の真ん中
                
                # クロップした画像 (NumPy配列)
                cropped_image_np = image_np[y_start:h, x_start:w]
                
                # (念のため) グレースケール画像だった場合にRGBに変換
                if cropped_image_np.ndim == 2:
                    cropped_image_np = cv2.cvtColor(cropped_image_np, cv2.COLOR_GRAY2RGB)
                # ★★★★★ 修正ここまで ★★★★★

                # OCR実行 (クロップした画像を使用)
                ocr_results = reader.readtext(cropped_image_np, detail=0)
                full_text = " ".join(ocr_results) # 検出したテキストを全て連結

                # 情報抽出
                date, count = extract_info(full_text)
                
                results_data.append({
                    "ファイル名": uploaded_file.name,
                    "日付": date,
                    "投票回数": count,
                    "検出テキスト (参考)": full_text[:200] + "..." if len(full_text) > 200 else full_text
                })

            except Exception as e:
                st.error(f"ファイル '{uploaded_file.name}' の処理中にエラーが発生しました: {e}")
                results_data.append({
                    "ファイル名": uploaded_file.name,
                    "日付": "エラー",
                    "投票回数": "エラー",
                    "検出テキスト (参考)": str(e)
                })
            
            progress_bar.progress((i + 1) / len(uploaded_files), text=f"処理中: {uploaded_file.name}")

        progress_bar.empty()
        st.success("全てのファイルの処理が完了しました。")

        # 3. 表の作成
        if results_data:
            df = pd.DataFrame(results_data)
            st.subheader("抽出結果")
            st.dataframe(df, use_container_width=True)
            
            # 4. CSVダウンロード
            csv_data = convert_df_to_csv(df)
            st.download_button(
                label="📥 結果をCSVでダウンロード",
                data=csv_data,
                file_name="ocr_results.csv",
                mime="text/csv",
                help="ダウンロードしたCSVファイルは、Googleスプレッドシートにインポートできます。"
            )

else:
    st.warning("処理を開始するには、画像ファイルをアップロードしてください。")
