# Resolve an installed Python 3.10+ and manage this skill's dependencies.
# Order: DRAW_PYTHON -> activated virtual environment -> skill-local .venv
# -> python / python3 on PATH. No parent/sibling directories are inspected.
# Python is never downloaded. An invalid explicit override fails immediately.
#
# Actions:
#   resolve       print the chosen python.exe absolute path
#   check-deps    exit 0 when the resolved python can import the drawing deps
#   install       pip install requirements.txt into the resolved python
param(
    [ValidateSet('resolve', 'check-deps', 'install')]
    [string]$Action = 'resolve'
)

$ErrorActionPreference = 'Continue'

$SkillPath = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-Usable {
    param([string]$Py)
    if (-not $Py -or -not (Test-Path -LiteralPath $Py)) { return $false }
    try {
        & $Py -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>$null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}

function Get-EnvironmentPython {
    param([string]$Directory)
    foreach ($RelativePath in @('Scripts/python.exe', 'bin/python')) {
        $Candidate = Join-Path $Directory $RelativePath
        if (Test-Usable $Candidate) {
            return (Resolve-Path -LiteralPath $Candidate).ProviderPath
        }
    }
    return $null
}

function Find-Python {
    if ($env:DRAW_PYTHON) {
        $p = $env:DRAW_PYTHON
        if (Test-Path -LiteralPath $p -PathType Container) {
            $p = Join-Path $p 'python.exe'
        }
        if (Test-Usable $p) { return (Resolve-Path -LiteralPath $p).ProviderPath }
        Write-Error 'bootstrap: DRAW_PYTHON 无效，需要 Python 3.10+ 的解释器文件或目录'
        return $null
    }
    if ($env:VIRTUAL_ENV) {
        $p = Get-EnvironmentPython $env:VIRTUAL_ENV
        if ($p) { return $p }
        Write-Error 'bootstrap: 当前激活的虚拟环境中未找到 Python 3.10+'
        return $null
    }
    $p = Get-EnvironmentPython (Join-Path $SkillPath '.venv')
    if ($p) { return $p }
    foreach ($CommandName in @('python', 'python3')) {
        $Command = Get-Command $CommandName -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($Command -and (Test-Usable $Command.Source)) { return $Command.Source }
    }
    Write-Error 'bootstrap: 未找到 Python 3.10+；请先安装 Python 并加入 PATH，或设置 DRAW_PYTHON'
    return $null
}

function Get-Index {
    if ($env:DRAW_PIP_INDEX) { return $env:DRAW_PIP_INDEX }
    return 'https://pypi.org/simple'
}

switch ($Action) {
    'resolve' {
        $Py = Find-Python
        if (-not $Py) { exit 3 }
        Write-Output $Py
        exit 0
    }
    'check-deps' {
        $Py = Find-Python
        if (-not $Py) { Write-Error 'bootstrap: 未找到可用 Python'; exit 3 }
        & $Py -B -c 'import PIL, numpy, matplotlib, svglib, reportlab.graphics, rlPyCairo'
        exit $LASTEXITCODE
    }
    'install' {
        $Py = Find-Python
        if (-not $Py) { Write-Error 'bootstrap: 未找到可用 Python'; exit 3 }
        & $Py -m pip install --disable-pip-version-check --index-url (Get-Index) -r (Join-Path $SkillPath 'requirements.txt')
        exit $LASTEXITCODE
    }
}
