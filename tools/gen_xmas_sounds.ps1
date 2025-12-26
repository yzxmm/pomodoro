Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

function Gen-Audio {
    param($path, $text)
    $dir = Split-Path $path
    if (!(Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $synth.SetOutputToWaveFile($path)
    $synth.Speak($text)
    $synth.SetOutputToNull()
    Write-Host "Generated $path"
}

$root = "E:\Pomodoro_Widget\pomodoro_git\cloud"

# Greetings
Gen-Audio "$root\holidays\christmas\greeting\greet1.wav" "Merry Christmas! Welcome back."
Gen-Audio "$root\holidays\christmas\greeting\greet2.wav" "Ho Ho Ho! It is Christmas day."
Gen-Audio "$root\holidays\christmas\greeting\greet3.wav" "Happy Holidays! Let's have a productive Christmas."

# Common Holiday (Global)
Gen-Audio "$root\holidays\christmas\common1.wav" "Jingle bells, jingle bells."
Gen-Audio "$root\holidays\christmas\common2.wav" "Christmas spirit is in the air."
Gen-Audio "$root\holidays\christmas\common3.wav" "Have a holly jolly Christmas."

# Start
Gen-Audio "$root\start\christmas\start1.wav" "Starting work on this Christmas day."
Gen-Audio "$root\start\christmas\start2.wav" "Focus time! Even Santa is working."
Gen-Audio "$root\start\christmas\start3.wav" "Let's get things done before the feast."

# End
Gen-Audio "$root\end\christmas\end1.wav" "Work is done! Time for presents."
Gen-Audio "$root\end\christmas\end2.wav" "Great job! Merry Christmas."
Gen-Audio "$root\end\christmas\end3.wav" "Session complete. Enjoy the holiday."

# Interval
Gen-Audio "$root\interval\christmas\int1.wav" "Take a break and have some eggnog."
Gen-Audio "$root\interval\christmas\int2.wav" "Short rest. Check your stocking."
Gen-Audio "$root\interval\christmas\int3.wav" "Relax for a bit. It's Christmas!"

# Resume
Gen-Audio "$root\resume\christmas\res1.wav" "Back to work. Santa is watching."
Gen-Audio "$root\resume\christmas\res2.wav" "Resuming session. Stay festive."
Gen-Audio "$root\resume\christmas\res3.wav" "Let's continue. The reindeer are waiting."

# Exit
Gen-Audio "$root\exit\christmas\exit1.wav" "Goodbye! Merry Christmas to all."
Gen-Audio "$root\exit\christmas\exit2.wav" "Closing down. Happy New Year soon."
Gen-Audio "$root\exit\christmas\exit3.wav" "See you later. Enjoy the snow."
