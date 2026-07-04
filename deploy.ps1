# AORA AI - Production Deployment Helper Script

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "      AORA AI Deployment Trigger          " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Deploy Frontend to Vercel
Write-Host "`n[1/2] Deploying Frontend to Vercel..." -ForegroundColor Yellow
if (Get-Command vercel -ErrorAction SilentlyContinue) {
    cd frontend
    vercel --prod
    cd ..
    Write-Host "Vercel deployment completed successfully." -ForegroundColor Green
} else {
    Write-Host "WARNING: 'vercel' CLI is not found on your system path." -ForegroundColor Red
    Write-Host "Please install Vercel CLI globally: npm install -g vercel" -ForegroundColor White
    Write-Host "Then run: cd frontend; vercel --prod" -ForegroundColor White
}

# 2. Deploy Backend to Google Cloud Run
Write-Host "`n[2/2] Deploying Backend to Google Cloud Run..." -ForegroundColor Yellow
if (Get-Command gcloud -ErrorAction SilentlyContinue) {
    cd backend
    gcloud run deploy aora-backend --source . --platform managed --allow-unauthenticated
    cd ..
    Write-Host "Cloud Run deployment completed successfully." -ForegroundColor Green
} else {
    Write-Host "WARNING: 'gcloud' CLI is not found on your system path." -ForegroundColor Red
    Write-Host "Please install Google Cloud SDK: https://cloud.google.com/sdk" -ForegroundColor White
    Write-Host "Then run: cd backend; gcloud run deploy aora-backend --source ." -ForegroundColor White
}

Write-Host "`nDeployment process completed." -ForegroundColor Cyan
