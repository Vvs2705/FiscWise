# ============================================================
# ContaFlow -- Push fix: DATABASE_URL asyncpg driver
# Execute com: botao direito > "Executar com PowerShell"
# ============================================================

$projectPath = "C:\Users\VINICIUS\Videos\MEUS PROJETOS\ContaFlow"
Set-Location $projectPath

Write-Host "==> Adicionando arquivos corrigidos..." -ForegroundColor Cyan
git add backend/app/core/config.py backend/alembic/env.py

Write-Host "==> Commit da correcao..." -ForegroundColor Cyan
git commit -m "fix: convert DATABASE_URL to postgresql+asyncpg for Railway compatibility"

Write-Host "==> Push para GitHub (Railway vai re-deployar automaticamente)..." -ForegroundColor Yellow
git push origin main

Write-Host ""
Write-Host "OK! Fix enviado. Aguarde ~2 min e o Railway vai re-deployar." -ForegroundColor Green
Write-Host "   Acesse: https://railway.com/project/00d3b902-6f5a-4677-ac35-9dd62a25a322" -ForegroundColor Green
