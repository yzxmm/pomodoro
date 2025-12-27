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

# Christmas Specific Categories
Gen-Audio "Merry Christmas! Let's start working on our gifts." "cloud/start/christmas/1.wav"
Gen-Audio "Merry Christmas! Great job, have a cookie." "cloud/end/christmas/1.wav"
Gen-Audio "Merry Christmas! Take a break under the mistletoe." "cloud/interval/christmas/1.wav"
Gen-Audio "Merry Christmas! Back to the workshop." "cloud/resume/christmas/1.wav"
Gen-Audio "Merry Christmas! Have a silent night." "cloud/exit/christmas/1.wav"

# Holiday Greeting
Gen-Audio "Ho Ho Ho! Merry Christmas! I hope you have been good this year." "cloud/holidays/christmas/greeting/1.wav"

# Common Holiday (General ambience or phrases)
Gen-Audio "Jingle bells, jingle bells." "cloud/holidays/christmas/common/1.wav"

# Winter Season (Fallback)
Gen-Audio "It is cold outside, let's focus inside." "cloud/start/winter/1.wav"
Gen-Audio "Winter session complete." "cloud/end/winter/1.wav"
Gen-Audio "Warm up with a break." "cloud/interval/winter/1.wav"
Gen-Audio "Back to the cozy work." "cloud/resume/winter/1.wav"
Gen-Audio "Stay warm, goodbye." "cloud/exit/winter/1.wav"
