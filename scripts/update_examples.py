from pathlib import Path
path=Path(__file__).resolve().parents[1]/'frontend/src/App.jsx'
text=path.read_text(encoding='utf-8')
start="examples.filter(e => (isDemo || e.icon === CarFront) && (!selected || selected === 'court' && e.icon === Scale || selected === 'notary_car' && e.icon === CarFront || selected === 'vehicle_power' && e.icon === FilePenLine))"
assert start in text
text=text.replace(start,'shownExamples')
path.write_text(text,encoding='utf-8')
