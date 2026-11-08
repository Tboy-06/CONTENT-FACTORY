import os, glob, re

files = glob.glob(r'D:\CONTENT-FACTORY\frontend\src\components\copilot\*.tsx')
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('"use client";\n', '')
    content = content.replace('import Link from "next/link";', '')
    content = content.replace('</Link>', '</a>')
    content = re.sub(r'<Link\s+href=([^>]+)>', r'<a href=\1>', content)
    content = content.replace('@/lib/types', '../../types')
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
print('Fixed!')
