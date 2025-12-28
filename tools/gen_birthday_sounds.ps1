
Add-Type -AssemblyName System.Speech

function Generate-Voice {
    param (
        [string]$Text,
        [string]$Path
    )
    
    $parent = Split-Path -Path $Path
    if (-not (Test-Path -Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    # Set to a female voice if available, otherwise default
    # Try to find a voice with "Zira" (common US English female voice) or just pick first female
    $voice = $synth.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Gender -eq 'Female' } | Select-Object -First 1
    if ($voice) {
        $synth.SelectVoice($voice.VoiceInfo.Name)
    }
    
    $synth.SetOutputToWaveFile($Path)
    $synth.Speak($Text)
    $synth.Dispose()
    Write-Host "Generated: $Path"
}

$baseDir = "sounds"

# Start
Generate-Voice -Text "Happy Birthday! Let's make a wish and start working." -Path "$baseDir\start\birthday\start_bday.wav"

# End
Generate-Voice -Text "Great work! Now go enjoy your birthday cake." -Path "$baseDir\end\birthday\end_bday.wav"

# Interval
Generate-Voice -Text "Take a birthday break! You deserve it." -Path "$baseDir\interval\birthday\interval_bday.wav"

# Resume
Generate-Voice -Text "Back to work, birthday star! You're doing great." -Path "$baseDir\resume\birthday\resume_bday.wav"

# Exit
Generate-Voice -Text "Happy Birthday! See you later." -Path "$baseDir\exit\birthday\exit_bday.wav"
