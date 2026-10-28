$ErrorActionPreference='Stop'
foreach($name in @('live_uart.ps1','start_demo.ps1','stop_demo_worker.ps1')){
 $parseTokens=$null;$parseErrors=$null
 $tree=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name),[ref]$parseTokens,[ref]$parseErrors)
 if($parseErrors.Count){throw ($parseErrors|Out-String)}
 if($name -eq 'live_uart.ps1'){
  # Execute only the pure Hash and Decode functions, never the script/device body.
  foreach($functionName in @('Hash','Decode')){
   $part=$tree.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $functionName},$true)
   if($null -eq $part){throw 'Missing pure protocol function'}
   . ([ScriptBlock]::Create($part.Extent.Text))
  }
 }
}
$Session='abcdef0123456789abcdef0123456789';$Manifest='a'*64
$proof=@{session=$Session;package_manifest_sha256=$Manifest;nonce=('b'*32)}
$raw=[Text.Encoding]::UTF8.GetBytes(($proof|ConvertTo-Json -Compress))
$stream=[IO.MemoryStream]::new();$z=[IO.Compression.ZLibStream]::new($stream,[IO.Compression.CompressionLevel]::Fastest,$true);$z.Write($raw,0,$raw.Length);$z.Dispose();$encoded=[Convert]::ToBase64String($stream.ToArray());$stream.Dispose()
$line='M544_READY '+(Hash $raw)+' '+$encoded
$decoded=Decode $line 'READY'
if($decoded.nonce -ne $proof.nonce){throw 'Decoded protocol value changed'}
$rejected=0
foreach($bad in @($line.Replace((Hash $raw),('0'*64)),$line.Replace('M544_READY','M544_RESULT'))){try{$null=Decode $bad 'READY'}catch{$rejected++}}
$Session='c'*32;try{$null=Decode $line 'READY'}catch{$rejected++}
if($rejected -ne 3){throw 'Pure packet rejection failed'}
Write-Output 'PASS: 3 host scripts parsed; actual .NET ZLib/SHA Decode round-trip and 3 invalid packets rejected. Zero UART/device calls.'
