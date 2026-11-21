import pdfMake from 'pdfmake/build/pdfmake';
import fonts from 'pdfmake/build/vfs_fonts';
import {letterBlocks,signatureLine} from './refund-layout.js';

pdfMake.addVirtualFileSystem(fonts);

export function signedPdf(text,signature,lang,name) {
  const signer=signatureLine(name,lang);
  const content=letterBlocks(text).map(({text,alignment,bold,gapAfter})=>({text,alignment,bold,margin:[0,0,0,gapAfter]}));
  content.push({unbreakable:true,columns:[{text:signer.label,width:'auto',margin:[0,6,0,0]},{image:signature,width:100,height:23},{text:signer.name,margin:[0,6,0,0]}],columnGap:5});
  const pdf=pdfMake.createPdf({pageSize:'A4',pageMargins:[55,44,48,44],defaultStyle:{font:'Roboto',fontSize:10.5,lineHeight:1.12},info:{title:lang==='ru'?'Заявление о возврате госпошлины':'Davlat bojini qaytarish uchun ariza'},content});
  return new Promise((resolve,reject)=>{try {pdf.getBlob(resolve);}catch(e){reject(e);}});
}
