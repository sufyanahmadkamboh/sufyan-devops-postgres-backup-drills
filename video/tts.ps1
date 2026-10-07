# Narrates every step with the Windows speech engine (offline).
#   powershell -File tts.ps1 <items.json> <voice name> <sample rate> <speed -10..10>
# items.json: [{"text": "...", "out": "...wav"}, ...]
param([string]$Items, [string]$Voice = 'Microsoft David Desktop', [int]$Rate = 24000, [int]$Speed = 0)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo($Rate, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$list = Get-Content -Raw -Encoding UTF8 $Items | ConvertFrom-Json
$n = 0
foreach ($item in $list) {
  $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
  $s.SelectVoice($Voice)
  $s.Rate = $Speed
  $s.SetOutputToWaveFile($item.out, $format)
  $s.Speak($item.text)
  $s.Dispose()
  $n++
}
"narrated $n steps with $Voice"
