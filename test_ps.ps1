param($LogFile)
Start-Transcript -Path $LogFile
& cmd.exe /c "echo hello"
$exit = $LASTEXITCODE
Stop-Transcript
exit $exit