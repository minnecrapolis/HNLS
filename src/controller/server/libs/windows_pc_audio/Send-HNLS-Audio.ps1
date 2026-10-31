param([switch]$SelfTest, [string]$TestOutput = "$env:TEMP\hnls-packet.bin")
$ErrorActionPreference = 'Stop'
try {
    Add-Type -Path (Join-Path $PSScriptRoot 'LoopbackSender.cs')
    if ($SelfTest) { [HNLSAudio.Sender]::SelfTest($TestOutput); Write-Host "Sender compile, PCM conversion and packet fixture passed: $TestOutput"; exit 0 }
    $config = Get-Content (Join-Path $PSScriptRoot 'connection.json') -Raw | ConvertFrom-Json
    if (-not $config.host -or $config.port -ne 8950) { throw 'Download a new sender from HNLS Music on the main Pi.' }
    Write-Host 'HNLS Windows PC Audio' -ForegroundColor Cyan
    Write-Host 'On the HNLS Music page, click Receive Windows PC audio. Use Q to stop this sender.'
    [HNLSAudio.Sender]::Run([string]$config.host, [int]$config.port, [string]$config.key)
} catch {
    Write-Host ('HNLS sender error: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'If your Windows playback device changed, close this window and start again.'
    exit 1
}
