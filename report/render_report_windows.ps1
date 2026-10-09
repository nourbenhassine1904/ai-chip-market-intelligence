# Render only the Phase 9B document, using an isolated Word COM instance.
# No model execution, dependency installation or scientific file writes.
param([switch]$AttachWord)
$ErrorActionPreference = 'Stop'
$taskRepo = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $PSScriptRoot 'rapport_final.docx'
$pdfPath = Join-Path $PSScriptRoot 'rapport_final.pdf'
$auditPath = Join-Path $taskRepo 'docs/phase9b_render_audit.json'
$word = $null
$doc = $null
try {
    Write-Host 'Connecting to Word...'
    if ($AttachWord) {
        $word = [Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
    } else {
        $word = New-Object -ComObject Word.Application
    }
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    Write-Host 'Opening Phase 9B DOCX...'
    $doc = $word.Documents.Open($docPath, $false, $false)
    Write-Host 'Updating table of contents and repaginating...'
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    Write-Host 'TOC updated.'
    [void]$doc.Fields.Update()
    Write-Host 'Fields updated.'
    $doc.Repaginate()
    foreach ($toc in $doc.TablesOfContents) { $toc.UpdatePageNumbers() }
    $doc.Repaginate()
    $pageCount = $doc.ComputeStatistics(2)
    $sections = @()
    foreach ($bookmark in $doc.Bookmarks) {
        if ($bookmark.Name -match '^section\d+$') {
            $range = $bookmark.Range
            $sections += [ordered]@{
                bookmark = $bookmark.Name
                title = $range.Paragraphs.Item(1).Range.Text.Trim()
                page = $range.Information(3)
            }
        }
    }
    $sections = @($sections | Sort-Object { [int]($_.bookmark -replace 'section', '') })
    $bodyStart = ($sections | Where-Object { $_.title -match '^1[ .].*Introduction' } | Select-Object -First 1).page
    $annexStart = ($sections | Where-Object { $_.title -eq 'Annexes' } | Select-Object -First 1).page
    if (-not $bodyStart -or -not $annexStart) { throw 'Body or annex bookmark not found' }
    $doc.Save()
    $doc.ExportAsFixedFormat($pdfPath, 17)
    $doc.Close(0)
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($doc)
    $doc = $null
    $audit = [ordered]@{
        renderer = 'Microsoft Word COM; ExportAsFixedFormat PDF'
        rendered_at = (Get-Date).ToString('o')
        total_pages = $pageCount
        front_matter_pages = $bodyStart - 1
        body_start_page = $bodyStart
        annex_start_page = $annexStart
        body_pages_excluding_annexes = $annexStart - $bodyStart
        annex_pages = $pageCount - $annexStart + 1
        sections = $sections
        markdown_sha256 = (Get-FileHash (Join-Path $PSScriptRoot 'rapport_final.md') -Algorithm SHA256).Hash.ToLowerInvariant()
        docx_sha256 = (Get-FileHash $docPath -Algorithm SHA256).Hash.ToLowerInvariant()
        pdf_sha256 = (Get-FileHash $pdfPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $audit | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $auditPath -Encoding utf8
    $audit | ConvertTo-Json -Depth 6
}
finally {
    if ($null -ne $doc) {
        try { $doc.Close(0) } catch { Write-Warning $_ }
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($doc)
    }
    if ($null -ne $word) {
        try { $word.Quit() } catch { Write-Warning $_ }
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)
    }
}
