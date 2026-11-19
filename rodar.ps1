# Compila (se algum .cpp/.h mudou desde o ultimo build) e roda o brp.
# Uso: .\rodar.ps1 -i instancias\brp_txt\brp_W3_H4_N8_id1.txt -m LA-1 -maxHeight file
Set-Location $PSScriptRoot
$exe = "brp.exe"
$precisa = -not (Test-Path $exe)
if (-not $precisa) {
    $t = (Get-Item $exe).LastWriteTime
    $precisa = [bool](Get-ChildItem src\*.cpp, include\*.h |
                      Where-Object { $_.LastWriteTime -gt $t })
}
if ($precisa) {
    Write-Host ">> compilando..."
    g++ -std=c++14 -O3 -static -Wall -pedantic -Wno-sign-compare -Wno-unused -Iinclude (Get-ChildItem src\*.cpp).FullName -o $exe
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
& ".\$exe" @args
