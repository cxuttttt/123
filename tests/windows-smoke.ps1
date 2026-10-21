param([Parameter(Mandatory=$true)][string]$Bundle)
$ErrorActionPreference = 'Stop'
$bundlePath = (Resolve-Path -LiteralPath $Bundle).Path
$testPython = (Get-Command python.exe).Source
$testRoot = Join-Path $env:TEMP ('PocketAgent-test-' + [Guid]::NewGuid().ToString('N'))
$fixture = Join-Path $testRoot '便携 测试'
$reportRoot = Join-Path (Split-Path $PSScriptRoot -Parent) 'test-results'
New-Item -ItemType Directory -Path $fixture,$reportRoot -Force | Out-Null
Copy-Item -LiteralPath $bundlePath -Destination $fixture -Recurse
$originalPath = $env:PATH
$originalFetch = $env:OPENCODE_DISABLE_MODELS_FETCH
$env:OPENCODE_DISABLE_MODELS_FETCH = '1'
$env:PATH = "$env:WINDIR\System32;$env:WINDIR\System32\WindowsPowerShell\v1.0;$env:WINDIR"
$mapped = @()
try {
    foreach ($drive in @('R:', 'S:')) {
        if (Test-Path ($drive + '\')) { throw "Test drive already in use: $drive" }
        & subst.exe $drive $testRoot
        if ($LASTEXITCODE -ne 0) { throw "subst failed for $drive" }
        $mapped += $drive
        $portable = Join-Path ($drive + '\便携 测试') (Split-Path $bundlePath -Leaf)
        New-Item -ItemType Directory -Path (Join-Path $portable 'workspaces\default') -Force | Out-Null
        $launcher = Join-Path $portable 'PocketAgent.exe'
        # Windows PowerShell 5's native argument marshaller mishandles quoted
        # arguments ending in a backslash; use the canonical directory here.
        $doctor = & $launcher --project (Join-Path $portable 'workspaces\default') --doctor 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Doctor failed: $doctor" }
        $doctorText = $doctor -join "`n"
        $doctorText | Set-Content -Encoding utf8 (Join-Path $reportRoot ($drive.TrimEnd(':') + '-doctor.txt'))
        if ($doctorText -notmatch [Regex]::Escape('Root: ' + $drive + '\')) { throw 'Current drive was not used by the launcher' }
        if ($doctorText -notmatch 'data[\\/]share[\\/]opencode') { throw 'Portable data path not used' }
        if ($drive -eq 'R:') {
            'portable-state-survives' | Set-Content -Encoding utf8 (Join-Path $portable 'data\state-marker.txt')
            & $testPython (Join-Path $PSScriptRoot 'agent_roundtrip.py') --launcher $launcher --report (Join-Path $reportRoot 'R-agent.json')
        } else {
            if ((Get-Content (Join-Path $portable 'data\state-marker.txt')).Trim() -ne 'portable-state-survives') { throw 'State lost during drive change' }
            & $testPython (Join-Path $PSScriptRoot 'agent_roundtrip.py') --launcher $launcher --resume-last --report (Join-Path $reportRoot 'S-agent.json')
        }
        if ($LASTEXITCODE -ne 0) { throw "Real OpenCode tool integration failed on $drive" }
        & subst.exe $drive /d
        if ($LASTEXITCODE -ne 0) { throw "Could not unmap $drive" }
        $mapped = @($mapped | Where-Object { $_ -ne $drive })
    }
    'PASS: isolated PATH; bundled runtimes; Unicode/space paths; R: -> S:; real read/edit/shell; persistent resumed session.' |
        Set-Content -Encoding utf8 (Join-Path $reportRoot 'summary.txt')
    Get-Content (Join-Path $reportRoot 'summary.txt')
} finally {
    foreach ($drive in $mapped) { & subst.exe $drive /d }
    $env:PATH = $originalPath
    $env:OPENCODE_DISABLE_MODELS_FETCH = $originalFetch
    Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}

