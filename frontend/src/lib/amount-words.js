const uzOnes = ['', 'bir', 'ikki', 'uch', 'to‘rt', 'besh', 'olti', 'yetti', 'sakkiz', 'to‘qqiz'];
const uzTens = ['', 'o‘n', 'yigirma', 'o‘ttiz', 'qirq', 'ellik', 'oltmish', 'yetmish', 'sakson', 'to‘qson'];
const ruOnes = ['', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять'];
const teens = ['десять','одиннадцать','двенадцать','тринадцать','четырнадцать','пятнадцать','шестнадцать','семнадцать','восемнадцать','девятнадцать'];
const ruTens = ['','','двадцать','тридцать','сорок','пятьдесят','шестьдесят','семьдесят','восемьдесят','девяносто'];
const hundreds = ['','сто','двести','триста','четыреста','пятьсот','шестьсот','семьсот','восемьсот','девятьсот'];
const scales = [[],['тысяча','тысячи','тысяч'],['миллион','миллиона','миллионов'],['миллиард','миллиарда','миллиардов'],['триллион','триллиона','триллионов']];
function plural(n) {
  if (n%100>=11 && n%100<=14) return 2;
  if (n%10===1) return 0;
  return n%10>=2 && n%10<=4 ? 1 : 2;
}
export function amountWords(amount, lang) {
  if (!Number.isSafeInteger(amount) || amount<0 || amount>1e12) throw Error('Invalid amount');
  const ru=lang==='ru';
  if (!amount) return ru?'ноль':'nol';
  const groups=[];
  for(let scale=0, rest=amount;rest;scale++,rest=Math.floor(rest/1000)) {
    const n=rest%1000;
    if (!n) continue;
    const h=Math.floor(n/100),t=Math.floor(n/10)%10,u=n%10;
    let parts;
    if (ru) {
      const one=scale===1 && u===1?'одна':scale===1 && u===2?'две':ruOnes[u];
      parts=[hundreds[h],...(t===1?[teens[u]]:[ruTens[t],one]), scales[scale][plural(n)]];
    } else parts=[h?uzOnes[h]+' yuz':'',uzTens[t],uzOnes[u],['','ming','million','milliard','trillion'][scale]];
    groups.unshift(parts.filter(Boolean).join(' '));
  }
  return groups.join(' ');
}
