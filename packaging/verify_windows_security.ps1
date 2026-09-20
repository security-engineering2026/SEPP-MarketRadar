$ErrorActionPreference = "Stop"
$exe = Join-Path $PSScriptRoot "..\release\portable\MarketRadar\MarketRadar.exe"
if (-not (Test-Path $exe)) { throw "EXE missing" }
$sig = Get-AuthenticodeSignature $exe
[pscustomobject]@{ Path=$exe; Status=$sig.Status; Signer=if($sig.SignerCertificate){$sig.SignerCertificate.Subject}else{$null} } | ConvertTo-Json
if ($env:REQUIRE_AUTHENTICODE_SIGNING -eq "1" -and $sig.Status -ne "Valid") { throw "Authenticode signature required but not valid" }
