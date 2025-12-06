# Legal Research 模块实现指南

## 📋 项目结构

```
backend/
├── modules/legal_research/          # 新增法律检索模块
│   ├── __init__.py                  # 模块说明
│   ├── retriever.py                 # 核心检索引擎 (两层检索)
│   ├── routes.py                    # FastAPI路由
│   └── requirements.txt              # 依赖列表
├── scripts/
│   └── build_vector_db.py           # 向量库构建脚本
└── app.py                           # (已更新) 注册新路由

frontend/src/
└── pages/
    └── LegalResearch.tsx            # (已更新) 前端页面
```

## 🚀 快速开始

### Step 1: 安装依赖

```bash
# 后端依赖
cd backend
pip install -r modules/legal_research/requirements.txt

# 前端已包含必要库
```

### Step 2: 构建向量库

前置条件：准备好你的法律JSON数据库

```bash
# 方式1：使用命令行参数
python scripts/build_vector_db.py \
  --json-root /path/to/json-laws \
  --output-path ./data/vector_db

# 方式2：使用环境变量
export LEGAL_JSON_ROOT=/path/to/json-laws
export LEGAL_VECTOR_DB_PATH=./data/vector_db
python scripts/build_vector_db.py

# 方式3：使用GPU (推荐)
python scripts/build_vector_db.py \
  --json-root /path/to/json-laws \
  --output-path ./data/vector_db
# (默认使用GPU，若无GPU可加 --no-cuda)
```

输出示例：
```
============================================================
🚀 法律检索向量库构建工具
============================================================
📂 JSON文件目录: /path/to/json-laws
💾 输出路径: ./data/vector_db
🖥️  使用GPU: True
============================================================
📂 找到 150 个JSON文件
加载JSON文件: 100%|██████████| 150/150 [02:35<00:00,  1.03s/it]
✅ 成功加载 45230 个文档
🔧 构建向量库...
  • 文档数: 45230
  • 设备: cuda
  • 嵌入模型: shibing624/text2vec-base-chinese
📌 生成嵌入向量...
✅ 向量库已保存到: ./data/vector_db
============================================================
```

### Step 3: 启动后端服务

```bash
# 设置向量库路径
export LEGAL_VECTOR_DB_PATH=./data/vector_db

# 启动Flask服务
cd backend
python app.py

# 或使用uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: 启动前端服务

```bash
cd frontend
npm install
npm start
```

访问: http://localhost:3000/legal-research

## 🔍 API 文档

### 1. 执行检索

**POST** `/api/legal-research/search`

请求体：
```json
{
  "query": "《合同法》第六十条",
  "top_k": 3
}
```

响应：
```json
{
  "query": "《合同法》第六十条",
  "search_type": "exact",
  "message": "✓ 精确匹配成功",
  "results": [
    {
      "content": "《中华人民共和国合同法》 第六十条: 当事人订立合同...",
      "law_name": "中华人民共和国合同法",
      "simple_law_name": "合同法",
      "article": "第六十条",
      "article_num": 60,
      "score": 1.0,
      "metadata": {...}
    }
  ]
}
```

### 2. 批量检索

**POST** `/api/legal-research/batch-search`

请求体：
```json
{
  "queries": [
    "《合同法》第六十条",
    "《公司法》第三十五条"
  ],
  "top_k": 3
}
```

### 3. 健康检查

**GET** `/api/legal-research/health`

### 4. 统计信息 (调试)

**GET** `/api/legal-research/debug/stats`

## 🎯 检索策略

### 两层检索流程

```
用户查询 "《合同法》第六十条"
    ↓
[第一层] 精确检索
    • 提取法律名称: "合同法"
    • 提取法条号: "第六十条" → 60
    • 遍历所有文档，匹配 law_name 和 article_num
    • ✓ 找到精确匹配 → 返回
    • ✗ 未找到 → 进入第二层
    ↓
[第二层] 模糊检索 (向量相似度)
    • 将查询转换为向量 (text2vec-base-chinese)
    • 使用 FAISS 搜索相似度最高的 Top-K
    • 返回 Top-3 法条 (含相似度分数)
```

### 响应结果类型

| search_type | 说明 | score |
|------------|------|-------|
| `exact` | 精确匹配 | 1.0 |
| `fuzzy` | 向量相似度 | 0-1 |
| `none` | 无结果 | - |

## 📊 前端页面功能

### 主界面
- ✅ 查询输入（支持多行）
- ✅ Top-K 参数设置
- ✅ 执行检索按钮
- ✅ 结果列表展示
  - 法律名称 + 法条号
  - 相似度分数 (模糊检索时显示)
  - 条文内容预览

### 详情抽屉
- ✅ 完整条文内容
- ✅ 法律基本信息
- ✅ 复制到剪贴板功能

## 🔧 环境配置

### 必需环境变量

```bash
# 向量库路径 (最重要！)
export LEGAL_VECTOR_DB_PATH=/path/to/vector_db

# 可选
export LEGAL_JSON_ROOT=/path/to/json-laws  # 构建脚本使用
```

### Docker 部署 (可选)

```dockerfile
# backend/Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
COPY modules/legal_research/requirements.txt ./modules/legal_research/
RUN pip install -r requirements.txt && \
    pip install -r modules/legal_research/requirements.txt

COPY . .

ENV LEGAL_VECTOR_DB_PATH=/data/vector_db

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🧪 测试示例

### cURL 测试

```bash
# 精确检索
curl -X POST http://localhost:8000/api/legal-research/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "《合同法》第六十条",
    "top_k": 3
  }'

# 模糊检索
curl -X POST http://localhost:8000/api/legal-research/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "合同的主要条款",
    "top_k": 5
  }'
```

### Python 测试

```python
from modules.legal_research.retriever import LegalRetriever

# 初始化检索引擎
retriever = LegalRetriever('./data/vector_db')

# 执行检索
result = retriever.search("《合同法》第六十条", top_k=3)

print(f"检索类型: {result['search_type']}")
print(f"结果数: {len(result['results'])}")

for r in result['results']:
    print(f"- {r['law_name']} {r['article']}")
    print(f"  相似度: {r['score']:.2%}")
    print(f"  内容: {r['content'][:100]}...")
```

## 🐛 常见问题

### Q1: 构建向量库时内存不足

**解决方案：**
- 使用 CPU 而非 GPU: `--no-cuda`
- 分批处理文件
- 增加系统虚拟内存

### Q2: 查询时返回 "向量数据库路径不存在"

**解决方案：**
- 确保已执行 `build_vector_db.py`
- 检查 `LEGAL_VECTOR_DB_PATH` 环境变量是否正确设置
- 验证输出目录权限

### Q3: 模糊检索结果不理想

**优化方案：**
- 增加 `top_k` 参数，从Top-3改为Top-5
- 改进查询关键词的表述
- 更新或重建向量库

### Q4: 精确匹配失败，都是模糊匹配

**可能原因：**
- 查询格式不标准 (应为 "《法律名称》法条号")
- JSON数据中法律名称或法条号格式不一致
- 需要调整提取正则表达式

## 📚 技术细节

### 嵌入模型

使用 `shibing624/text2vec-base-chinese`
- **维度**: 768
- **优势**: 中文优化，适合法律文本
- **加载**: 自动从 HuggingFace 下载

### FAISS 索引

使用 `FAISS.from_documents()` 构建默认索引
- **索引类型**: Flat (精确搜索)
- **相似度度量**: L2距离 (转换为余弦相似度)
- **搜索复杂度**: O(n) (线性搜索)

### 性能指标

| 操作 | 耗时 | 规模 |
|------|------|------|
| 加载JSON | ~3s | 150文件 |
| 生成嵌入 | ~2.5min | 45k文档 |
| 向量库保存 | ~10s | 完整库 |
| 精确检索 | <1ms | - |
| 模糊检索 | <500ms | Top-3 |

## 🔗 集成对标

### 与 DeepResearch 对标

| 维度 | DeepResearch | Legal Research |
|------|--------------|-----------------|
| 输入 | 研究主题 | 法律查询 |
| 数据源 | 网络搜索 | 向量数据库 |
| 处理流程 | 多轮迭代 | 两层检索 |
| 会话管理 | UUID + 内存 | 无需会话 |
| 前端流程 | 审核→生成 | 查询→返回 |

### API 调用示例

前端模板代码已在 `LegalResearch.tsx` 中提供，
可参考 DeepResearch 页面的模式进行集成。

## 📖 下一步扩展

1. **性能优化**
   - 使用 `IVFFlat` 或 `HNSW` 索引加速检索
   - 实现查询缓存

2. **功能增强**
   - 支持关键词过滤 (如: 仅搜索特定法律)
   - 返回相关条例组合
   - LLM 答案生成

3. **用户体验**
   - 搜索历史记录
   - 法律书签功能
   - 下载导出 PDF

---

**模块开发人员**: 
**创建日期**: 2025-12-07
**版本**: 1.0.0
