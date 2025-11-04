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
    # 日本語と英語を認識
    reader = easyocr.Reader(['ja', 'en'])
    return reader

def extract_info(text, date_text):
    """
    OCRテキストから日付と投票回数を抽出します。
    投票回数の抽出はメインのテキストから、日付はクロップ範囲を絞ったテキストから行います。
    """
    
    # --- 投票回数の正規表現 ---
    # 「投票回数」または「総使用量」の後に続く数字を抽出。
    # 数字はカンマを含む可能性があるので [\d,]+ で対応。
    count_pattern = r"投票回数[:：\s]*([\d,]+)|総使用量[:：\s]*([\d,]+)"
    
    count_match = re.search(count_pattern, text)
    
    count = "N/A"
    if count_match:
        count = next((g for g in count_match.groups() if g is not None), "N/A")
        count = count.replace(",", "") # カンマを除去

    # --- 日付の正規表現 ---
    # YYYY.MM.DD または YYYY.M.D 形式に柔軟にマッチ
    # date_text (数字とドットに特化したOCR結果) を使用
    date_pattern = r"(\d{4}\.\d{1,2}\.\d{1,2})"
    date_match = re.search(date_pattern, date_text)
    date = date_match.group(0) if date_match else "N/A"

    return date, count

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
            
            # --- デバッグ用: ファイル名と現在の進捗表示 ---
            st.sidebar.markdown(f"**処理中:** `{uploaded_file.name}`")
            # ----------------------------------------------
            
            try:
                # 画像の読み込み (PILからNumPy配列へ)
                image_bytes = uploaded_file.getvalue()
                image = Image.open(io.BytesIO(image_bytes))
                image_np = np.array(image)
                
                h, w = image_np.shape[:2]
                
                # ★★★ 修正点1: クロップ範囲を右下1/3に絞る ★★★
                # 目的の文字周辺に絞ることで精度向上を狙う
                y_start_count = h * 2 // 3 # 高さの2/3から
                x_start_count = w * 2 // 3 # 幅の2/3から
                
                cropped_image_count_np = image_np[y_start_count:h, x_start_count:w]
                
                # (A) 投票回数などの認識（日本語と数字）
                ocr_results_count = reader.readtext(cropped_image_count_np, detail=0)
                full_text_count = " ".join(ocr_results_count) 
                
                # ★★★ 修正点2: 日付認識のためにさらに範囲を絞り、認識文字を限定する ★★★
                # 日付は画像の一番右下の隅にあると仮定
                y_start_date = h * 3 // 4 # 高さの3/4から
                x_start_date = w * 3 // 4 # 幅の3/4から
                
                cropped_image_date_np = image_np[y_start_date:h, x_start_date:w]
                
                # (B) 日付の認識（数字とドットのみに限定: 誤認識防止）
                # allowlist: 認識を許可する文字セットを指定 (数字とドット)
                ocr_results_date = reader.readtext(cropped_image_date_np, detail=0, allowlist='0123456789.')
                full_text_date = " ".join(ocr_results_date)
                
                # 情報抽出
                date, count = extract_info(full_text_count, full_text_date)
                
                results_data.append({
                    "ファイル名": uploaded_file.name,
                    "日付": date,
                    "投票回数": count,
                    "検出テキスト (全体/参考)": full_text_count[:100] + "...",
                    "検出テキスト (日付/参考)": full_text_date
                })

            except Exception as e:
                st.error(f"ファイル '{uploaded_file.name}' の処理中にエラーが発生しました: {e}")
                results_data.append({
                    "ファイル名": uploaded_file.name,
                    "日付": "エラー",
                    "投票回数": "エラー",
                    "検出テキスト (全体/参考)": str(e),
                    "検出テキスト (日付/参考)": "エラー"
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
            csv_data = convert_df_to_csv(df.drop(columns=["検出テキスト (全体/参考)", "検出テキスト (日付/参考)"], errors='ignore'))
            st.download_button(
                label="📥 結果をCSVでダウンロード",
                data=csv_data,
                file_name="ocr_results.csv",
                mime="text/csv",
                help="ダウンロードしたCSVファイルは、Googleスプレッドシートにインポートできます。"
            )

else:
    st.warning("処理を開始するには、画像ファイルをアップロードしてください。")
