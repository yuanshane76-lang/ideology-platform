# 简单部署脚本
$ServerIP = "82.156.211.237"
$User = "ubuntu"

Write-Host "打包项目..."

$ProjectRoot = "D:\Desktop\大四学习资料\workspace\ideology-platform"
$TempDir = "C:\temp\ideology-platform-deploy"
$ZipFile = "C:\temp\ideology-platform.zip"

# 清理并创建临时目录
if (Test-Path $TempDir) { Remove-Item -Path $TempDir -Recurse -Force }
if (Test-Path $ZipFile) { Remove-Item -Path $ZipFile -Force }
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

# 复制文件
Copy-Item -Path "$ProjectRoot\app.py" -Destination $TempDir -Force
Copy-Item -Path "$ProjectRoot\requirements.txt" -Destination $TempDir -Force
Copy-Item -Path "$ProjectRoot\Dockerfile" -Destination $TempDir -Force
Copy-Item -Path "$ProjectRoot\docker-compose.yml" -Destination $TempDir -Force
Copy-Item -Path "$ProjectRoot\package.json" -Destination $TempDir -Force
Copy-Item -Path "$ProjectRoot\src" -Destination $TempDir -Recurse -Force
Copy-Item -Path "$ProjectRoot\static" -Destination $TempDir -Recurse -Force
Copy-Item -Path "$ProjectRoot\templates" -Destination $TempDir -Recurse -Force
Copy-Item -Path "$ProjectRoot\content" -Destination $TempDir -Recurse -Force
Copy-Item -Path "$ProjectRoot\Qdrant" -Destination $TempDir -Recurse -Force
Copy-Item -Path "$ProjectRoot\scripts" -Destination $TempDir -Recurse -Force

# 打包
Compress-Archive -Path "$TempDir\*" -DestinationPath $ZipFile -Force
$zipSize = (Get-Item $ZipFile).Length / 1MB
Write-Host "打包完成: $([math]::Round($zipSize, 2)) MB"

# 上传
Write-Host "上传到服务器..."
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$ZipFile" "${User}@${ServerIP}:/home/ubuntu/ideology-platform/"

if ($LASTEXITCODE -eq 0) {
    Write-Host "上传成功!"
    
    # 在服务器上解压
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "${User}@${ServerIP}" "cd /home/ubuntu/ideology-platform && unzip -o ideology-platform.zip && rm -f ideology-platform.zip && mkdir -p outputs/html outputs/ppt outputs/ppt_image_cache downloads cache/sessions && echo '部署准备完成'"
    
    Write-Host ""
    Write-Host "=========================================="
    Write-Host "部署准备完成!"
    Write-Host "=========================================="
    Write-Host ""
    Write-Host "请在服务器上执行以下命令:"
    Write-Host "  cd /home/ubuntu/ideology-platform"
    Write-Host "  docker compose up -d --build"
    Write-Host ""
    Write-Host "查看日志:"
    Write-Host "  docker compose logs -f"
} else {
    Write-Host "上传失败!"
}
