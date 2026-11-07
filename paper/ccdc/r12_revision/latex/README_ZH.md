# R12 LaTeX 可编辑版

直接编辑 `main.tex`。这是完整英文第二稿的LaTeX转换版，研究内容与上一级 `manuscript.md` 一致。公式、伪代码、表格和参考文献均为可编辑源码；图表沿用真实结果的PDF矢量文件。旧Word/PDF没有覆盖。

## Overleaf

1. 上传整个 `R12_LaTeX.zip` 创建项目。
2. 将主文件设为 `main.tex`，编译器选择 pdfLaTeX。
3. 编译两次，使引用与交叉引用更新。

## 本地

在已有TeX发行版的环境中，于本目录运行：

```sh
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

参考文献用 `thebibliography` 与 `\bibitem`，无需BibTeX；新增引用时使用 `\cite{ref...}`。图表与公式均带 `\label`，正文使用交叉引用，便于增删修改。

`IEEEtran.cls`逐字节来自你提供的 `conference-latex-template.zip`；使用原模板的 `conference` 选项，未为追求页数改字号、页边距。`official_template_original.tex`仅保留作对照，不是主文件。

## 验证状态

已检查全部正文块转换、5组公式、3张表、5个图文件、8条引用、交叉引用及环境/括号配对。内置编译器实际尝试失败，错误为“Unable to find standard directories for platform”，不是已确认的源文件编译错误。当前电脑及项目服务器未发现可用的外部LaTeX编译器。因此**此包没有经过成功编译，也不包含伪称由LaTeX生成的PDF**。现有7页PDF来自Word，其页数不能直接套给LaTeX版；请在正常TeX环境中编译后检查浮动图表、页数和版面。

今后直接修改main.tex即可；不会自动同步回Markdown或Word。作者、单位、资助及资产许可仍沿用R12的待确认状态。
