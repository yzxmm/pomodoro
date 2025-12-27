Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 0  # Normal speed

function Gen-Audio {
    param($text, $path)
    $parent = Split-Path $path
    if (!(Test-Path $parent)) { New-Item -ItemType Directory -Force $parent | Out-Null }
    $absPath = Join-Path (Get-Location) $path
    $synth.SetOutputToWaveFile($absPath)
    $synth.Speak($text)
    $synth.SetOutputToNull()
    Write-Host "Generated $path"
}

$categories = @("start", "end", "interval", "resume", "exit")

foreach ($cat in $categories) {
    # Generate 3 files for each category for Christmas
    for ($i = 1; $i -le 3; $i++) {
        Gen-Audio "Merry Christmas! This is $cat voice number $i." "cloud/$cat/christmas/$i.wav"
    }
}
