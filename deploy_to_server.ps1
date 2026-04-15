# 思政云伴侣 - 一键部署脚本
# 使用方法: 右键点击"使用PowerShell运行" 或在PowerShell中执行: .\deploy_to_server.ps1

$ErrorActionPreference = "Stop"

# 服务器配置
$ServerIP = "82.156.211.237"
$Username = "ubuntu"
$Password = "g:}vU/=j96ZTSP8"
$RemotePath = "/home/ubuntu/ideology-platform"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  思政云伴侣 - 一键部署脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 检查本地文件
Write-Host "[1/6] 检查本地文件..." -ForegroundColor Yellow
$RequiredFiles = @("app.py", "requirements.txt", ".env", "deploy_autodl.sh", "ideology.service")
$RequiredDirs = @("src", "templates", "static", "Qdrant")

foreach ($file in $RequiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "错误: 缺少文件 $file" -ForegroundColor Red
        exit 1
    }
}

foreach ($dir in $RequiredDirs) {
    if (-not (Test-Path $dir)) {
        Write-Host "错误: 缺少目录 $dir" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✓ 所有文件检查通过" -ForegroundColor Green

# 安装OpenSSH客户端（如果需要）
Write-Host ""
Write-Host "[2/6] 检查OpenSSH客户端..." -ForegroundColor Yellow
$sshInstalled = Get-WindowsOptionalFeature -Online -FeatureName OpenSSH.Client -ErrorAction SilentlyContinue
if ($sshInstalled.State -ne "Enabled") {
    Write-Host "正在安装OpenSSH客户端..." -ForegroundColor Yellow
    Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
}
Write-Host "✓ OpenSSH客户端已就绪" -ForegroundColor Green

# 创建临时目录并复制文件
Write-Host ""
Write-Host "[3/6] 准备部署文件..." -ForegroundColor Yellow
$TempDir = "$env:TEMP\ideology-deploy"
if (Test-Path $TempDir) {
    Remove-Item -Recurse -Force $TempDir
}
New-Item -ItemType Directory -Path $TempDir | Out-Null

# 复制文件
Copy-Item -Path "app.py" -Destination $TempDir
Copy-Item -Path "requirements.txt" -Destination $TempDir
Copy-Item -Path ".env" -Destination $TempDir
Copy-Item -Path "deploy_autodl.sh" -Destination $TempDir
Copy-Item -Path "ideology.service" -Destination $TempDir
Copy-Item -Path "src" -Destination $TempDir -Recurse
Copy-Item -Path "templates" -Destination $TempDir -Recurse
Copy-Item -Path "static" -Destination $TempDir -Recurse
Copy-Item -Path "Qdrant" -Destination $TempDir -Recurse

Write-Host "✓ 文件准备完成" -ForegroundColor Green

# 使用SCP上传文件
Write-Host ""
Write-Host "[4/6] 上传文件到服务器..." -ForegroundColor Yellow
Write-Host "服务器: $ServerIP" -ForegroundColor Gray
Write-Host "这可能需要几分钟，请耐心等待..." -ForegroundColor Gray

# 创建远程目录
$createDirCmd = "echo '$Password' | ssh -o StrictHostKeyChecking=no $Username@$ServerIP 'mkdir -p $RemotePath'"
Invoke-Expression $createDirCmd

# 上传文件
$scpCmd = "scp -o StrictHostKeyChecking=no -r '$TempDir\*' $Username@${ServerIP}:$RemotePath/"
Invoke-Expression $scpCmd

Write-Host "✓ 文件上传完成" -ForegroundColor Green

# 在服务器上执行部署
Write-Host ""
Write-Host "[5/6] 在服务器上执行部署..." -ForegroundColor Yellow

$deployScript = @"
cd $RemotePath
chmod +x deploy_autodl.sh
bash deploy_autodl.sh
"@

$deployCmd = "echo '$Password' | ssh -o StrictHostKeyChecking=no $Username@$ServerIP '$deployScript'"
Invoke-Expression $deployCmd

Write-Host "✓ 部署脚本执行完成" -ForegroundColor Green

# 启动服务
Write-Host ""
Write-Host "[6/6] 启动服务..." -ForegroundColor Yellow

$startScript = @"
cd $RemotePath
sudo cp ideology.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ideology
sudo systemctl start ideology
sudo systemctl status ideology --no-pager
"@

$startCmd = "echo '$Password' | ssh -o StrictHostKeyChecking=no $Username@$ServerIP '$startScript'"
Invoke-Expression $startCmd

# 清理临时文件
Remove-Item -Recurse -Force $TempDir

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  部署完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "访问地址: http://$ServerIP`:6006" -ForegroundColor Cyan
Write-Host ""
Write-Host "管理命令:" -ForegroundColor Yellow
Write-Host "  查看状态: ssh $Username@$ServerIP 'sudo systemctl status ideology'"
Write-Host "  重启服务: ssh $Username@$ServerIP 'sudo systemctl restart ideology'"
Write-Host "  查看日志: ssh $Username@$ServerIP 'sudo journalctl -u ideology -f'"
Write-Host ""

# 等待用户确认
Read-Host "按回车键退出"
