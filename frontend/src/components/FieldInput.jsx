import React, { useLayoutEffect, useRef, useState } from 'react';

function group(value) {
  const [integer, fraction] = value.split('.');
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return fraction === undefined ? grouped : grouped + '.' + fraction;
}

function NumericInput({ value, onValueChange, min, max, step = 1, ...props }) {
  const input = useRef(null);
  const cursor = useRef(null);
  const [draft, setDraft] = useState('');
  const raw = typeof value === 'number' && draft !== '' && Object.is(Number(draft), value)
    ? draft : String(value ?? '');
  const display = group(raw);

  // Keep the browser's range and step checks while displaying grouping commas.
  useLayoutEffect(() => {
    const probe = document.createElement('input');
    probe.type = 'number';
    if (min != null) probe.min = min;
    if (max != null && Number.isFinite(Number(max))) probe.max = max;
    probe.step = step;
    probe.value = raw;
    input.current.setCustomValidity(raw && !probe.value ? probe.validationMessage || '0–9' : probe.validationMessage);
  }, [raw, min, max, step]);

  useLayoutEffect(() => {
    if (cursor.current === null) return;
    let offset = 0, count = 0;
    while (offset < display.length && count < cursor.current) {
      if (display[offset++] !== ',') count++;
    }
    input.current.setSelectionRange(offset, offset);
    cursor.current = null;
  });

  function update(text, position) {
    const clean = part => part.replace(/[,\s]/g, '');
    const next = clean(text);
    if (!/^-?\d*(?:\.\d*)?$/.test(next)) return;
    cursor.current = clean(text.slice(0, position)).length;
    setDraft(next);
    onValueChange(next);
  }

  function paste(event) {
    event.preventDefault();
    const element = event.currentTarget;
    let digits = event.clipboardData.getData('text').trim().replace(/\s/g, '');
    if (digits.includes(',') && !/^-?\d{1,3}(,\d{3})+(\.\d+)?$/.test(digits)) {
      // Decimal-comma input is common on Russian keyboards.
      if (!/^-?\d+,\d+$/.test(digits)) return;
      digits = digits.replace(',', '.');
    }
    const start = element.selectionStart;
    update(display.slice(0,start) + digits + display.slice(element.selectionEnd), start + digits.length);
  }

  function skipSeparator(event) {
    const element = event.currentTarget;
    const position = element.selectionStart;
    if (position !== element.selectionEnd) return;
    if (event.key === 'Backspace' && display[position - 1] === ',') {
      element.setSelectionRange(Math.max(0, position - 2), position);
    } else if (event.key === 'Delete' && display[position] === ',') {
      element.setSelectionRange(position, Math.min(display.length, position + 2));
    }
  }
  return <input {...props} ref={input} type="text" inputMode={Number(step) === 1 && Number(min) >= 0 ? 'numeric' : 'decimal'}
    value={display} onChange={event => update(event.target.value, event.target.selectionStart)} onPaste={paste} onKeyDown={skipSeparator} />;
}

export default function FieldInput({ type, onValueChange, ...props }) {
  if (type === 'number') return <NumericInput {...props} onValueChange={onValueChange} />;
  return <input {...props} type={type} onChange={event => onValueChange(event.target.value)} />;
}
