from pathlib import Path
import zipfile
from lxml import etree as E
p=Path(__file__).parent
root=E.fromstring(zipfile.ZipFile(p/'manuscript.docx').read('word/document.xml'));ns={'m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
for i,x in enumerate(root.findall('.//m:oMath',ns)):
 if i in [4,5,6,7,8]: print(i,E.tostring(x,pretty_print=True).decode()[:6500])
