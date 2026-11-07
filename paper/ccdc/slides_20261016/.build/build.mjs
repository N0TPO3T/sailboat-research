import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation, PresentationFile} from '@oai/artifact-tool';
const root='C:/Users/74095/hs/SailBoat/sailboat-routing-v0/paper/ccdc';
const workspaceDir=root+'/slides_20261016';
const source=root+'/track_A_closeout_20261013';
const skill='C:/Users/74095/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations';
const p=Presentation.create({slideSize:{width:1280,height:720}});
const font='Microsoft YaHei';
function text(s,t,x,y,w,h,size=26,color='#243746',bold=false){const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=t;a.text.style={typeface:font,fontSize:size,color,bold};return a;}
function slide(title,notes){const s=p.slides.add();s.background.fill='#FFFFFF';text(s,title,54,30,1172,60,40,'#203747',true);text(s,`${p.slides.items.length} / 6`,1160,672,70,24,16,'#64717B');s.speakerNotes.text=notes+'\n来源：'+source+'/manuscript.md；SUPPLEMENT.md；evidence/episodes.csv。仅使用已有测试，不含新实验。';return s;}
function table(s,values,x,y,w,h,widths){const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,values,columnWidths:widths});t.borders.assign({fill:'#DCE3E8',width:1,style:'solid'});for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){const z=t.getCell(r,c);z.fill=r===0?'#E9EFF4':'#FFFFFF';z.text.style={typeface:font,fontSize:24,color:r===0?'#203747':'#354552',bold:r===0};}return t;}
async function fig(s,name,x,y,w,h){s.images.add({blob:new Uint8Array(await fs.readFile(source+'/figures/'+name)),contentType:'image/png',alt:name,fit:'contain',position:{left:x,top:y,width:w,height:h}});s.speakerNotes.text+='\n原始图：figures/'+name;}
let s=slide('帆船避障测试：24 个任务的总体结果','论文 Table I / II。R 为 reactive，L 为低阶预测监督器，S15 为详细预测监督器；H=60 s，P=15 s，ρ=30 m。全体安全完成要求到达且不侵犯规定安全域。');
text(s,'冻结控制器，同一组 1 km 仿真任务',58,106,1130,42,28);
table(s,[['方法','全部任务','组合压力任务','其余任务'],['R  反应式','19 / 24','3 / 8','16 / 16'],['L  低阶预测','23 / 24','7 / 8','16 / 16'],['S15  详细预测','24 / 24','8 / 8','16 / 16']],58,195,1160,270,[380,260,260,260]);
text(s,'表中数值为安全完成数；S15 相比 L 增加 1 个',58,505,1130,54,29,'#487EAF',true);
text(s,'单个低速恒速目标，已知静态地图，无观测噪声\n计算期间物理时间暂停，结果不代表实时部署性能',58,583,1100,74,22,'#64717B');
s=slide('航迹案例：S15 增加一个安全完成','论文 Fig.3，r12new_mixed_pressure_1。R 在 392 s 提前退出；L 在566 s到达但侵犯缓冲边界。S15在519 s安全到达。260 s选取新参考，261 s交付，262 s首次物理差异。不能把整个航程效果归因于单个选择。');
await fig(s,'figure5_rescue.png',44,100,630,550);
table(s,[['方法','最小裕度 / m'],['R','−0.162'],['L','−1.115'],['S15','+42.096']],720,142,500,232,[225,275]);
text(s,'L：566 s 到达，缓冲区越界\nS15：519 s 安全到达',720,414,510,102,28);
text(s,'裕度 < 0 表示侵犯安全缓冲区\n不等同于实体船体碰撞',720,558,510,80,23,'#64717B');
s=slide('航迹反例：详细预测增加 308 秒航时','论文 Fig.4。第四个 endpoint confirmation 实例。R 与 L 的轨迹重合，均279 s安全到达；S15 587 s。保留最坏航时反例，不能只展示有利任务。');
await fig(s,'figure6_adverse.png',44,100,630,550);
table(s,[['方法','安全到达时间 / s'],['R','279'],['L','279'],['S15','587']],720,142,500,232,[225,275]);
text(s,'+308 s',720,410,500,80,58,'#B47E46',true);
text(s,'三个方法均安全完成\n额外绕行带来明显航时成本',720,520,510,100,28);
s=slide('共同安全任务：航时没有整体改善','主文 V-A。confirmation 按 scene_id 配对 simple 和 sampled，仅两者 success=True。23对总差161 s。等航时不代表相同航迹。剔除不安全任务仅用于航时比较，安全计数保留所有24任务。');
text(s,'S15 − L，仅统计两者均安全完成的 23 个任务',58,108,1150,45,28);
table(s,[['比较','任务数'],['S15 更快','5'],['航时相同','13'],['S15 更慢','5']],58,202,560,286,[390,170]);
table(s,[['统计量','航时差 / s'],['均值','+7'],['中位数','0'],['范围','−136 至 +308']],670,202,550,286,[270,280]);
text(s,'同航时不等于同航迹',58,545,1100,48,30,'#487EAF',true);
text(s,'不安全到达或提前退出不作为航时改善',58,610,1100,40,24,'#64717B');
s=slide('固定协议预测：局部更准，仍存在反例','论文 Fig.6，Supplement S7。6个开发状态×2协议，不是12个独立场景。三方共同时间区间10条60s、2条58s。分支最大位置误差的中位数S15 1.104 m、L53.818 m。详细预测最大误差106.064m；同状态重复协议不能当独立失败。');
await fig(s,'figure4_prediction.png',44,105,745,530);
text(s,'分支最大位置误差的中位数',810,160,410,70,25);
text(s,'S15    1.104 m\nL       53.818 m',810,252,410,120,32,'#487EAF',true);
text(s,'详细预测仍有\n106.064 m 误差反例',810,427,410,110,29,'#B47E46',true);
text(s,'6 个选定开发状态\n不构成普适精度或安全保证',810,570,410,80,22,'#64717B');
s=slide('计算代价与当前结论','论文 Table I、V-D及补充S4/S14。Episode CPU总量分别270.677134051、378.444522666、2133.232056205s，覆盖各24任务。planning core profile三状态各三重复，17.009144与0.067051s，不含加载；早返导致候选数可不同。两类时间不可混为同一工作量指标。');
table(s,[['方法','24 个任务 CPU 总量 / s'],['R','270.68'],['L','378.44'],['S15','2133.23']],58,140,1160,240,[430,730]);
text(s,'规划核心耗时中位数：L  0.067 s，S15  17.009 s',58,420,1150,65,30,'#487EAF',true);
text(s,'详细预测增加一个安全完成，同时增加计算与部分航时成本',58,520,1150,66,29);
text(s,'当前结果支持取舍分析，尚未证明额外成本通常值得\n物理时间暂停；未验证实时部署与在线预测器切换',58,600,1120,64,22,'#64717B');
await (await PresentationFile.exportPptx(p)).save(workspaceDir+'/.build/candidate.pptx');
for(let i=0;i<p.slides.items.length;i++){const b=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(workspaceDir+`/.build/slide-${i+1}.png`,new Uint8Array(await b.arrayBuffer()));}
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const result=await finalizePresentation({workspaceDir,candidatePath:workspaceDir+'/.build/candidate.pptx',finalPath:workspaceDir+'/output/SailBoat_实验结果简报.pptx',pythonExecutable:'C:/Users/74095/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...[1,2,3,4,6].flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:6,requiredNativeTableOwnerSlides:[1,2,3,4,6],fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:workspaceDir+'/.build/validation.json'});
console.log(JSON.stringify(result));
