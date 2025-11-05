// OCR対象の画像が保存されているフォルダ名を指定してください
const INPUT_FOLDER_NAME = "OCR_Input";
// OCR結果を書き込むシート名を指定してください
const OUTPUT_SHEET_NAME = "シート1"; // 例: スプレッドシートのデフォルトのシート名

/**
 * Google Driveフォルダ内の新しい画像に対してOCRを実行し、
 * 結果をスプレッドシートに書き込みます。
 */
function processImagesForOCR() {
  
  // 1. スプレッドシートと出力シートを取得
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(OUTPUT_SHEET_NAME);
  if (!sheet) {
    Logger.log(`シート「${OUTPUT_SHEET_NAME}」が見つかりません。`);
    return;
  }
  
  // 2. 入力フォルダを取得
  const folders = DriveApp.getFoldersByName(INPUT_FOLDER_NAME);
  if (!folders.hasNext()) {
    Logger.log(`フォルダ「${INPUT_FOLDER_NAME}」が見つかりません。`);
    return;
  }
  const folder = folders.next();
  
  // 3. フォルダ内の未処理の画像ファイルを取得 (JPEG, PNG, PDFを対象)
  const files = folder.getFilesByType(MimeType.JPEG);
  const pngFiles = folder.getFilesByType(MimeType.PNG);
  const pdfFiles = folder.getFilesByType(MimeType.PDF);

  const allFiles = [];
  while (files.hasNext()) {
    allFiles.push(files.next());
  }
  while (pngFiles.hasNext()) {
    allFiles.push(pngFiles.next());
  }
  while (pdfFiles.hasNext()) {
    allFiles.push(pdfFiles.next());
  }
  
  Logger.log(`処理対象のファイル数: ${allFiles.length}`);

  
  // 4. 各ファイルに対してOCR処理を実行
  const processedFiles = [];
  for (const file of allFiles) {
    const fileId = file.getId();
    const fileName = file.getName();
    
    try {
      // **【重要】Advanced Drive Service (Drive.Files.insert) を使ってOCRを実行**
      // 画像をGoogleドキュメントとして作成し、その際にOCRを有効化します。
      const resource = {
        title: `OCR結果_${fileName}`,
        parents: [{id: folder.getId()}] // 結果のドキュメントも同じフォルダに保存
      };
      
      const blob = file.getBlob();
      
      // OCR設定を有効にしてGoogleドキュメントを作成
      const ocrDoc = Drive.Files.insert(resource, blob, {
        ocr: true, 
        ocrLanguage: "ja" // 日本語を設定 (必要に応じて変更)
      });
      
      // 5. OCR結果のGoogleドキュメントからテキストを抽出
      const doc = DocumentApp.openById(ocrDoc.id);
      const text = doc.getBody().getText();
      
      // 6. スプレッドシートに書き出し
      const date = new Date();
      sheet.appendRow([date, fileName, text.trim()]);
      
      // 7. 処理済みファイルを識別するために、OCR結果のドキュメントを削除
      // 処理後にOCRドキュメントが残るのが嫌な場合は以下の行を有効化
      // Drive.Files.remove(ocrDoc.id); 
      
      // 8. 処理済みのファイルを別の場所に移動するか、名前に印を付ける
      // ここでは、ファイル名の先頭に「✓」を付けて処理済みとします。
      file.setName("✓" + fileName);
      
    } catch (e) {
      Logger.log(`ファイル ${fileName} の処理中にエラーが発生しました: ${e.toString()}`);
    }
  }
  
  // ログの確認方法: GASエディタ上部の「実行」ボタンの隣にある「実行ログ」
}
