@echo off
chcp 65001 > nul
echo ===== 开始下载 Sentence Transformer 模型 =====

:: 创建目录
if not exist ".\models\all-MiniLM-L6-v2" (
    mkdir ".\models\all-MiniLM-L6-v2"
    echo 创建目录: .\models\all-MiniLM-L6-v2
)

:: 方法1: 使用 Python 直接下载
echo.
echo [方法1] 使用 Python 下载模型...
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='sentence-transformers/all-MiniLM-L6-v2', local_dir='./models/all-MiniLM-L6-v2', local_dir_use_symlinks=False, resume_download=True)"

if %errorlevel% neq 0 (
    echo.
    echo [方法1] 下载失败，尝试方法2...
    
    :: 方法2: 使用阿里云镜像
    echo [方法2] 使用阿里云镜像下载...
    git clone https://www.modelscope.cn/sentence-transformers/all-MiniLM-L6-v2.git ./models/all-MiniLM-L6-v2-temp
    
    if %errorlevel% equ 0 (
        echo 移动文件到目标目录...
        move /Y .\models\all-MiniLM-L6-v2-temp\* .\models\all-MiniLM-L6-v2\ >nul 2>&1
        rmdir /s /q .\models\all-MiniLM-L6-v2-temp
        echo [方法2] 下载成功！
    ) else (
        echo [方法2] 下载失败，请检查网络连接
        goto :error
    )
) else (
    echo [方法1] 下载成功！
)

echo.
echo ===== 下载完成 =====
echo 模型路径: .\models\all-MiniLM-L6-v2
dir .\models\all-MiniLM-L6-v2
echo.
echo 现在可以修改代码使用本地模型：
echo "model = SentenceTransformer('./models/all-MiniLM-L6-v2', device='cpu')"
goto :eof

:error
echo.
echo ===== 下载失败 =====
echo 请尝试手动下载：
echo 1. 访问 https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
echo 2. 点击 "Files and versions" 选项卡
echo 3. 手动下载所有文件到 .\models\all-MiniLM-L6-v2 目录
pause