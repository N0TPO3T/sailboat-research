# 完整稿 LaTeX 源文件包

内容起点：`track_A_closeout_20261013` 的完整正文和补充材料。打包日期：2026-10-30。本次仅转换排版与打包，不更新算法、实验、数字或科学结论；不回退到 R13 旧正文。

## 打开和编译

将整个压缩包解压到任意新目录，或上传到 Overleaf。在项目根目录选择 `main.tex` 为主文件，编译器选 pdfLaTeX。补充材料独立选择 `supplement.tex` 编译。

本机有 TeX Live 或 MiKTeX 时，可执行：

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error supplement.tex
```

没有 latexmk 时，分别对两个文件执行两遍 `pdflatex`。正文参考文献直接写在 `main.tex` 的 `thebibliography` 环境中，因此不需要 `.bib` 文件或 BibTeX。Windows 可运行 `build.ps1`。

所需标准宏包：fontenc、inputenc、cite、amsmath、amssymb、amsfonts、graphicx、textcomp、array、url、geometry、longtable。`IEEEtran.cls` 已随附，来自项目此前使用的模板，保留原许可证头；其随附不代表已重新认证 CCDC 2027 格式要求。

## 文件位置

- `main.tex`：可直接编辑的完整正文，含作者、公式、算法、三张表、六幅图和十条参考文献。
- `supplement.tex`：完整 S1–S14 补充材料，四张表单独编号 S1–S4。其 Fig. 1–6 和文献 [8]/[10] 指向正文。
- `figures/`：图的矢量 PDF、SVG 和 PNG，以及原有图脚本。正文编译使用 PDF。
- `source_markdown/`：本次转换所依据的原始正文与补充材料，逐字保留，便于内容核对。
- `reference_word_edition/`：原有 Word 文件和由 Word 导出的 PDF。这里的 PDF 不是本次 LaTeX 编译结果，排版页数可能不同。
- `evidence/`、`provenance/`：原有轻量证据与来源记录。
- `check_paired_times.py`：仅核对已有 CSV，不运行新仿真；在解压目录执行 `python check_paired_times.py`。
- `plot_data.json`、`plot_figures.py`、`draw_interface.py`：已有图数据和绘图入口。图再生成需要 `requirements-editorial.txt` 中的依赖，LaTeX 编译不需要 Python。
- `CONTENTS_SHA256.json`：本包文件校验清单。
- `BUILD_STATUS.json`：本次编译检查实际状态；以该文件为准，不将源文件检查等同于编译成功。

## 范围和待确认项

这是论文源文件与轻量证据包，不是完整仿真恢复包。不包含完整模型权重或全部原始轨迹。补充材料中指向 `R13_REPRODUCTION_internal.zip` 的说明仍有效，该恢复包并未随附。本文所有图片、文献和编译文件均从本包内部读取，不依赖作者机器上的目录。

作者顺序与单位保持原稿。尚缺的通讯作者、邮箱及适用资助见 `AUTHOR_CHECKLIST_ZH.md`。此次未向服务器同步、未 push、未上传私人材料，也未提交论文。

`CLOSEOUT_RESPONSE.md` 和 `provenance/` 中的历史核验记录属于此前收口工作，不是本次 LaTeX 转换的新评审。

## 本次编译结果

Tectonic 0.15.0 实际编译成功：`main.pdf` 8 页，`supplement.pdf` 9 页。两个 PDF 位于包根目录。全部 17 页已渲染并查看页面总览；无越界盒或未定义引用，仍有非致命的行间距/页内空白警告，保留 `main.log`、`supplement.log` 供核查。本次没有单独运行 pdfLaTeX，应用内编译曾超时，随后由独立 Tectonic 完成。也可用 `tectonic main.tex` 和 `tectonic supplement.tex` 重建。
