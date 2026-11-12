# switzerlandNG installer for Windows: always installs the NEWEST version of wintrymichi/switzerlandNG (main).
#
#   powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/wintrymichi/switzerlandNG/main/beamng/builder/launch/install.ps1 | iex"
#   powershell -ExecutionPolicy Bypass -File install.ps1 [folder] [--no-start]     default folder: %USERPROFILE%\switzerlandNG
#
# It asks GitHub for the newest commit, downloads that commit's archive (about 330 MB) and unpacks it into the folder,
# puts a "switzerlandNG" shortcut on the desktop and starts the app (the first start sets up its Python, 5-10 minutes).
# A folder that already holds switzerlandNG is updated instead (only the changed files, "Update switzerlandNG.bat").
# PowerShell variable names ignore case: every name below is used for one thing only (CLAUDE.md).
$InstArgs = @($args)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { }
$RepoName = 'wintrymichi/switzerlandNG'
$RefName = $env:SWISSNG_REF
if (-not $RefName) { $RefName = 'main' }
$Dest = Join-Path $env:USERPROFILE 'switzerlandNG'
$StartAfter = $true
foreach ($a in $InstArgs) { if ($a -eq '--no-start') { $StartAfter = $false } else { $Dest = $a } }
function Say([string]$Text) { Write-Host ''; Write-Host "  $Text" }

try {
    $Curl = (Get-Command curl.exe -ErrorAction SilentlyContinue)
    $TarExe = (Get-Command tar.exe -ErrorAction SilentlyContinue)
    if (-not $Curl -or -not $TarExe) { throw 'curl.exe and tar.exe are missing (Windows 10 1803 or newer has both).' }
    $UpdBat = Join-Path $Dest 'Update switzerlandNG.bat'
    if ((Test-Path (Join-Path $Dest '.switzerlandng.json')) -and (Test-Path $UpdBat)) {
        Say "switzerlandNG is already in ${Dest}: updating it to the newest version."
        if (-not $StartAfter) { $env:SWISSNG_UPDATE_ONLY = '1' }
        & cmd.exe /c "`"$UpdBat`""
        exit $LASTEXITCODE
    }
    Say 'Looking for the newest version of switzerlandNG...'
    $Sha = (& $Curl.Source -fsSL --retry 4 --connect-timeout 20 -H 'Accept: application/vnd.github.sha' "https://api.github.com/repos/$RepoName/commits/$RefName")
    if ($LASTEXITCODE -ne 0 -or -not ($Sha -match '^[0-9a-f]{40}$')) { throw 'GitHub could not be reached: check the internet connection.' }
    Say ("Newest version: {0}. Downloading it (about 330 MB) into {1} ..." -f $Sha.Substring(0, 10), $Dest)
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    $TmpDir = Join-Path ([IO.Path]::GetTempPath()) ("swissng-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null
    $Arc = Join-Path $TmpDir 'src.tar.gz'
    try {
        & $Curl.Source -fSL --progress-bar --retry 4 --retry-delay 3 --connect-timeout 20 --speed-limit 1024 --speed-time 60 -o $Arc "https://codeload.github.com/$RepoName/tar.gz/$Sha"
        if ($LASTEXITCODE -ne 0) { throw 'the download stopped: start the installer again.' }
        Say 'Unpacking...'
        & $TarExe.Source -xzf $Arc -C $Dest --strip-components=1
        if ($LASTEXITCODE -ne 0) { throw 'the archive could not be unpacked.' }
        $List = & $TarExe.Source -tzf $Arc | Where-Object { $_ -notmatch '/$' } | ForEach-Object { ($_ -split '/', 2)[1] } |
            Where-Object { $_ } | Sort-Object -CaseSensitive
        [IO.File]::WriteAllText((Join-Path $Dest '.switzerlandng-files.txt'), (($List -join "`n") + "`n"))
    } finally {
        Remove-Item -Recurse -Force $TmpDir -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path (Join-Path $Dest 'beamng\builder\app\server.py'))) { throw 'the download is not a switzerlandNG version.' }
    $Stamp = '{{"commit": "{0}", "ref": "{1}", "date": null, "updated": "{2}"}}' -f $Sha, $RefName, (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    [IO.File]::WriteAllText((Join-Path $Dest '.switzerlandng.json'), $Stamp + "`n")
    try {
        $Shell = New-Object -ComObject WScript.Shell
        $Lnk = $Shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'switzerlandNG.lnk'))
        $Lnk.TargetPath = Join-Path $Dest 'Start Switzerland Builder.bat'
        $Lnk.WorkingDirectory = $Dest
        $Ico = Join-Path $Dest 'beamng\builder\web\icon.ico'
        if (Test-Path $Ico) { $Lnk.IconLocation = $Ico }
        $Lnk.Save()
    } catch { }
    Say ("switzerlandNG {0} is installed in {1}. Desktop shortcut: switzerlandNG. Update it with 'Update switzerlandNG.bat'." -f $Sha.Substring(0, 10), $Dest)
    if ($StartAfter) {
        & cmd.exe /c "`"$(Join-Path $Dest 'Start Switzerland Builder.bat')`""
        exit $LASTEXITCODE
    }
    exit 0
} catch {
    Write-Host ''
    Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ''
    exit 1
}
