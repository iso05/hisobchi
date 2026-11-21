export function letterBlocks(text) {
  const blocks=text.trim().split(/\r?\n\s*\r?\n/);
  const titleIndex=blocks.findIndex(block=>/^(ARIZA|ЗАЯВЛЕНИЕ)$/i.test(block.trim()));
  return blocks.map((text,i)=>({
    text, alignment:i===0?'right':titleIndex>=0 && (i===titleIndex || i===titleIndex+1)?'center':'left',
    bold:i===titleIndex, gapAfter:i===titleIndex?2:6,
  }));
}

export function signatureLine(name,lang) {
  const [surname,...given]=name.trim().split(/\s+/);
  const initials=given.map(n=>Array.from(n)[0]+'.').join('');
  return {label:lang==='ru'?'Подпись заявителя:':'Arizachining imzosi:', name:[initials,surname].filter(Boolean).join(' ')};
}
