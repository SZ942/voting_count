import streamlit as st
import pandas as pd
import easyocr
import re
from PIL import Image
import io
import numpy as np

# --- 設定とヘルパー関数 ---

@st.cache_resource
def load_reader():
    """
    EasyOCRリーダーをキャッシュします。
    初回起動時にモデルをダウンロードするため、時間がかかることがあります。
    """
    reader = easyocr.Reader(['ja', 'en']) # 日本語と英語を認識
    return reader

def extract_info(text):
    """
    OCRテキストから日付と投票回数を抽出します。
    提供された画像パターンに合わせて正規表現を調整しています。
    """
    
    # --- デバッグ用 (不要ならコメントアウトまたは削除) ---
    # with st.expander("デバッグ: OCR生テキスト"):
    #     st.text(text)
    # ----------------------------------------------------

    # 日付の正規表現
    # YYYY.MM.DD 形式にマッチ。画像右下の黄色い文字のパターンに対応。
    # OCRが「2025.10.31」のように認識すると仮定。
    date_pattern = r"(\d{4}\.\d{1,2}\.\d{1,2})"
    date_match = re.search(date_pattern, text)
    date = date_match.group(0) if date_match else "N/A"

    # 投票回数の正規表現
    # 「投票回数」または「総使用量」の後に続く数字を抽出。
    # 数字はカンマを含む可能性があるので [\d,]+ で対応。
    # 複数のパターンをOR条件(|)で連結し、最初のマッチを採用。
    
    # 投票回数: 123 の形式
    # 総使用量: 123 の形式
    count_pattern = r"投票回数[:：\s]*([\d,]+)|総使用量[:：\s]*([\d,]+)"
    
    count_match = re.search(count_pattern, text)
    
    count = "N/A"
    if count_match:
        # group(1) (「投票回数」の後) または group(2) (「総使用量」の後) のいずれか
        count = next((g for g in count_match.groups() if g is not None), "N/A")
        # 抽出した数字からカンマを除去
        count = count.replace(",", "")

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
    
    # 実行ボタン
    if st.button(" OCRを実行して表を作成 ", type="primary"):
        
        # EasyOCRリーダーのロード（キャッシュ利用）
        try:
            reader = load_reader()
        except Exception as e:
            st.error(f"EasyOCRリーダーのロードに失敗しました: {e}")
            st.error("（Streamlit Cloudデプロイ直後は、モデルのダウンロードに時間がかかることがあります）")
            st.stop()

        progress_bar = st.progress(0, text="処理を開始します...")
        results_data = [] # 抽出結果を格納するリスト

        # 2. OCR処理と情報抽出
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                # 画像の読み込み
                image_bytes = uploaded_file.getvalue()
                image = Image.open(io.BytesIO(image_bytes))
                image_np = np.array(image) # EasyOCRはNumPy配列を必要とする

                # OCR実行 (detail=0 でテキストのみのリストを取得)
                # 画像をトリミングしてOCR範囲を絞ることで精度向上も期待できるが、
                # まずは全体で試行。必要であれば画像処理を追加。
                ocr_results = reader.readtext(image_np, detail=0)
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
            
            # プログレスバーの更新
            progress_bar.progress((i + 1) / len(uploaded_files), text=f"処理中: {uploaded_file.name}")

        progress_bar.empty()
        st.success("全てのファイルの処理が完了しました。")

        # 3. 表の作成 (Pandas DataFrame)
        if results_data:
            df = pd.DataFrame(results_data)
            
            st.subheader("抽出結果")
            st.dataframe(df, use_container_width=True)
            
            # 4. CSVダウンロード（Googleスプレッドシート転記用）
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

