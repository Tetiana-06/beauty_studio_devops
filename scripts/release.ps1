# ЛР-7, завдання 6: реліз з дефектом і його відкат через Git (GitOps).
#
#   powershell -ExecutionPolicy Bypass -File scripts\release.ps1 bad     # failRate 0.5 -> push у main
#   powershell -ExecutionPolicy Bypass -File scripts\release.ps1 revert  # git revert -> push у main
#
# Після push скрипт просить Argo CD одразу перечитати Git (не чекати до 3 хв).

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("bad", "revert")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
$repo = Join-Path $PSScriptRoot "..\..\beauty-studio-gitops" | Resolve-Path
$valuesRel = "charts/beauty-studio/values-minikube.yaml"
$values = Join-Path $repo $valuesRel

Push-Location $repo
try {
    git checkout main
    git pull origin main

    if ($Mode -eq "bad") {
        $text = [IO.File]::ReadAllText($values)
        if ($text -notmatch 'failRate: "0\.0"') { throw "failRate вже не 0.0 - спершу виконайте: release.ps1 revert" }
        $text = $text -replace 'failRate: "0\.0"', 'failRate: "0.5"'
        [IO.File]::WriteAllText($values, $text, (New-Object Text.UTF8Encoding($false)))
        git add $valuesRel
        git commit -m "release: backend canary with 50% failure rate (will be aborted) #DVO-L7"
    }
    else {
        $last = git log -1 --format=%s
        if ($last -notmatch "failure rate") { throw "Останній коміт у main - не реліз з дефектом: '$last'" }
        git revert HEAD --no-edit
    }

    git push origin main
    git log --oneline -1
}
finally {
    Pop-Location
}

kubectl annotate application beauty-studio -n argocd argocd.argoproj.io/refresh=normal --overwrite | Out-Null
Write-Host "Push виконано, Argo CD отримав сигнал Refresh." -ForegroundColor Green
