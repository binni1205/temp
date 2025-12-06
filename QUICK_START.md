# Legal Research 快速启动指南

## 🎯 五分钟快速开始

### Step 1: 准备向量库 (关键！)

```bash
# 前提：有 JSON 法律数据库
# 假设你的数据在：/path/to/json-laws

cd /home/oslab/dc/temp/backend

# 安装依赖
pip install -r modules/legal_research/requirements.txt

# 构建向量库 (首次运行，耗时 5-10 分钟)
python scripts/build_vector_db.py \
  --json-root /path/to/json-laws \
  --output-path ./data/vector_db

# 输出示例：
# ✅ 向量库已保存到: ./data/vector_db
```

### Step 2: 启动后端服务

```bash
# 设置环境变量
export LEGAL_VECTOR_DB_PATH=/home/oslab/dc/temp/backend/data/vector_db

# 启动 FastAPI
cd /home/oslab/dc/temp/backend
python app.py

# 输出：INFO: Uvicorn running on http://0.0.0.0:8000
```

### Step 3: 启动前端服务

```bash
cd /home/oslab/dc/temp/frontend
npm install
npm start

# 浏览器访问：http://localhost:3000/legal-research
```

### Step 4: 测试API

```bash
# 在另一个终端执行

# 精确检索
curl -X POST http://localhost:8000/api/legal-research/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "《合同法》第六十条",
    "top_k": 3
  }'

# 预期响应：
# {
#   "query": "《合同法》第六十条",
#   "search_type": "exact",
#   "message": "✓ 精确匹配成功",
#   "results": [
#     {
#       "content": "《中华人民共和国合同法》 第六十条: ...",
#       "law_name": "中华人民共和国合同法",
#       "simple_law_name": "合同法",
#       "article": "第六十条",
#       "article_num": 60,
#       "score": 1.0
#     }
#   ]
# }
```

---

## 📂 文件位置速览

### 后端文件

```
backend/
├── modules/legal_research/
│   ├── __init__.py               模块说明
│   ├── retriever.py              ⭐ 核心检索引擎 (310行)
│   ├── routes.py                 ⭐ API路由 (210行)
│   ├── requirements.txt           依赖列表
│   └── README.md                 详细文档
├── scripts/
│   └── build_vector_db.py        ⭐ 向量库构建脚本 (240行)
├── app.py                        (已更新) 注册新路由
├── .env.example                  环境变量示例
└── examples_legal_research.py    使用示例 (150行)
```

### 前端文件

```
frontend/src/
├── pages/
│   ├── LegalResearch.tsx         ⭐ 搜索页面 (400行)
│   └── App.tsx                   (已更新) 添加路由
```

⭐ = 核心实现文件

---

## 🔍 核心实现概览

### 两层检索策略

```
用户查询
    ↓
[第一层] 精确检索
    ├─ 提取法律名称和法条号
    ├─ 遍历所有文档精确匹配
    ├─ 找到 → 返回 (score=1.0)
    └─ 未找到 ↓

[第二层] 模糊检索
    ├─ 向量相似度搜索
    ├─ FAISS similarity_search
    └─ 返回 Top-3 (含相似度)
```

### 关键代码片段

**检索引擎 - retriever.py**

```python
class LegalRetriever:
    def search(self, query: str, top_k: int = 3):
        # 第一层：精确检索
        exact_results = self.exact_search(query)
        if exact_results:
            return {"search_type": "exact", "results": exact_results}
        
        # 第二层：模糊检索
        fuzzy_results = self.fuzzy_search(query, top_k)
        return {"search_type": "fuzzy", "results": fuzzy_results}
```

**API 端点 - routes.py**

```python
@router.post("/search", response_model=SearchResponse)
async def search_legal(request: SearchRequest):
    retriever = get_retriever()
    result = retriever.search(request.query, top_k=request.top_k)
    return SearchResponse(
        query=result["query"],
        search_type=result["search_type"],
        results=[SearchResult(**r) for r in result["results"]],
        message="✓ 精确匹配成功" if result["search_type"] == "exact" else "✓ 向量匹配"
    )
```

---

## 🧪 测试示例

### Python 测试

```python
from modules.legal_research.retriever import LegalRetriever

# 初始化
retriever = LegalRetriever('./data/vector_db')

# 精确检索
result = retriever.search("《合同法》第六十条")
print(f"类型: {result['search_type']}")  # 输出: exact
print(f"分数: {result['results'][0]['score']}")  # 输出: 1.0

# 模糊检索
result = retriever.search("合同双方权利", top_k=5)
print(f"类型: {result['search_type']}")  # 输出: fuzzy
print(f"前3条相似度: {[r['score'] for r in result['results'][:3]]}")
```

### 前端测试

在浏览器中：
1. 访问 http://localhost:3000/legal-research
2. 输入查询：《合同法》第六十条
3. 点击"执行检索"
4. 查看结果和相似度分数
5. 点击结果卡片查看详情

---

## ⚙️ 环境变量配置

### 必需

```bash
export LEGAL_VECTOR_DB_PATH=/home/oslab/dc/temp/backend/data/vector_db
```

### 可选

```bash
export LEGAL_JSON_ROOT=/path/to/json-laws    # 构建脚本用
export HOST=0.0.0.0                          # 后端监听地址
export PORT=8000                             # 后端监听端口
```

### 持久化配置

编辑 `backend/.env`：

```bash
LEGAL_VECTOR_DB_PATH=./data/vector_db
LEGAL_JSON_ROOT=./data/json-laws
HOST=0.0.0.0
PORT=8000
```

---

## 🔗 API 参考

### 1. 单次检索

```
POST /api/legal-research/search
Content-Type: application/json

请求:
{
  "query": "《合同法》第六十条",
  "top_k": 3
}

响应:
{
  "query": "《合同法》第六十条",
  "search_type": "exact",
  "message": "✓ 精确匹配成功",
  "results": [...]
}
```

### 2. 批量检索

```
POST /api/legal-research/batch-search

请求:
{
  "queries": [
    "《合同法》第六十条",
    "《公司法》第三十五条"
  ],
  "top_k": 3
}

响应:
{
  "total": 2,
  "results": [
    { "query": "...", "search_type": "exact", "results": [...] },
    { "query": "...", "search_type": "fuzzy", "results": [...] }
  ]
}
```

### 3. 健康检查

```
GET /api/legal-research/health

响应:
{
  "status": "healthy",
  "message": "向量数据库加载成功，检索引擎就绪",
  "vector_db_path": "./data/vector_db"
}
```

### 4. 调试信息

```
GET /api/legal-research/debug/stats

响应:
{
  "status": "ok",
  "vector_db_path": "./data/vector_db",
  "total_documents": 45230,
  "embedding_model": "shibing624/text2vec-base-chinese",
  "retrieval_strategy": "exact (priority) → fuzzy (fallback)"
}
```

---

## 🐛 常见问题

### Q: 启动时报错 "LEGAL_VECTOR_DB_PATH 不存在"

**A**: 确保已运行构建脚本并设置环境变量
```bash
export LEGAL_VECTOR_DB_PATH=/home/oslab/dc/temp/backend/data/vector_db
python app.py
```

### Q: 构建向量库很慢

**A**: 这是正常的。优化方法：
- 使用 GPU（默认启用，需 CUDA）
- 减少文件数量（分批处理）

### Q: 查询没有返回结果

**A**: 检查查询格式
- ✅ 正确：《合同法》第六十条
- ❌ 错误：合同法 60条

### Q: 精确检索总是失败

**A**: 可能原因
- JSON 中法律名称格式不一致
- 法条号转换有问题
- 调整 `extract_simple_law_name()` 正则

---

## 📊 性能参考

| 操作 | 耗时 | 说明 |
|------|------|------|
| 向量库构建 | 5-10 min | 首次，45k 文档 |
| 向量库加载 | 2-3 sec | 每次启动 |
| 精确检索 | <1 ms | 线性查询 |
| 模糊检索 | 100-500 ms | 向量相似度 |

---

## 🔄 与 DeepResearch 对比

| 特性 | Deep Research | Legal Research |
|------|----------------|-----------------|
| 数据源 | 网络搜索 | 向量数据库 |
| 响应时间 | 分钟级 | 毫秒级 |
| 准确度 | 高 | 很高 |
| 场景 | 深度研究 | 快速查询 |

---

## ✅ 检查清单

部署前确认：

- [ ] 准备好 JSON 法律数据
- [ ] 运行了 `build_vector_db.py`
- [ ] 设置了 `LEGAL_VECTOR_DB_PATH`
- [ ] 后端成功启动
- [ ] 前端能访问后端 API
- [ ] 测试查询返回结果

---

## 💡 下一步

1. **基础使用**
   - 在前端页面进行法律查询测试
   - 验证精确和模糊检索功能

2. **集成应用**
   - 在其他模块中调用 legal_research API
   - 与 deep_research、legal_consultation 结合

3. **性能优化**
   - 考虑实现查询缓存
   - 调整 FAISS 索引类型

4. **功能扩展**
   - 添加法律类别过滤
   - 实现 LLM 答案生成
   - 支持导出 PDF

---

**快速启动完成！** 🚀

有任何问题，参考 `backend/modules/legal_research/README.md` 获得完整文档。
