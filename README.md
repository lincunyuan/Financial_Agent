
```bash
python run_frontend.py
```

python scripts/download_sse_financial_reports.py --stock-code 600519.SH --max-downloads 10


.\Start-DBservices.ps1 

以管理员身份打开新的 PowerShell
# 切换到 MySQL 目录
cd D:\program\mysql-9.5.0-winx64

# 启动服务
net start MySQL9.5

# 使用临时密码登录
mysql -u root -p

-- 退出
EXIT;



redis
cd D:\program\redis


# 连接到Redis
redis-cli -h localhost -p 6379

# 输入密码认证
AUTH 123

# 现在可以执行命令了
INFO
KEYS *


# 财经知识助手 Agent

一个基于RAG（检索增强生成）技术的智能财经知识助手，支持知识库检索、实时数据查询和对话历史管理，具备完善的插件系统和多模态交互能力。

## 项目完善状态

### ✅ 已完成的功能模块

#### 1. 核心模块
- **`core/agent_coordinator.py`** - Agent主协调器，管理对话流程和工具调用
- **`core/data_processor.py`** - 数据处理器，处理各种数据格式
- **`core/intent_recognizer.py`** - 意图识别器，识别用户查询意图和实体
- **`core/knowledge_base.py`** - 知识库管理，支持向量检索和相关度排序
- **`core/llm_client.py`** - LLM客户端，支持OpenAI API和本地模型（如Ollama）
- **`core/prompt_engine.py`** - 提示词引擎，动态生成高质量提示词
- **`core/session_manager.py`** - 会话管理器，使用Redis管理会话状态和对话历史

#### 2. LangChain集成
- **`core/langchain_graph.py`** - 基于LangChain的状态图实现
- **`core/langchain_rag.py`** - LangChain RAG实现
- **`core/langchain_tools.py`** - 自定义工具封装

#### 3. 模块化组件平台
- **`core/mcp/`** - 插件系统框架
  - `context_storage_api.py` - 上下文存储API
  - `data_source_api.py` - 数据源API
  - `plugin_manager.py` - 插件管理器
  - `tool_plugin_api.py` - 工具插件API

#### 4. 具体插件实现
- **`core/plugins/`**
  - `stock_price_plugin.py` - 股票价格查询插件
  - `market_index_plugin.py` - 市场指数查询插件

#### 5. 工具脚本
- **`scripts/init_kb.py`** - 知识库初始化脚本
- **`scripts/data_sync.py`** - 数据同步脚本
- **`scripts/build_rag_kb.py`** - 构建RAG知识库
- **`scripts/download_all_stock_data.py`** - 批量下载股票数据
- **`scripts/generate_stock_mapping_csv.py`** - 生成股票映射表

## 功能特性

- 📚 **知识库检索**：基于Chroma向量数据库的RAG知识库，支持PDF文档和结构化数据检索
- 💬 **对话管理**：使用Redis存储和管理对话历史，支持上下文理解和多轮对话
- 🔌 **工具集成**：支持股票数据、市场指数等实时API调用，采用插件化架构
- 🤖 **大模型支持**：支持OpenAI API和本地模型（如Ollama）
- 📖 **来源引用**：自动标注知识库来源，提高回答可信度
- 📊 **实时数据**：集成AKShare等财经数据源，提供实时股票行情和市场数据
- 🔍 **意图识别**：基于规则和模型的混合意图识别系统，支持复杂查询理解
- 📱 **Web界面**：基于Streamlit的用户友好型Web界面

## 项目架构

```
financial_assistant_agent/
├── config/                 # 配置文件目录
│   ├── database.yaml      # 数据库连接配置
│   └── model_config.yaml  # 大模型配置
├── core/                   # 核心模块
│   ├── agent_coordinator.py  # Agent主协调器
│   ├── data_processor.py     # 数据处理器
│   ├── intent_recognizer.py  # 意图识别器
│   ├── knowledge_base.py     # 知识库管理
│   ├── langchain_graph.py    # LangChain工作流图
│   ├── langchain_rag.py      # LangChain RAG实现
│   ├── langchain_tools.py    # LangChain工具集成
│   ├── llm_client.py         # LLM客户端
│   ├── mcp/                  # 模块化组件平台
│   │   ├── context_storage_api.py  # 上下文存储API
│   │   ├── data_source_api.py      # 数据源API
│   │   ├── plugin_manager.py       # 插件管理器
│   │   └── tool_plugin_api.py      # 工具插件API
│   ├── plugins/              # 具体插件实现
│   │   ├── market_index_plugin.py  # 市场指数插件
│   │   └── stock_price_plugin.py   # 股票价格插件
│   ├── prompt_engine.py      # 提示词引擎
│   ├── session_manager.py    # 会话管理器
│   └── tool_integration.py   # 工具集成
├── data/                   # 数据目录
│   ├── pdfs/               # PDF文档存储
│   ├── stock_mapping.csv   # 股票代码映射表
│   └── vector_db/          # 向量数据库存储
├── scripts/                # 工具脚本
│   ├── build_rag_kb.py     # 构建RAG知识库
│   ├── data_sync.py        # 数据同步脚本
│   ├── download_all_stock_data.py  # 下载全量股票数据
│   ├── generate_stock_mapping_csv.py  # 生成股票映射表
│   ├── init_kb.py          # 初始化知识库
│   └── test_*.py           # 各种测试脚本
├── utils/                  # 工具模块
│   ├── config_loader.py    # 配置加载器
│   ├── embedding_utils.py  # 向量化工具
│   ├── logging.py          # 日志管理
│   └── text_processing.py  # 文本处理
├── app.py                  # Streamlit Web应用入口
├── main.py                 # 命令行应用入口
├── requirements.txt        # 依赖包列表
└── setup_models.bat        # 模型设置脚本
```

## 安装步骤

### 1. 环境要求

- Python 3.8+
- Redis 6.0+（用于会话管理）
- MySQL 5.7+ 或 8.0+（可选，用于结构化数据存储）

### 2. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 3. 安装和配置数据库

#### Redis安装与配置

下载并安装Redis（Windows用户可使用Redis for Windows）。

##### Redis持久化配置

为确保会话数据不丢失，建议配置Redis持久化：

```conf
# 保存900秒（15分钟）内有至少1个键被修改
save 900 1
# 保存300秒（5分钟）内有至少10个键被修改
save 300 10
# 保存60秒（1分钟）内有至少10000个键被修改
save 60 10000

# RDB文件名称
dbfilename dump.rdb

# RDB文件保存路径
# Windows示例：C:\redis\data
# Linux/macOS示例：/var/lib/redis
dir /var/lib/redis

# 启用AOF持久化
appendonly yes

# AOF文件名称
appendfilename "appendonly.aof"

# AOF持久化策略（每秒将缓冲区内容写入磁盘）
appendfsync everysec

# 自动重写AOF文件的配置
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
```

**启动Redis服务**：

```bash
# Windows
redis-server redis.windows.conf

# Linux
sudo systemctl restart redis-server
```

#### MySQL配置（可选）

如果需要使用MySQL存储结构化数据，创建数据库：

```sql
CREATE DATABASE financial_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 配置项目

#### 4.1 配置数据库连接

编辑 `config/database.yaml`：

```yaml
mysql:
  host: "localhost"
  user: "root"
  password: "your_password"  # 填入MySQL密码
  database: "financial_rag"

redis:
  host: "localhost"
  port: 6379
  password: ""  # Redis密码（如果有）
  db: 0

vector_db:
  type: "chroma"
  persist_directory: "./data/vector_db"
```

#### 4.2 配置大模型

编辑 `config/model_config.yaml`：

**使用OpenAI：**
```yaml
provider: "openai"
api_key: "your_openai_api_key"  # 或设置环境变量 OPENAI_API_KEY
model: "gpt-3.5-turbo"
temperature: 0.7
```

**使用本地模型（Ollama）：**
```yaml
provider: "local"
base_url: "http://localhost:11434"
model: "llama2"
temperature: 0.7
```

## 使用方法

### 1. 初始化知识库

首次使用前，初始化向量数据库：

```bash
python scripts/init_kb.py
```

### 2. 构建RAG知识库

导入PDF文档到知识库：

```bash
# 将PDF文件放入data/pdfs/目录后执行
python scripts/build_rag_kb.py
```

### 3. 生成股票映射表

```bash
python scripts/generate_stock_mapping_csv.py
```

### 4. 运行应用

#### 4.1 Web界面（推荐）

启动Streamlit Web应用：

```bash
python app.py
```

或使用快捷脚本：

```bash
python run_frontend.py
```

访问 `http://localhost:8501` 使用Web界面。

#### 4.2 命令行界面

启动命令行交互模式：

```bash
python main.py
```

指定用户ID：

```bash
python main.py --user-id user123
```

## 使用示例

### Web界面示例

1. 打开浏览器访问 `http://localhost:8501`
2. 在输入框中输入问题，例如：
   - "贵州茅台的股价是多少？"
   - "它和酒鬼酒谁的表现更好？"
   - "上证指数今天的走势如何？"
3. 查看助手的回答，包含实时数据和知识库引用

### 命令行示例

```
欢迎使用财经知识助手Agent！输入'退出'结束对话。

您的问题: 什么是股票市场？
助手回答: 股票市场是股票发行和交易的场所...[详细回答]

您的问题: 贵州茅台的股价是多少？
助手回答: 截至2024年XX月XX日，贵州茅台(600519)的股价为XXXX元...

您的问题: 它和五粮液相比怎么样？
助手回答: 贵州茅台和五粮液都是中国白酒行业的龙头

您的问题: 退出
感谢使用，再见！
```

## 测试指南

### 1. 测试Redis连接

```bash
python -c "from core.session_manager import RedisSessionManager; sm = RedisSessionManager(); print('Redis连接成功')"
```

### 2. 测试意图识别

```bash
python -c "from core.intent_recognizer import IntentRecognizer; ir = IntentRecognizer(); result = ir.recognize_intent('贵州茅台的股价是多少？'); print(f'意图识别结果: {result}')"
```

### 3. 测试股票查询插件

```bash
python scripts/test_stock_query.py
```

### 4. 测试对话历史功能

```bash
python test_conversation_history.py
```

### 5. 端到端测试

```bash
python scripts/test_end_to_end.py
```

## 故障排除

### 问题：Redis连接失败
- 检查Redis服务是否启动：`redis-cli ping`
- 确认配置文件中的Redis连接参数是否正确
- 检查防火墙设置，确保端口6379可访问

### 问题：向量数据库初始化失败
- 检查 `data/vector_db/` 目录是否存在且有写入权限
- 确认Chroma数据库依赖是否正确安装

### 问题：股票数据查询失败
- 检查AKShare是否正确安装：`pip install akshare`
- 确认网络连接正常，AKShare需要网络访问

### 问题：LLM调用失败
- 检查API密钥是否正确配置
- 确认网络连接正常
- 查看日志文件了解详细错误信息

## 注意事项

1. **服务必须运行**
   - Redis服务需要运行（用于会话管理）
   - MySQL服务可选（仅用于结构化数据存储）

2. **配置文件需要填写**
   - `config/database.yaml` 中的配置需要填写
   - `config/model_config.yaml` 中的LLM配置需要填写（或使用环境变量）

3. **如果没有配置LLM**
   - 系统会使用模拟模式运行
   - 可以测试知识库检索功能，但回答是模拟的

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！


## 代码推送指南

### SSH配置与代码推送流程

当您需要向GitHub仓库推送代码时，按照以下步骤操作：

### 1. 确保SSH代理正在运行（Windows系统）
首先需要启动SSH代理，让Git能够自动使用您的SSH密钥：
```powershell
# 启动SSH代理服务
Start-Service ssh-agent

# 将SSH密钥添加到代理
ssh-add ~/.ssh/id_rsa
```

如果`Start-Service`命令失败（如权限问题），可以尝试：
```powershell
# 使用Git Bash提供的ssh-agent
ssh-agent bash -c 'ssh-add ~/.ssh/id_rsa; bash'
```

### 2. 检查远程仓库配置（可选）
确认您的远程仓库URL仍然是SSH格式：
```powershell
git remote -v
```

如果输出显示`https://`开头的URL，需要切换回SSH格式：
```powershell
git remote set-url origin git@github.com:lincunyuan/Financial_Agent.git
```

### 3. 添加更改并提交
```powershell
# 添加所有修改的文件到暂存区
git add -A

# 提交更改
git commit -m "您的提交信息"
```

### 4. 推送代码
```powershell
# 推送到远程仓库的main分支
git push origin master:main
```
或如果您的本地分支已经与远程分支关联：
```powershell
git push
```

### 故障排除：
如果推送时出现`Permission denied (publickey)`错误：
1. 确保SSH代理正在运行且密钥已添加：`ssh-add -l`（应显示您的密钥）
2. 检查公钥是否已正确添加到GitHub账户
3. 确认远程仓库URL是正确的SSH格式

### 简化流程（推荐）：
您可以将SSH代理启动和密钥添加的步骤添加到PowerShell配置文件中，这样每次打开终端都会自动完成这些设置。


ipconfig /flushdns
git push origin master:main