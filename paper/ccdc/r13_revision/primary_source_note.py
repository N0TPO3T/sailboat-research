from pathlib import Path
p=Path(__file__).parent
with (p/'SOURCE_FOLLOWUP.md').open('a',encoding='utf8') as f:f.write('''
## Verified primary software page
On2026-10-07 the author-maintained MathWorks FileExchange page https://www.mathworks.com/matlabcentral/fileexchange/47981-sailingyachtmodel-zip was retrieved. It identifies Jerome Jouffroy, version1.0.0.0 dated2014-10-02, describes a4DOF Simulink model and explicitly attributes model/notation/parameters to Xiao and Jouffroy2014. Its linked license was retrieved: https://www.mathworks.com/matlabcentral/mlc-downloads/downloads/e5af5a09-4a80-11e4-9553-005056977bd0/7d340fc0-01b1-1f26-4a9f-f5153adf520a/licenses/license.txt . It has copyright2014JeromeJouffroy and permits redistribution subject to retaining notices/disclaimer. This license describes that original distribution; it does not establish permissions for the inherited Python translation or learned checkpoint. Download links currently route through sign-in; no original MATLAB source comparison or executable equivalence was completed. Distinguish verified author software metadata, inherited draft attribution, and unverified port/checkpoint lineage.
''')
