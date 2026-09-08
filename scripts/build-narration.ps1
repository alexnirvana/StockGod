param([string]$Python = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Python) { $Python = Join-Path $projectRoot '.venv/Scripts/python.exe' }
& $Python (Join-Path $PSScriptRoot 'narration-assets.py') prepare
if ($LASTEXITCODE -ne 0) { throw 'Narration preparation failed.' }
Add-Type -AssemblyName System.Speech
$speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $plan = Get-Content -Raw -Encoding utf8 (Join-Path $projectRoot 'data/narration-build/plan.json') | ConvertFrom-Json
    foreach ($track in $plan) {
        $speaker.SelectVoice($track.voice)
        $speaker.Rate = 0
        for ($i = 0; $i -lt $track.sections.Count; $i++) {
            $outputPath = Join-Path $projectRoot ('data/narration-build/' + $track.build_id + '-' + $i + '.wav')
            $speaker.SetOutputToWaveFile($outputPath)
            $speaker.Speak($track.sections[$i].text)
            $speaker.SetOutputToNull()
        }
        Write-Output ('Synthesized ' + $track.build_id)
    }
} finally { $speaker.Dispose() }
& $Python (Join-Path $PSScriptRoot 'narration-assets.py') package
if ($LASTEXITCODE -ne 0) { throw 'Narration packaging failed.' }
