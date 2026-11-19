# Виправляє DATABASE_URL у Secret beauty-db-secret (namespace beauty-studio).
# Причина: пароль містить символ '@', а в URL він має бути закодований як %40.
# Без цього SQLAlchemy бачить хост "...@beauty-studio-db" і /api/bookings повертає 500.
# Пароль НЕ змінюється і НЕ виводиться на екран.
#
# Запуск із папки beauty_studo:
#   powershell -ExecutionPolicy Bypass -File scripts\fix-db-secret.ps1

$ErrorActionPreference = "Stop"
$ns = "beauty-studio"
$secretName = "beauty-db-secret"

function Decode([string]$b64) {
    [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))
}

$secret = kubectl get secret $secretName -n $ns -o json | ConvertFrom-Json
$user = Decode $secret.data.POSTGRES_USER
$pass = Decode $secret.data.POSTGRES_PASSWORD
$db   = Decode $secret.data.POSTGRES_DB

$url = "postgresql://{0}:{1}@beauty-studio-db:5432/{2}" -f `
    [uri]::EscapeDataString($user), [uri]::EscapeDataString($pass), $db
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($url))

$patchFile = Join-Path $env:TEMP "beauty-db-secret-patch.json"
'{"data":{"DATABASE_URL":"' + $b64 + '"}}' | Out-File -FilePath $patchFile -Encoding ascii
try {
    kubectl patch secret $secretName -n $ns --type merge --patch-file $patchFile
} finally {
    Remove-Item $patchFile -Force -ErrorAction SilentlyContinue
}
Write-Host "DATABASE_URL оновлено (пароль закодовано)." -ForegroundColor Green

# Поди читають Secret лише під час старту, тому перезапускаємо бекенд.
kubectl argo rollouts restart beauty-studio-backend -n $ns
Write-Host "Бекенд перезапускається. Перевірка: kubectl get pods -n $ns" -ForegroundColor Green
