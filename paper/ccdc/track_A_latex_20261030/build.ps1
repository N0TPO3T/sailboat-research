$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    foreach ($entry in @('main.tex', 'supplement.tex')) {
        if (Get-Command latexmk -ErrorAction SilentlyContinue) {
            & latexmk -pdf -interaction=nonstopmode -halt-on-error $entry
            if ($LASTEXITCODE -ne 0) { throw "LaTeX compilation failed: $entry" }
        } else {
            foreach ($pass in 1..2) {
                & pdflatex -interaction=nonstopmode -halt-on-error $entry
                if ($LASTEXITCODE -ne 0) { throw "LaTeX compilation failed: $entry" }
            }
        }
    }
} finally { Pop-Location }
