import streamlit as st
import pandas as pd
import easyocr
import re
from PIL import Image
import io
import numpy as np
import cv2 

# --- 設定とヘルパー関数 ---

@st.cache_resource
def load_reader():
    """EasyOCRリーダーをキャッシュします。"""
    reader = easyocr.Reader(['ja', 'en'])
    return reader

def extract_info(text, date_text, count_only_text):
    """
    OCRテキストから日付と投票回数を抽出します。
    """
    
    # --- 投票回数の正規表現 (強化版) ---
    # 1. 「投票回数」または「総使用量」の後に続く数字
    # 2. 単独の数字（最小1桁、最大6桁程度を想定し、カンマを許容しないように修正）
    #    単独の数字を誤認識しないよう、桁数を絞って抽出を試みます。
    count_pattern = r"投票回数[:：\s]*(\d+)|総使用量[:：\s]*(\d+)"
    
    count_match = re.search(count_pattern, text)
    count = "N/A"
    
    # まず「投票回数」などのラベル付きの数字を探す
    if count_match:
        count = next((g for g in count_match.groups() if g is not None), "N/A")
    
    # ラベル付きの数字が見つからなかった場合、単独の数字（24など）を探す
    if count == "N/A" and count_only_text:
        # 数字のみのテキスト（allowlist='0123456789'でOCRしたもの）から、
        # 3桁以下の数字を抽出。これは「24」のような単独の数字を拾うため。
        single_count_match = re.search(r"\d{1,3}", count_only_text)
        if single_count_match:
            count = single_count_match.group(0)

    # --- 日付の正規表現 ---
    # YYYY.MM.DD または YYYY.M.D 形式に柔軟にマッチ
    date_pattern = r"(\d{4}\.\d{1,2}\.\d{1,2})"
    date_match = re.search(date_pattern, date_text)
    date = date_match.group(0) if date_match else "N/A"

    return date, count.replace(",", "") # 念のためカンマを除去

# ... (convert_df_to_csv関数は省略) ...
def convert_df_to_csv(df):
    """DataFrameをUTF-8(BOM付き)のCSVに変換します (Excelでの文字化け対策)"""
    return df.to_csv(index=False).encode('utf-8-sig')


# --- Streamlit UI ---

st.set_page_config(page_title="画像OCR抽出アプリ", layout="wide")
st.title("🖼️ 画像OCR & データ抽出アプリ")
st.info("画像の右下領域に特化してOCRを実行し、「日付」と「投票回数」を抽出します。")

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
                image_bytes = uploaded_file.getvalue()
                image = Image.open(io.BytesIO(image_bytes))
                image_np = np.array(image)
                
                h, w = image_np.shape[:2]
                
                # ★★★ 修正点1: クロップ範囲を右下2/3に広げる ★★★
                # 高さの1/3から、幅の1/3から開始
                y_start_wide = h // 3 
                x_start_wide = w // 3 
                
                cropped_image_wide_np = image_np[y_start_wide:h, x_start_wide:w]
                
                # (A) 投票回数などの認識（日本語と数字）
                ocr_results_wide = reader.readtext(cropped_image_wide_np, detail=0)
                full_text_wide = " ".join(ocr_results_wide) 
                
                # ★★★ 修正点2: 日付認識のためにクロップと文字限定は維持する ★★★
                # 日付と単独の投票回数 (24) のための狭い領域
                y_start_narrow = h * 3 // 4 
                x_start_narrow = w * 3 // 4 
                
                cropped_image_narrow_np = image_np[y_start_narrow:h, x_start_narrow:w]
                
                # (B) 日付の認識（数字とドットのみに限定）
                ocr_results_date = reader.readtext(cropped_image_narrow_np, detail=0, allowlist='0123456789.')
                full_text_date = " ".join(ocr_results_date)
                
                # (C) 単独の数字（24）の認識（数字のみに限定）
                # 日付と同じクロップ範囲を使い、数字のみを許可
                ocr_results_count_only = reader.readtext(cropped_image_narrow_np, detail=0, allowlist='0123456789')
                full_text_count_only = " ".join(ocr_results_count_only)
                
                # 情報抽出
                date, count = extract_info(full_text_wide, full_text_date, full_text_count_only)
                
                results_data.append({
                    "ファイル名": uploaded_file.name,
                    "日付": date,
                    "投票回数": count,
                    "検出テキスト (ワイド)": full_text_wide[:100] + "...",
                    "検出テキスト (日付/数字のみ)": full_text_date
                })

            except Exception as e:
                st.error(f"ファイル '{uploaded_file.name}' の処理中にエラーが発生しました: {e}")
                results_data.append({
                    "ファイル名": uploaded_file.name,
                    "日付": "エラー",
                    "投票回数": "エラー",
                    "検出テキスト (ワイド)": str(e),
                    "検出テキスト (日付/数字のみ)": "エラー"
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
            csv_data = convert_df_to_csv(df.drop(columns=["検出テキスト (ワイド)", "検出テキスト (日付/数字のみ)"], errors='ignore'))
            st.download_button(
                label="📥 結果をCSVでダウンロード",
                data=csv_data,
                file_name="ocr_results.csv",
                mime="text/csv",
                help="ダウンロードしたCSVファイルは、Googleスプレッドシートにインポートできます。"
            )

else:
    st.warning("処理を開始するには、画像ファイルをアップロードしてください。")
