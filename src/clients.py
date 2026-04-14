import gc
import os
import shutil
from openai import OpenAI
from qdrant_client import QdrantClient
from .config import settings

def build_openai_client() -> OpenAI:
    return OpenAI(api_key=settings.api_key, base_url=settings.base_url)

# 延迟初始化 Qdrant 客户端
_qdrant_client = None

def get_qdrant_client() -> QdrantClient:
    """获取 Qdrant 客户端（延迟初始化）"""
    global _qdrant_client
    
    if _qdrant_client is not None:
        return _qdrant_client
    
    # 转换为绝对路径
    qdrant_path = os.path.abspath(settings.qdrant_path)
    print(f"[INFO] Using Qdrant path: {qdrant_path}")
    
    if not os.path.exists(qdrant_path):
        print(f"[WARNING] Qdrant path not found: {qdrant_path}")
    
    # 尝试清理可能的锁文件
    lock_file = os.path.join(qdrant_path, ".lock")
    if os.path.exists(lock_file):
        print(f"[WARNING] Removing existing Qdrant lock file: {lock_file}")
        try:
            os.remove(lock_file)
            print(f"[INFO] Lock file removed successfully")
        except PermissionError:
            print(f"[WARNING] Permission denied when removing lock file, trying to force...")
            try:
                import stat
                os.chmod(lock_file, stat.S_IWRITE)
                os.remove(lock_file)
            except Exception as e:
                print(f"[WARNING] Failed to remove lock file: {e}")
        except Exception as e:
            print(f"[WARNING] Failed to remove lock file: {e}")
    
    try:
        _qdrant_client = QdrantClient(path=qdrant_path)
        print(f"[INFO] Qdrant client created successfully")
        return _qdrant_client
    except RuntimeError as e:
        # 若是"同一进程里重复初始化/残留实例"导致的占用，尝试释放后重试一次
        if "already accessed by another instance" in str(e):
            print(f"[WARNING] Qdrant instance locked, attempting to recover...")
            try:
                if _qdrant_client is not None and hasattr(_qdrant_client, "close"):
                    _qdrant_client.close()
            finally:
                _qdrant_client = None
                gc.collect()
            
            # 再次尝试清理锁文件
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except:
                    pass
            
            # 再次尝试创建客户端
            _qdrant_client = QdrantClient(path=qdrant_path)
            print(f"[INFO] Qdrant client recovered successfully")
            return _qdrant_client
        raise

# 添加程序退出时的清理逻辑
import atexit

def cleanup_qdrant_client():
    global _qdrant_client
    if _qdrant_client is not None:
        try:
            _qdrant_client.close()
            print("[INFO] Qdrant client closed successfully")
        except Exception as e:
            print(f"[WARNING] Error closing Qdrant client: {e}")
        finally:
            _qdrant_client = None

atexit.register(cleanup_qdrant_client)

# 立即创建 OpenAI 客户端
openai_client = build_openai_client()

# Qdrant 客户端延迟初始化
qdrant_client = None

def init_qdrant():
    """初始化 Qdrant 客户端"""
    global qdrant_client
    if qdrant_client is None:
        qdrant_client = get_qdrant_client()
    return qdrant_client
