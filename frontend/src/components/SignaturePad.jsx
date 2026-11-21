import React, { useLayoutEffect, useRef } from 'react';

const ink = '#111111';
const lineWidth = 2.6;

function draw(ctx, points) {
  if (points.length < 2) return;
  ctx.strokeStyle = ink;
  ctx.lineWidth = lineWidth;
  ctx.lineCap = ctx.lineJoin = 'round';
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length - 1; i++) {
    const a = points[i], b = points[i + 1];
    ctx.quadraticCurveTo(a.x, a.y, (a.x + b.x) / 2, (a.y + b.y) / 2);
  }
  const last = points[points.length - 1];
  ctx.lineTo(last.x, last.y);
  ctx.stroke();
}

// Fit just the ink into the signature line shared by the PDF and Word templates.
function exportInk(strokes) {
  let left = Infinity, top = Infinity, right = -Infinity, bottom = -Infinity;
  for (const stroke of strokes) for (const { x, y } of stroke) {
    left = Math.min(left, x); right = Math.max(right, x);
    top = Math.min(top, y); bottom = Math.max(bottom, y);
  }
  const image = document.createElement('canvas');
  image.width = 532; image.height = 120;
  const scale = Math.min(image.width / (right - left + 6), image.height / (bottom - top + 6));
  const ctx = image.getContext('2d');
  ctx.translate(image.width / 2, image.height / 2);
  ctx.scale(scale, scale);
  ctx.translate(-(left + right) / 2, -(top + bottom) / 2);
  strokes.forEach(stroke => draw(ctx, stroke));
  return image.toDataURL('image/png');
}

export default function SignaturePad({ copy, onSign, disabled }) {
  const pad = useRef(null), strokes = useRef([]), active = useRef(null), frame = useRef(0);
  function paint() {
    frame.current = 0;
    const canvas = pad.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    strokes.current.forEach(stroke => draw(ctx, stroke));
    if (active.current) draw(ctx, active.current.points);
  }
  function repaint() {
    if (!frame.current) frame.current = requestAnimationFrame(paint);
  }
  useLayoutEffect(() => {
    const canvas = pad.current;
    let oldWidth = 0, oldHeight = 0;
    function resize() {
      const w = canvas.clientWidth, h = canvas.clientHeight;
      if (!w || !h) return;
      if (oldWidth && (w !== oldWidth || h !== oldHeight)) {
        const ratio = Math.min(w / oldWidth, h / oldHeight);
        const paths = active.current ? [...strokes.current, active.current.points] : strokes.current;
        for (const path of paths) for (const point of path) {
          point.x = (point.x - oldWidth / 2) * ratio + w / 2;
          point.y = (point.y - oldHeight / 2) * ratio + h / 2;
        }
      }
      oldWidth = w; oldHeight = h;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      canvas.getContext('2d').setTransform(canvas.width / w, 0, 0, canvas.height / h, 0, 0);
      repaint();
    }
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    return () => { observer.disconnect(); cancelAnimationFrame(frame.current); frame.current = 0; };
  }, []);

  function sample(e) {
    const canvas = pad.current, bounds = canvas.getBoundingClientRect();
    const points = active.current.points;
    const events = e.nativeEvent.getCoalescedEvents?.() || [];
    for (const event of [...events, e]) {
      const x = Math.min(canvas.clientWidth, Math.max(0, event.clientX - bounds.left - canvas.clientLeft));
      const y = Math.min(canvas.clientHeight, Math.max(0, event.clientY - bounds.top - canvas.clientTop));
      const last = points[points.length - 1];
      if (!last || Math.hypot(x - last.x, y - last.y) >= 0.5) points.push({ x, y });
    }
    repaint();
  }
  function start(e) {
    if (disabled || active.current || e.button !== 0) return;
    pad.current.setPointerCapture(e.pointerId);
    active.current = { id: e.pointerId, points: [] };
    onSign('');
    sample(e);
  }
  function finish(e, commit) {
    if (active.current?.id !== e.pointerId) return;
    if (commit) {
      sample(e);
      if (active.current.points.length > 1) strokes.current.push(active.current.points);
    }
    active.current = null;
    onSign(strokes.current.length ? exportInk(strokes.current) : '');
    repaint();
  }
  function clear() {
    active.current = null; strokes.current = [];
    onSign(''); repaint();
  }
  return <div className="signature-step"><strong>{copy.sign}</strong><p>{copy.signHint}</p>
    <canvas ref={pad} aria-label={copy.sign}
      onPointerDown={start} onPointerMove={e => { if (active.current?.id === e.pointerId) sample(e); }}
      onPointerUp={e => finish(e, true)} onLostPointerCapture={e => finish(e, false)}
      onPointerCancel={e => finish(e, false)}/>
    <button type="button" className="outline-button" disabled={disabled} onClick={clear}>{copy.clearSign}</button>
  </div>;
}
