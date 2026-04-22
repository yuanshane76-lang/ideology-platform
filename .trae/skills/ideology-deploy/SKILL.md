---
name: "ideology-deploy"
description: "部署和更新 Ideology-Platform 思政云伴侣项目到服务器。Invoke when user wants to deploy the project to server, update files on server, or manage the deployment process."
---

# Ideology-Platform 部署 Skill

本 Skill 专门用于 Ideology-Platform（思政云伴侣）项目的服务器部署和文件更新。

## 服务器信息

- **服务器地址**: `82.156.211.237`
- **SSH 端口**: `22`
- **部署用户**: `root`
- **部署路径**: `/opt/ideology-platform`
- **服务端口**: `6006`

## 部署前准备

### 1. 确保本地有 SSH 密钥

```powershell
# 检查是否存在 SSH 密钥
ls ~/.ssh/id_rsa

# 如果不存在，生成密钥（一路回车）
ssh-keygen -t rsa -b 4096

# 将公钥复制到服务器（首次需要密码）
ssh-copy-id root@82.156.211.237
```

### 2. 确保服务器环境就绪

服务器已配置：
- Python 3.12
- Nginx 反向代理
- systemd 服务管理
- Qdrant 向量数据库数据

## 常用部署操作

### 完整部署流程（首次或重大更新）

```powershell
# 1. 进入项目目录
cd D:\Desktop\大四学习资料\workspace\ideology-platform

# 2. 确保代码已提交
git status
git add .
git commit -m "部署前更新"

# 3. 运行部署脚本
.\deploy_to_server.ps1
```

### 快速更新（仅代码变更）

```powershell
# 使用简单部署脚本（仅同步代码，不重启服务）
.\deploy_simple.ps1

# 然后 SSH 到服务器手动重启
ssh root@82.156.211.237
systemctl restart ideology
```

### Docker 部署

```powershell
# 构建并推送 Docker 镜像
.\deploy_docker.ps1
```

## 文件同步命令

### 同步特定文件/目录

```powershell
# 同步 src 目录
scp -r .\src\ root@82.156.211.237:/opt/ideology-platform/

# 同步 templates
scp -r .\templates\ root@82.156.211.237:/opt/ideology-platform/

# 同步 static
scp -r .\static\ root@82.156.211.237:/opt/ideology-platform/

# 同步单个文件
scp .\app.py root@82.156.211.237:/opt/ideology-platform/
scp .\requirements.txt root@82.156.211.237:/opt/ideology-platform/
```

### 同步配置变更

```powershell
# 同步 .env 文件（谨慎操作）
scp .\.env root@82.156.211.237:/opt/ideology-platform/

# 同步 Dockerfile
scp .\Dockerfile root@82.156.211.237:/opt/ideology-platform/

# 同步 docker-compose.yml
scp .\docker-compose.yml root@82.156.211.237:/opt/ideology-platform/
```

## 服务器管理命令

### SSH 登录

```powershell
ssh root@82.156.211.237
```

### 服务管理

```bash
# 查看服务状态
systemctl status ideology

# 重启服务
systemctl restart ideology

# 停止服务
systemctl stop ideology

# 启动服务
systemctl start ideology

# 查看日志
journalctl -u ideology -f
```

### 查看应用日志

```bash
# 实时查看日志
tail -f /opt/ideology-platform/app.log

# 查看最近100行
tail -n 100 /opt/ideology-platform/app.log
```

### 检查服务运行状态

```bash
# 检查端口监听
netstat -tlnp | grep 6006

# 检查进程
ps aux | grep gunicorn

# 测试本地访问
curl http://localhost:6006
```

## 更新流程（标准操作）

### 1. 本地开发完成

```powershell
# 检查修改的文件
git status

# 提交更改
git add .
git commit -m "feat: xxx 功能更新"
```

### 2. 部署到服务器

```powershell
# 方式一：使用部署脚本（推荐）
.\deploy_to_server.ps1

# 方式二：手动同步
ssh root@82.156.211.237 "cd /opt/ideology-platform && git pull"

# 如果需要，同步本地未提交的更改
scp -r .\src\ root@82.156.211.237:/opt/ideology-platform/
```

### 3. 服务器端操作

```powershell
ssh root@82.156.211.237
```

```bash
cd /opt/ideology-platform

# 如果使用虚拟环境
source venv/bin/activate

# 安装新依赖（如果 requirements.txt 有变更）
pip install -r requirements.txt

# 重启服务
systemctl restart ideology

# 检查状态
systemctl status ideology
```

### 4. 验证部署

```bash
# 服务器本地测试
curl http://localhost:6006

# 查看公网访问
curl http://82.156.211.237:6006
```

## 常见问题处理

### 服务无法启动

```bash
# 检查日志
journalctl -u ideology -n 50

# 检查配置文件
python -c "from src.config import settings; print('Config OK')"

# 检查端口占用
lsof -i :6006
```

### 依赖问题

```bash
cd /opt/ideology-platform
source venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt --force-reinstall

# 重启服务
systemctl restart ideology
```

### Qdrant 数据库问题

```bash
# 检查 Qdrant 目录权限
ls -la /opt/ideology-platform/qdrant_db

# 确保服务用户有权限
chown -R ubuntu:ubuntu /opt/ideology-platform/qdrant_db
```

### Nginx 配置检查

```bash
# 测试配置
nginx -t

# 重载配置
systemctl reload nginx
```

## 回滚操作

```bash
cd /opt/ideology-platform

# 查看提交历史
git log --oneline -10

# 回滚到指定版本
git reset --hard <commit-hash>

# 重启服务
systemctl restart ideology
```

## 安全注意事项

1. **不要提交 .env 文件到 Git**
2. **SSH 密钥妥善保管**
3. **定期更新服务器密码**
4. **检查防火墙规则**

## 快捷命令汇总

```powershell
# 一键部署（本地执行）
.\deploy_to_server.ps1

# 快速查看服务器日志
ssh root@82.156.211.237 "journalctl -u ideology -f"

# 快速重启服务
ssh root@82.156.211.237 "systemctl restart ideology"

# 检查服务健康
ssh root@82.156.211.237 "curl -s http://localhost:6006 | head -5"
```
