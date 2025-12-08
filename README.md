# 财经知识助手 Agent

一个基于RAG（检索增强生成）技术的智能财经知识助手，支持知识库检索、实时数据查询和对话历史管理。

## 功能特性

- 📚 **知识库检索**：基于Milvus向量数据库和MySQL的RAG知识库
- 💬 **对话管理**：使用Redis存储和管理对话历史
- 🔌 **工具集成**：支持股票数据、市场指数等实时API调用
- 🤖 **大模型支持**：支持OpenAI API和本地模型（如Ollama）
- 📖 **来源引用**：自动标注知识库来源，提高回答可信度

## 项目结构

```
financial_assistant_agent/
├── config/                 # 配置文件目录
│   ├── api_keys.yaml      # API密钥配置
│   ├── database.yaml      # 数据库连接配置
│   └── model_config.yaml  # 大模型配置
├── core/                   # 核心模块
│   ├── agent_coordinator.py  # Agent主协调器
│   ├── knowledge_base.py     # 知识库管理
│   ├── llm_client.py         # LLM客户端
│   ├── session_manager.py    # 会话管理
│   └── tool_integration.py   # 工具集成
├── scripts/                # 工具脚本
│   ├── init_kb.py         # 初始化知识库
│   └── data_sync.py       # 数据同步脚本
├── utils/                  # 工具模块
│   ├── config_loader.py   # 配置加载器
│   ├── embedding_utils.py # 向量化工具
│   ├── logging.py         # 日志管理
│   └── text_processing.py # 文本处理
├── main.py                # 主程序入口
└── requirements.txt       # 依赖包列表
```

## 安装步骤

### 1. 环境要求

- Python 3.8+
- MySQL 5.7+ 或 8.0+
- Redis 6.0+
- Milvus 2.0+

### 2. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 3. 安装和配置数据库

#### MySQL

创建数据库：
```sql
CREATE DATABASE financial_rag;
```

#### Redis

确保Redis服务已启动：
```bash
redis-server
```

#### Milvus

参考 [Milvus安装文档](https://milvus.io/docs/install_standalone-docker.md) 安装Milvus。

使用Docker快速启动：
```bash
docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest
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
```

#### 4.2 配置API密钥

编辑 `config/api_keys.yaml`，填入相应的API密钥（如需要）。

#### 4.3 配置大模型

编辑 `config/model_config.yaml`：

**使用OpenAI：**
```yaml
provider: "openai"
api_key: "your_openai_api_key"  # 或设置环境变量 OPENAI_API_KEY
model: "gpt-3.5-turbo"
```

**使用本地模型（Ollama）：**
```yaml
provider: "local"
base_url: "http://localhost:11434"
model: "llama2"
```

## 使用指南

### 1. 初始化知识库

首先初始化知识库（创建数据库表和Milvus集合）：

```bash
python scripts/init_kb.py
```

### 2. 添加知识库内容

将财经新闻或文档添加到知识库：

```bash
# 同步单个URL
python scripts/data_sync.py --urls https://example.com/financial-news-1

# 同步多个URL
python scripts/data_sync.py --urls https://example.com/news-1 https://example.com/news-2

# 从文件读取URL列表（每行一个URL）
python scripts/data_sync.py --file urls.txt
```

### 3. 运行主程序

启动财经助手Agent：

```bash
python main.py
```

或指定用户ID：

```bash
python main.py --user-id user123
```

### 4. 使用示例

启动后会进入交互式对话模式：

```
欢迎使用财经知识助手Agent！输入'退出'结束对话。

您的问题: 什么是股票市场？
助手回答: [基于知识库的回答，包含来源引用]

您的问题: 退出
感谢使用，再见！
```

## 测试指南

### 单元测试

由于项目结构已完整，您可以开始进行测试：

### 1. 测试数据库连接

```bash
# 测试MySQL连接
python -c "from core.knowledge_base import FinancialKnowledgeBase; kb = FinancialKnowledgeBase(); print('MySQL连接成功'); kb.close_connections()"

# 测试Redis连接
python -c "from core.session_manager import RedisSessionManager; sm = RedisSessionManager(); print('Redis连接成功')"
```

### 2. 测试知识库初始化

```bash
python scripts/init_kb.py
```

### 3. 测试配置加载

```bash
python -c "from utils.config_loader import default_config_loader; print(default_config_loader.load_all_configs())"
```

### 4. 测试向量化

```bash
python -c "from utils.embedding_utils import EmbeddingGenerator; gen = EmbeddingGenerator(); vec = gen.encode('测试文本'); print(f'向量维度: {vec.shape}')"
```

### 5. 完整功能测试

1. **初始化知识库**
   ```bash
   python scripts/init_kb.py
   ```

2. **添加测试数据**
   ```bash
   # 创建一个测试URL文件
   echo "https://example.com/financial-news" > test_urls.txt
   python scripts/data_sync.py --file test_urls.txt
   ```

3. **运行主程序并测试对话**
   ```bash
   python main.py
   ```

## 开发说明

### 添加新的数据源

1. 在 `core/tool_integration.py` 中添加新的API客户端
2. 在 `core/agent_coordinator.py` 的 `_get_relevant_tool_data` 方法中添加调用逻辑

### 自定义LLM提供商

在 `core/llm_client.py` 中添加新的提供商支持，实现相应的 `_generate_xxx` 方法。

### 调整知识库检索参数

修改 `core/knowledge_base.py` 中的 `retrieve_relevant_chunks` 方法的 `top_k` 参数。

## 注意事项

1. **API密钥安全**：不要将包含真实API密钥的配置文件提交到版本控制系统。建议使用环境变量或在 `.gitignore` 中排除配置文件。

2. **数据库连接**：确保MySQL、Redis和Milvus服务在运行前已启动。

3. **模型配置**：如果没有配置LLM API，系统将使用模拟模式运行，主要用于测试知识库检索功能。

4. **向量模型**：默认使用 `all-MiniLM-L6-v2`（英文）或 `paraphrase-multilingual-MiniLM-L12-v2`（中英文），可根据需要调整。

## 故障排除

### 问题：Milvus连接失败
- 检查Milvus服务是否运行：`docker ps | grep milvus`
- 确认端口19530是否开放

### 问题：MySQL连接失败
- 检查MySQL服务是否运行
- 确认用户名、密码和数据库名称是否正确

### 问题：Redis连接失败
- 检查Redis服务是否运行：`redis-cli ping`
- 确认端口6379是否开放

### 问题：LLM调用失败
- 检查API密钥是否正确配置
- 确认网络连接正常
- 查看日志文件了解详细错误信息

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

