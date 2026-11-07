from pathlib import Path
p=Path(__file__).parent
f=p/'convert_to_latex.py';s=f.read_text(encoding='utf8');s=s.replace("+'}\\n\\\\[2pt]')", "+'}'+chr(92)*2+'[2pt]\\n')")
f.write_text(s,encoding='utf8')
print([x for x in s.splitlines() if 'begin{quote}' in x])
