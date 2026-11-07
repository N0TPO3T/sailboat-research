import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL,fileURLToPath} from 'node:url';
const dir=path.dirname(fileURLToPath(import.meta.url));
const req=createRequire('C:/Users/74095/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/_entry.cjs');
const {marked}=await import(pathToFileURL(req.resolve('marked')).href);
const main=await fs.readFile(path.join(dir,'实验全说明.md'),'utf8');
const appendix=await fs.readFile(path.join(dir,'附录_逐场景结果.md'),'utf8');
let body=marked.parse(main+'\n\n---\n\n'+appendix);
body=body.replaceAll('href="附录_逐场景结果.md"','href="#appendix"');
body=body.replace(/<h1>附录：/,'<h1 id="appendix">附录：');
for(const m of [...body.matchAll(/src="(figures\/[^" ]+)"/g)]){
 const b=await fs.readFile(path.join(dir,m[1]));body=body.replaceAll(`src="${m[1]}"`,`src="data:image/png;base64,${b.toString('base64')}"`);
}
const links=[];let id=0;
body=body.replace(/<h2>(.*?)<\/h2>/g,(_,title)=>{const anchor='section-'+(++id);links.push(`<a href="#${anchor}">${title}</a>`);return `<h2 id="${anchor}">${title}</h2>`;});
const css=`*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f4f6f8;color:#243442;font:17px/1.85 'Microsoft YaHei','Segoe UI',sans-serif}nav{position:fixed;left:0;top:0;width:270px;height:100vh;overflow:auto;padding:25px 19px;background:#e9eff4;border-right:1px solid #d5dfe8}nav strong{display:block;color:#1d435d;font-size:19px;margin-bottom:18px}nav a{display:block;color:#345b74;text-decoration:none;font-size:13px;line-height:1.7;margin:9px 0}main{max-width:1130px;margin-left:290px;padding:48px 60px 100px;background:white}h1{font-size:31px;line-height:1.5;color:#163e59;margin:0 0 28px}h2{font-size:25px;line-height:1.5;color:#163e59;border-top:2px solid #cbdce7;padding-top:28px;margin-top:54px;scroll-margin-top:24px}h3{font-size:20px;margin-top:30px}p{margin:14px 0}a{color:#176c9a;overflow-wrap:anywhere}strong{color:#203e52}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.65;margin:24px 0;table-layout:auto}th{background:#eaf1f6;color:#25465b}td,th{padding:10px 11px;border:1px solid #ced9e2;text-align:left;overflow-wrap:anywhere}tbody tr:nth-child(even){background:#f7f9fb}pre{background:#f1f5f8;padding:20px;overflow:auto;font:14px/1.8 Consolas,'Microsoft YaHei',monospace;border-left:3px solid #7197b0}code{font-family:Consolas,'Microsoft YaHei',monospace;overflow-wrap:anywhere}p>img{display:block;width:auto;max-width:100%;max-height:950px;margin:30px auto;border:1px solid #e4e9ed}blockquote{border-left:3px solid #7197b0;padding:8px 20px;margin:20px 0;background:#f2f6f9}@media(max-width:1000px){nav{position:static;width:100%;height:auto;max-height:260px}main{margin:0;padding:30px 20px}table{font-size:12px}td,th{padding:7px}}@media print{nav{display:none}main{margin:0;max-width:none;padding:0}body{background:white;font-size:10pt}h2{break-before:page}table{font-size:8pt}tr,img{break-inside:avoid}a{color:inherit;text-decoration:none}}`;
await fs.writeFile(path.join(dir,'实验全说明.html'),'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>帆船避障实验全说明</title><style>'+css+'</style><nav><strong>实验全说明</strong><span>2026-10-22 · 原实验记录整理</span>'+links.join('')+'</nav><main>'+body+'</main></html>');
console.log(JSON.stringify({sections:id,mainCharacters:main.length,html:'实验全说明.html',embeddedFigureCount:(body.match(/src="data:image/g)||[]).length}));
