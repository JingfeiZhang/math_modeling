# -*- coding: utf-8 -*-
"""从 .docx 抽取纯文本（无需安装 python-docx）：docx 本质是 zip+XML。"""
import sys, zipfile, re

def extract(path):
    try:
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.startswith('word/') and n.endswith('.xml')]
            # 优先 document.xml，其次 header/footer
            order = ['word/document.xml'] + [n for n in names if n != 'word/document.xml']
            out = []
            for n in order:
                if n not in z.namelist():
                    continue
                xml = z.read(n).decode('utf-8', errors='ignore')
                # 段落/换行标记转为换行；表格单元格加制表符
                xml = re.sub(r'<w:p[ >]', '\n<w:p ', xml)
                xml = xml.replace('<w:br/>', '\n').replace('<w:tab/>', '\t')
                xml = xml.replace('</w:tc>', '\t')
                # 去掉所有 XML 标签，只留文本
                para = re.sub(r'<[^>]+>', '', xml)
                # 解码常见实体
                for a, b in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                             ('&quot;', '"'), ('&apos;', "'")]:
                    para = para.replace(a, b)
                if para.strip():
                    out.append(para)
            text = '\n'.join(out)
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text
    except Exception as e:
        return f'[ERROR] {path}: {e}'

if __name__ == '__main__':
    for p in sys.argv[1:]:
        print('=' * 70)
        print('FILE:', p)
        print('=' * 70)
        print(extract(p))
        print()
