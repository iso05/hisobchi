import React from 'react';
import { Pencil, Eye, Upload, Trash2, RotateCcw } from 'lucide-react';
import { SERVICE_ICONS } from '../lib/service-icons.js';

export default function CalculatorTable({calculators,showDeleted,setShowDeleted,busy,onEdit,onAvailability,onPreview,onPublish,renderEditor}) {
  const visible=calculators.filter(c=>c.active||showDeleted);
  return <section className="catalog-section" aria-label="Kalkulyatorlar jadvali"><div className="catalog-toolbar"><h2>Kalkulyatorlar ro‘yxati</h2><label><input type="checkbox" checked={showDeleted} onChange={e=>setShowDeleted(e.target.checked)}/> O‘chirilganlarni ko‘rsatish</label></div>
    <div className="admin-table-scroll"><table className="admin-table builder-table"><thead><tr><th>Kalkulyator</th><th>Xizmat turi</th><th>Holati</th><th>Tahrirlash</th><th>Sinash</th><th>E’lon qilish</th><th>O‘chirish</th></tr></thead><tbody>
    {visible.map(c=>{const Icon=SERVICE_ICONS[c.icon]||SERVICE_ICONS.calculator;const editor=renderEditor?.(c);return <React.Fragment key={c.id}><tr className={c.active?'':'deleted-row'}>
      <td><div className="builder-table-name"><span><Icon size={23}/></span><div><strong>{c.name}</strong><small>{c.dynamic?'Admin yaratgan':'Mavjud kalkulyator'}</small></div></div></td><td>{c.category}</td><td><span className={`catalog-status ${!c.active?'inactive':''}`}>{!c.active?'Yashirilgan':!c.dynamic?'Faol':!c.published?'Qoralama':c.has_changes?'Yangi qoralama':c.rule?'E’lon qilingan':'Rejalashtirilgan'}</span></td>
      <td><button className="table-edit" disabled={busy||!c.active} aria-label={`${c.name}: tahrirlash`} onClick={()=>onEdit(c)}><Pencil size={15}/> Tahrirlash</button></td>
      <td>{c.dynamic?<button className="table-edit" disabled={busy||!c.active} aria-label={`${c.name}: sinab ko‘rish`} onClick={()=>onPreview(c)}><Eye size={15}/> Sinash</button>:<a className="table-edit" href={`/?calculator=${encodeURIComponent(c.id)}`} target="_blank" rel="noreferrer"><Eye size={15}/> Sinash</a>}</td>
      <td>{c.dynamic?<button className="table-edit" disabled={busy||!c.active||!c.tested||!c.has_changes} title={c.tested?'Qoralamani e’lon qilish':'Avval sinab ko‘ring'} onClick={()=>onPublish(c)}><Upload size={15}/> E’lon qilish</button>:<span className="builder-muted">Saytda</span>}</td>
      <td><button className={c.active?'table-delete':'table-edit'} disabled={busy} aria-label={`${c.name}: ${c.active?'o‘chirish':'tiklash'}`} onClick={()=>onAvailability(c,!c.active)}>{c.active?<Trash2 size={15}/>:<RotateCcw size={15}/>} {c.active?'O‘chirish':'Tiklash'}</button></td>
    </tr>{editor&&<tr className="builder-editor-row"><td colSpan={7}>{editor}</td></tr>}</React.Fragment>;})}
    {!visible.length&&<tr><td colSpan={7}>Kalkulyator yo‘q. Yangisini qo‘shing.</td></tr>}
    </tbody></table></div><p className="catalog-note">Qoralama faqat admin uchun. Sinab ko‘rib e’lon qilgach, kalkulyator saytga chiqadi. O‘chirilganini qayta tiklash mumkin.</p>
  </section>;
}
