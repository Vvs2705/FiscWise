# ============================================================
# ContaFlow -- Setup Git + Push para GitHub
# Execute este script UMA VEZ no PowerShell
# Clique com botao direito no arquivo > "Executar com PowerShell"
# ============================================================

$projectPath = "C:\Users\VINICIUS\Videos\MEUS PROJETOS\ContaFlow"
$remoteUrl   = "https://github.com/Vvs2705/ContaFlow.git"

Set-Location $projectPath

# Remove .git corrompido se existir
if (Test-Path ".git") {
    Write-Host "==> Removendo .git anterior corrompido..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".git"
    Write-Host "    .git removido com sucesso." -ForegroundColor Green
}

Write-Host "==> Inicializando repositorio git..." -ForegroundColor Cyan
git init
git branch -M main

Write-Host "==> Configurando identidade..." -ForegroundColor Cyan
git config user.email "vsouz009@gmail.com"
git config user.name  "Vvs2705"

Write-Host "==> Adicionando remote origin..." -ForegroundColor Cyan
git remote add origin $remoteUrl

Write-Host "==> Adicionando todos os arquivos..." -ForegroundColor Cyan
git add .

Write-Host "==> Primeiro commit..." -ForegroundColor Cyan
git commit -m "feat: initial commit -- ContaFlow backend complete (Phases 06-08)"

Write-Host "==> Fazendo push para GitHub (sera solicitado login)..." -ForegroundColor Yellow
Write-Host "    Use seu Personal Access Token como senha (nao a senha da conta)" -ForegroundColor Yellow
Write-Host "    Gere em: https://github.com/settings/tokens/new (scope: repo)" -ForegroundColor Yellow
git push -u origin main

Write-Host ""
Write-Host "OK! Codigo no GitHub: $remoteUrl" -ForegroundColor Green
Write-Host "   Railway fara o deploy automatico ao detectar o push." -ForegroundColor Green
