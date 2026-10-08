# Generates the bundled demo consultation using the Windows TTS engine.
# Fully offline. Doctor = David, Patient = Zira. Run once; the wav is committed.

$ErrorActionPreference = "Stop"
$outDir = Join-Path $PSScriptRoot "..\data\samples"
$tmpDir = Join-Path $env:TEMP "healthsync_sample"
New-Item -ItemType Directory -Force -Path $outDir, $tmpDir | Out-Null

$lines = @(
  @{ s = "doctor";  t = "Good morning. Please sit down. What brings you in today?" },
  @{ s = "patient"; t = "Doctor, I have been having a bad cough for about five days now. And since yesterday I have fever also." },
  @{ s = "doctor";  t = "Any chest pain, or difficulty in breathing?" },
  @{ s = "patient"; t = "No chest pain. But I feel short of breath when I climb the stairs." },
  @{ s = "doctor";  t = "Is the cough dry, or is there phlegm?" },
  @{ s = "patient"; t = "There is phlegm. Yellowish in colour, mostly in the morning." },
  @{ s = "doctor";  t = "Any history of asthma? Do you smoke?" },
  @{ s = "patient"; t = "No asthma. I used to smoke, but I stopped four years back." },
  @{ s = "doctor";  t = "Let me check your vitals. Your temperature is one hundred one point two Fahrenheit. Blood pressure is one thirty over eighty five. Pulse is ninety six. Oxygen saturation is ninety seven percent on room air." },
  @{ s = "doctor";  t = "Now let me listen to your chest. Take a deep breath. I can hear some crackles in the right lower zone." },
  @{ s = "doctor";  t = "This looks like a lower respiratory tract infection, most likely bacterial. I do not think it is pneumonia, but I want a chest X ray to be sure." },
  @{ s = "patient"; t = "Is it serious, doctor?" },
  @{ s = "doctor";  t = "It is treatable. I am starting you on Amoxicillin, five hundred milligrams, three times a day, after food, for five days. Please complete the full course even if you feel better." },
  @{ s = "doctor";  t = "For the fever, take Paracetamol six hundred fifty milligrams, only when needed, up to three times a day. Do not take more than that." },
  @{ s = "patient"; t = "Should I take any cough syrup?" },
  @{ s = "doctor";  t = "Yes. Two teaspoons at bedtime, for five days. It may make you drowsy, so do not drive after taking it." },
  @{ s = "doctor";  t = "Drink plenty of warm fluids and take rest. If the fever does not come down in three days, or if you get breathing difficulty, come back immediately." },
  @{ s = "doctor";  t = "Otherwise, come for a follow up after one week, with the X ray report." },
  @{ s = "patient"; t = "Thank you doctor." }
)

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

$parts = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    if ($line.s -eq "doctor") {
        $synth.SelectVoice("Microsoft David Desktop"); $synth.Rate = 0
    } else {
        $synth.SelectVoice("Microsoft Zira Desktop"); $synth.Rate = 1
    }
    $f = Join-Path $tmpDir ("{0:d2}.wav" -f $i)
    $synth.SetOutputToWaveFile($f)
    $synth.Speak($line.t)
    $parts += $f
}
$synth.SetOutputToNull()
$synth.Dispose()

# 400 ms of silence between turns so the gap-based speaker heuristic has something to work with
$silence = Join-Path $tmpDir "sil.wav"
ffmpeg -y -loglevel error -f lavfi -i anullsrc=r=16000:cl=mono -t 0.4 -c:a pcm_s16le $silence

$listFile = Join-Path $tmpDir "list.txt"
$listLines = @()
foreach ($p in $parts) {
    $listLines += "file '$($p -replace '\\', '/')'"
    $listLines += "file '$($silence -replace '\\', '/')'"
}
Set-Content -Path $listFile -Value $listLines -Encoding ascii

$out = Join-Path $outDir "sample_consult_01.wav"
ffmpeg -y -loglevel error -f concat -safe 0 -i $listFile -ar 16000 -ac 1 -c:a pcm_s16le $out

# turn list doubles as ground truth for checking the speaker heuristic later
$truth = @()
foreach ($line in $lines) { $truth += [pscustomobject]@{ speaker = $line.s; text = $line.t } }
$truth | ConvertTo-Json -Depth 3 | Set-Content -Path (Join-Path $outDir "sample_consult_01.truth.json") -Encoding utf8

Write-Output "wrote $out"
