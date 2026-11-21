import React, { useRef } from 'react';

export default function SignaturePad({ copy, onSign, disabled }) {
  const pad = useRef(null);
  const pen = useRef(null);
  function point(e) {
    const canvas = pad.current;
    const bounds = canvas.getBoundingClientRect();
    return [(e.clientX-bounds.left)*canvas.width/bounds.width, (e.clientY-bounds.top)*canvas.height/bounds.height];
  }
  function start(e) {
    if (disabled || pen.current || e.button !== 0) return;
    const canvas = pad.current;
    canvas.setPointerCapture(e.pointerId);
    pen.current = { id:e.pointerId, last:point(e), moved:false };
  }
  function move(e) {
    const stroke = pen.current;
    if (!stroke || stroke.id !== e.pointerId) return;
    const pos = point(e);
    if (Math.hypot(pos[0]-stroke.last[0],pos[1]-stroke.last[1]) < 2) return;
    if (!stroke.moved) onSign('');
    const ctx = pad.current.getContext('2d');
    ctx.strokeStyle = '#172c42'; ctx.lineWidth = 3.4; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(...stroke.last); ctx.lineTo(...pos); ctx.stroke();
    stroke.last=pos; stroke.moved=true;
  }
  function finish(e) {
    if (pen.current?.id !== e.pointerId) return;
    if (pen.current.moved) onSign(pad.current.toDataURL('image/png'));
    pen.current=null;
  }
  function clear() {
    pen.current=null;
    pad.current.getContext('2d').clearRect(0,0,pad.current.width,pad.current.height);
    onSign('');
  }
  return <div className="signature-step"><strong>{copy.sign}</strong><p>{copy.signHint}</p>
    <canvas ref={pad} width="800" height="180" aria-label={copy.sign}
      onPointerDown={start} onPointerMove={move} onPointerUp={finish} onLostPointerCapture={finish}
      onPointerCancel={clear}/>
    <button type="button" className="outline-button" disabled={disabled} onClick={clear}>{copy.clearSign}</button>
  </div>;
}
