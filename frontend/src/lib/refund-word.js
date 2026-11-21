import { Document, ImageRun, Packer, Paragraph, TextRun } from 'docx';

import {letterBlocks,signatureLine} from './refund-layout.js';

export async function signedLetter(text, signature, locale, name) {
  const signer=signatureLine(name,locale);
  const paragraphs=letterBlocks(text).map(({text,alignment,bold,gapAfter})=>new Paragraph({
    alignment,spacing:{after:gapAfter*20,line:240},
    children:text.split(/\r?\n/).map((line,i)=>new TextRun({text:line,bold,break:i?1:0})),
  }));
  const data = Uint8Array.from(atob(signature.split(',')[1]), c => c.charCodeAt(0));
  paragraphs.push(new Paragraph({children:[
    new TextRun({text:signer.label+'  '}),
    new ImageRun({type:'png', data, transformation:{width:133,height:30}}),
    new TextRun({text:'  '+signer.name}),
  ]}));
  return Packer.toBlob(new Document({
    creator:'Hisobchi', title:locale==='ru'?'Заявление о возврате госпошлины':'Davlat bojini qaytarish uchun ariza',
    styles:{default:{document:{run:{font:'Times New Roman',size:22}}}},
    sections:[{properties:{page:{size:{width:11906,height:16838},margin:{top:880,bottom:880,left:1100,right:960}}},children:paragraphs}],
  }));
}
