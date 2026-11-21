import json
import re
import sys
from html import unescape
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parents[1] / 'docs/sources'
source = (root / 'davlat-boji.html').read_text(encoding='utf-8')
pattern = re.compile(r'<(?:a|div|tr|td|span)\b[^>]*\bid=["\'](-?\d+)', re.I)
for term in ['avtomototransport vositalari uchun', 'mulkiy xususiyatga ega daʼvo', 'bitta ixtiroga', 'koʻchmas mol-mulkni boshqa shaxsga', 'merosga boʻlgan huquq', '23-modda.']:
    location = source.find(term)
    anchors = list(pattern.finditer(source[:location]))
    print(term, [(m.group(1), location-m.start()) for m in anchors[-3:]])
    if location > 0:
        print(source[max(0,location-170):location+130])

# Keep a searchable text copy for checking surrounding clauses without browser truncation.
clean = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', source, flags=re.S|re.I)
clean = re.sub(r'</(?:p|tr|div)>', '\n', clean)
clean = unescape(re.sub('<[^>]+>', ' ', clean))
clean = '\n'.join(re.sub(r'\s+', ' ', line).strip() for line in clean.splitlines() if line.strip())
(root/'davlat-boji.txt').write_text(clean, encoding='utf-8')
