# Copyright (C) 2024 pipin68k
# based on code by https://github.com/ymndoseijin/pyaozora copyright (C) 2023 ymndoseijin 
# License: GPL-3.0 license

import os
import sys
import re
import argparse
from dataclasses import dataclass
import requests_cache
from bs4 import BeautifulSoup
from ebooklib import epub

def get_gaiji(s):
    #<img src="../../../gaiji/1-88/1-88-22.png" alt="※(「王＋膠のつくり」、第3水準1-88-22)" class="gaiji" />
    m = re.search(r'<img .+第(\d)水準\d-(\d{1,2})-(\d{1,2}).+?"/>', s)
    if m:
        key = f'{m[1]}-{int(m[2])+32:2X}{int(m[3])+32:2X}'
        return gaiji_table.get(key, s)
    #<img alt="※(二の字点、1-2-22)" class="gaiji" src="../../../gaiji/1-02/1-02-22.png"/>
    m = re.search(r'<img alt.+\d-(\d{1,2})-(\d{1,2}).+?"/>', s)
    if m:
        key = f'3-{int(m[1])+32:2X}{int(m[2])+32:2X}'
        return gaiji_table.get(key, s)
    #※<span class="notes">［＃丸印、U+329E、36-10］</span>
    m = re.search(r'U\+(\w{4})', s)
    if m:
        return chr(int(m[1], 16))
    # unknown format
    return s

def sub_gaiji(text):
    buf = re.sub(r'<img .+?"/>', lambda m: get_gaiji(m[0]), text)
    return re.sub(r'※<span .+?span>', lambda m: get_gaiji(m[0]), buf)

@dataclass
class BookInfo:
    title: str
    creator: str
    publisher: str
    main_text: str
    biblio_info: str

def content_to_bookinfo(content):
    soup = BeautifulSoup(content,"html.parser")

    # 書誌情報を取得
    if soup.find('meta', attrs={'name': 'DC.Title'}):
        title   = soup.find('meta', attrs={'name': 'DC.Title'}).get('content')
    else:
        title   = soup.find('h1', class_="title").get_text()
    creator     = soup.find('meta', attrs={'name': 'DC.Creator'}).get('content') 
    publisher   = soup.find('meta', attrs={'name': 'DC.Publisher'}).get('content') 
    main_text   = soup.find("div", class_="main_text")
    biblio_info = soup.find("div", class_="bibliographical_information")

    return BookInfo(title,creator,publisher,main_text,biblio_info)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog = 'pyaozora',
                    description = 'aozoraのXHTMLリンクからEPUB3に')
    
    parser.add_argument('url', help="青空文庫のXHTMLのURL")
    parser.add_argument('--tategaki', '-t', action="store_true", help="縦書きにする")
    parser.add_argument('--output', '-o', help="ファイルに出力")
    args = parser.parse_args()

    # url確認
    pattern = "https:\/\/www.aozora.gr.jp\/cards\/\d+\/files\/(\d+)_\d+.html"
    match = re.match(pattern, args.url) 
    if not match:
        sys.exit('青空文庫のXHTMLのURLを指定してください。')

    # urlからepub用のidを生成
    id = "aozora-card-no." + match.group(1)

    # 外字ファイルの確認とロード
    gaiji = 'jisx0213-2004-std.txt'
    if not os.path.isfile(gaiji):
        sys.exit('外字ファイルが見つかりません。')
    with open(gaiji) as f:
        ms = (re.match(r'(\d-\w{4})\s+U\+(\w{4})', l) for l in f if l[0] != '#')
        gaiji_table = {m[1]: chr(int(m[2], 16)) for m in ms if m}

    # キャッシュを aozora_cache.sqlite に保存
    session = requests_cache.CachedSession('aozora_cache')
    response = session.get(args.url)
    response.encoding = response.apparent_encoding 
    print(f'from_cache:{response.from_cache}, status_code: {response.status_code}, url: {args.url}') 

    bookinfo = content_to_bookinfo(response.content)

    # 電子書籍作成
    book = epub.EpubBook()

    # 必須項目の設定
    book.set_identifier(id)
    book.set_title(bookinfo.title)
    book.set_language('ja')

    # オプション項目の設定
    book.add_author(bookinfo.creator)
    book.add_metadata('DC', 'publisher', bookinfo.publisher)
    if args.tategaki:
      book.set_direction("rtl")

    # 縦書きスタイル
    verticalstyle = '''
html {
    -epub-writing-mode:   vertical-rl;
    -webkit-writing-mode: vertical-rl;
}
'''
    vertical_css = epub.EpubItem(file_name="style-vertical.css", media_type="text/css", content=verticalstyle)
    book.add_item(vertical_css)

    # 表紙
    cover = epub.EpubHtml(title='表紙', file_name='cover.xhtml', lang='ja')
    cover.set_content(f'<h1>{bookinfo.title}</h1><h2>{bookinfo.creator}</h2>')
    if args.tategaki:
      cover.add_item(vertical_css)

    # 本文
    c1 = epub.EpubHtml(title=bookinfo.title, file_name='chapter1.xhtml', lang='ja')
    converted = []
    lines = str(bookinfo.main_text).splitlines()
    for line in lines:
        converted.append(sub_gaiji(line))
    convertedjoin = ''.join(converted)
    c1.set_content(f'<body>{convertedjoin}</body>')
    if args.tategaki:
      c1.add_item(vertical_css)

    # 奥付
    biblio = epub.EpubHtml(title='奥付', file_name='biblio.xhtml', lang='ja')
    biblio.set_content(f'<body>{bookinfo.biblio_info}</body>')

    # 各章を追加
    book.add_item(cover)
    book.add_item(c1)
    book.add_item(biblio)
    
    # 目次の構成
    toc=[]  
    toc.append(epub.Link('cover.xhtml', '表紙', 'cover'))
    toc.append(epub.Link('chapter1.xhtml', bookinfo.title, 'chapter1'))
    toc.append(epub.Link('biblio.xhtml', '奥付', 'biblio'))
    book.toc = tuple(toc)

    # ePub2とePub3の目次を追加
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 構造の設定
    book.spine = [cover, c1, biblio]

    # create epub file
    if args.output is None:
        epub.write_epub(f'{bookinfo.title}.epub', book, {})
    else:
        epub.write_epub(f'{args.output}', book, {})
