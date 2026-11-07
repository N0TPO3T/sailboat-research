from pathlib import Path
import json
P=Path(__file__).resolve().parent
data=json.loads((P/'evidence/fixed_branches.json').read_text())
assert len(data)==12 and all(x['actual']['prefix_state_max_error']==0 for x in data)
assert sum(x['selected'] for x in data)==6
assert all(x['selected15s_position_parity']==0 for x in data if x['selected'])
assert all(x['selected15s_position_parity'] is None for x in data if not x['selected'])
s=(P/'manuscript.md').read_text(encoding='utf8')
old='All twelve fixed real branches from six snapshots reproduce their full physical prefixes and the selected first 15 s exactly.'
new='All twelve fixed real branches from six snapshots reproduce their full physical prefixes exactly. The six branches using the actually selected protocols also reproduce the following 15 s of positions from the original executions exactly; the six alternative branches have no corresponding selected-prefix check.'
assert old in s
s=s.replace(old,new)
s=s.replace('after exact physical-prefix and selected-first-15-s reproduction.','after exact physical-prefix reproduction; the six actually selected branches also reproduce their original first 15 s of positions.')
(P/'manuscript.md').write_text(s,encoding='utf8')
supp=(P/'SUPPLEMENT.md').read_text(encoding='utf8')
supp=supp.replace("The selected branch's first 15 seconds of positions must also match its source.","For each of the six actually selected branches, the first 15 seconds of positions must also match its source. This check does not apply to the six alternative branches.")
supp=supp.replace('Full physical prefixes and selected first 15 seconds must reproduce the original trajectory before their branch comparisons are accepted.','All twelve branches must reproduce the original physical prefixes. The six actually selected branches must additionally reproduce the first 15 seconds of positions from their original continuations; the alternatives are not subject to that selected-continuation parity check.')
(P/'SUPPLEMENT.md').write_text(supp,encoding='utf8')
print('Separated twelve physical-prefix checks from six selected-continuation checks.')
