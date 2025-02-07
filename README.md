# pyaozora

青空文庫のXHTMLをEPUB3に変換

## 主な変更点

* JIS X0213 対応表を利用した外字対応
* 青空文庫上で目次がない図書への対応
* 青空文庫へのアクセスをキャッシュ化
* ePubのスタイルをシンプルに
* ePubの目次を変換しない

## セットアップ

「プロジェクトX0213」から JIS X0213 対応表 を取得してください。

```ps1
Invoke-WebRequest -Uri http://x0213.org/codetable/jisx0213-2004-std.txt -OutFile 'jisx0213-2004-std.txt'
```

あとは、pip だけでセットアップできます。dataclass を使っているので、Python 3.7以降。

```
pip install -r .\requirements.txt
```

## 使い方

`-p`が縦書きの設定です。 デフォルトは横書き。
`-o`プログラムの出力ファイルの設定です。デフォルトは `$題名.epub` です。

```
python .\pyaozora -p https://www.aozora.gr.jp/cards/000096/files/2381_13352.html
```

## 参照サイト

* [青空文庫](https://www.aozora.gr.jp/)	
* [プロジェクトX0213](https://x0213.org/)	
* [【Python CLI】青空文庫のXHTML本からEPUBに変換するツールを作った](https://qiita.com/ymndoseijin/items/88548a90c0ff06287f7c)
* [青空文庫の外字をPythonでUnicodeに置換](https://qiita.com/kichiki/items/bb65f7b57e09789a05ce)
