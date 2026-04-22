# ============================================
# 思政云伴侣 - Docker 部署脚本
# 自动打包并上传到服务器
# ============================================

param(
    [string]$ServerIP = "82.156.211.237",
    [string]$User = "ubuntu",
    [string]$RemotePath = "/home/ubuntu/ideology-platform"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  思政云伴侣 - Docker 部署脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 设置路径
$ProjectRoot = "D:\Desktop\大四学习资料\workspace\ideology-platform"
$TempDir = "C:\temp\ideology-platform-deploy"
$ZipFile = "C:\temp\ideology-platform.zip"

# 步骤 1: 清理临时目录
Write-Host "[1/5] 清理临时目录..." -ForegroundColor Yellow
if (Test-Path $TempDir) {
    Remove-Item -Path $TempDir -Recurse -Force
}
if (Test-Path $ZipFile) {
    Remove-Item -Path $ZipFile -Force
}
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
Write-Host "      完成" -ForegroundColor Green

# 步骤 2: 复制必要文件
Write-Host "[2/5] 复制项目文件..." -ForegroundColor Yellow
$filesToCopy = @(
    "app.py",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "package.json",
    "package-lock.json"
)

$dirsToCopy = @(
    "src",
    "static",
    "templates",
    "content",
    "Qdrant",
    "scripts"
)

# 复制文件
foreach ($file in $filesToCopy) {
    $srcPath = Join-Path $ProjectRoot $file
    if (Test-Path $srcPath) {
        Copy-Item -Path $srcPath -Destination $TempDir -Force
        Write-Host "      复制: $file" -ForegroundColor Gray
    } else {
        Write-Host "      警告: $file 不存在" -ForegroundColor Red
    }
}

# 复制文件夹
foreach ($dir in $dirsToCopy) {
    $srcPath = Join-Path $ProjectRoot $dir
    if (Test-Path $srcPath) {
        Copy-Item -Path $srcPath -Destination $TempDir -Recurse -Force
        Write-Host "      复制: $dir/" -ForegroundColor Gray
    } else {
        Write-Host "      警告: $dir/ 不存在" -ForegroundColor Red
    }
}
Write-Host "      完成" -ForegroundColor Green

# 步骤 3: 打包
Write-Host "[3/5] 打包项目..." -ForegroundColor Yellow
Compress-Archive -Path "$TempDir\*" -DestinationPath $ZipFile -Force
$zipSize = (Get-Item $ZipFile).Length / 1MB
Write-Host "      完成 (大小: $([math]::Round($zipSize, 2)) MB)" -ForegroundColor Green

# 步骤 4: 上传到服务器
Write-Host "[4/5] 上传到服务器 $ServerIP..." -ForegroundColor Yellow
Write-Host "      正在上传，请稍候..." -ForegroundColor Gray

$scpCommand = "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null `"$ZipFile`" ${User}@${ServerIP}:${RemotePath}/"

# 使用 Start-Process 来执行 SCP
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "powershell.exe"
$psi.Arguments = "-Command `"$scpCommand`""
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true

$process = [System.Diagnostics.Process]::Start($psi)
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()
$process.WaitForExit()

if ($process.ExitCode -eq 0) {
    Write-Host "      上传完成" -ForegroundColor Green
} else {
    Write-Host "      上传失败" -ForegroundColor Red
    Write-Host "      错误: $stderr" -ForegroundColor Red
    exit 1
}

# 步骤 5: 在服务器上解压并部署
Write-Host "[5/5] 在服务器上部署..." -ForegroundColor Yellow
$sshCommands = @"
cd $RemotePath
unzip -o ideology-platform.zip -d .
rm -f ideology-platform.zip

# 创建必要目录
mkdir -p outputs/html outputs/ppt outputs/ppt_image_cache downloads cache/sessions

# 检查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "警告: .env 文件不存在，请手动创建"
    echo "参考 .env.example 文件"
fi

echo "文件解压完成，准备构建 Docker 镜像..."
"@

$sshCommand = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${User}@${ServerIP} '$sshCommands'"
$psi2 = New-Object System.Diagnostics.ProcessStartInfo
$psi2.FileName = "powershell.exe"
$psi2.Arguments = "-Command `"$sshCommand`""
$psi2.UseShellExecute = $false
$psi2.RedirectStandardOutput = $true
$psi2.RedirectStandardError = $true

$process2 = [System.Diagnostics.Process]::Start($psi2)
$stdout2 = $process2.StandardOutput.ReadToEnd()
$stderr2 = $process2.StandardError.ReadToEnd()
$process2.WaitForExit()

Write-Host $stdout2 -ForegroundColor Gray
if ($stderr2) {
    Write-Host $stderr2 -ForegroundColor Red
}

if ($process2.ExitCode -eq 0) {
    Write-Host "      部署准备完成" -ForegroundColor Green
} else {
    Write-Host "      部署准备失败" -ForegroundColor Red
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  文件上传完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步：在服务器上执行以下命令构建并运行 Docker：" -ForegroundColor Yellow
Write-Host ""
Write-Host "  cd /home/ubuntu/ideology-platform" -ForegroundColor Cyan
Write-Host "  docker compose up -d --build" -ForegroundColor Cyan
Write-Host ""
Write-Host "查看日志：" -ForegroundColor Yellow
Write-Host '  docker compose logs -f' -ForegroundColor Cyan
Write-Host ''
