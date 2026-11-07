$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $document = $word.Documents.Open((Join-Path $PSScriptRoot 'manuscript.docx'), $false, $true)
    $document.ExportAsFixedFormat((Join-Path $PSScriptRoot 'manuscript.pdf'), 17)
    $document.Close(0)
} finally {
    $word.Quit()
}
