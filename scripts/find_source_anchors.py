from html.parser import HTMLParser
from pathlib import Path
import sys,re
sys.path.insert(0,'backend')
from app.catalog import CATALOG
class P(HTMLParser):
 def __init__(self): super().__init__(); self.stack=[]; self.rows=[]
 def handle_starttag(self,t,a):
  if t in {'meta','link','br','img','input','hr','wbr','source','area','base','embed','param','track','col'}: return
  self.stack.append((t,dict(a).get('id'),[]))
 def handle_data(self,d):
  for _,i,parts in self.stack:
   if i: parts.append(d)
 def handle_endtag(self,t):
  for n in range(len(self.stack)-1,-1,-1):
   if self.stack[n][0]==t:
    for _,i,parts in self.stack[n:]:
     if i:self.rows.append((i,re.sub(r'\s+',' ',''.join(parts))))
    del self.stack[n:]; break
ps={}
for name,key in [('davlat-boji','-4680944'),('elektron-ishonchnoma','-6672128')]:
 p=P();p.feed(Path(f'docs/sources/{name}.html').read_text(encoding='utf-8')); ps[key]=p
for item in CATALOG:
 for src in item['sources']:
  key=src['url'].split('/docs/')[1].split('?')[0]
  rows=[(i,txt) for i,txt in ps[key].rows if src['find_text'] in txt and re.fullmatch(r'-?\d+',i)]
  found=min(rows,key=lambda x:len(x[1])) if rows else None
  print(src['article'], found[0] if found else 'NONE')
