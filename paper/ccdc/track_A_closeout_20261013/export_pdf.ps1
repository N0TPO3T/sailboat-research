param([string]$OutputName = 'manuscript.pdf', [string]$InputName = 'manuscript.docx')
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $document = $word.Documents.Open((Join-Path $PSScriptRoot $InputName), $false, $true)
    $document.ExportAsFixedFormat((Join-Path $PSScriptRoot $OutputName), 17, $false, 0, 0, 1, 1, 0, $true, $true, 0, $true, $true, $true)
    $document.Close(0)
} finally {
    $word.Quit()
}
