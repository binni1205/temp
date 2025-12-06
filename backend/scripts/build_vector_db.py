#!/usr/bin/env python3
"""
法律检索向量库构建脚本

用法：
    python scripts/build_vector_db.py \\
        --json-root /path/to/json-laws \\
        --output-path ./data/vector_db

环境变量：
    LEGAL_VECTOR_DB_PATH: 向量库保存路径 (可选)
"""

import os
import sys
import json
import re
from pathlib import Path
from tqdm import tqdm
import argparse

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.legal_research.retriever import (
    chinese_to_arabic,
    get_article_number,
)

try:
    from langchain.docstore.document import Document
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain.vectorstores import FAISS
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请先安装依赖: pip install -r modules/legal_research/requirements.txt")
    sys.exit(1)


def load_json_files(json_root: str) -> list:
    """递归遍历json_root目录，返回所有JSON文件路径"""
    json_files = []
    for root, _, files in os.walk(json_root):
        for file in files:
            if file.lower().endswith(".json"):
                json_files.append(os.path.join(root, file))
    return sorted(json_files)


def flatten_law_json(law_data: dict) -> list:
    """
    将法律JSON数据扁平化为Document对象列表
    
    每个Document的格式：
    page_content = "《法律名称》 第X条: 条款内容"
    metadata = {"law_name", "simple_law_name", "article", "article_num"}
    """
    documents = []
    law_name = law_data.get("law_name", "").strip()
    simple_law_name = law_name.replace("中华人民共和国", "").strip()

    def process_articles(articles: dict):
        """处理条款字典"""
        for art_num, art_content in articles.items():
            norm_art = re.sub(r"\s+", "", art_num)  # 去掉空格
            art_number = get_article_number(norm_art)
            text = f"《{law_name}》 {norm_art}: {art_content}"
            
            documents.append(Document(
                page_content=text,
                metadata={
                    "law_name": law_name,
                    "simple_law_name": simple_law_name,
                    "article": norm_art,
                    "article_num": art_number
                }
            ))

    # 处理顶层articles
    if "articles" in law_data and law_data["articles"]:
        process_articles(law_data["articles"])

    # 处理章节中的articles
    if "chapters" in law_data:
        for chapter, chapter_data in law_data["chapters"].items():
            process_articles(chapter_data.get("articles", {}))
    
    return documents


def build_documents_from_json(json_root: str) -> list:
    """加载json_root下所有JSON文件，扁平化为Document列表"""
    json_files = load_json_files(json_root)
    
    if not json_files:
        print(f"❌ 未找到JSON文件: {json_root}")
        return []
    
    print(f"📂 找到 {len(json_files)} 个JSON文件")
    
    all_docs = []
    for jf in tqdm(json_files, desc="加载JSON文件"):
        try:
            with open(jf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            docs = flatten_law_json(data)
            all_docs.extend(docs)
        except Exception as e:
            print(f"⚠️  处理 {jf} 失败: {e}")
            continue
    
    return all_docs


def build_vector_store(documents: list, output_path: str, use_cuda: bool = True):
    """构建FAISS向量库并保存"""
    if not documents:
        print("❌ 没有文档可处理")
        return None
    
    print(f"\n🔧 构建向量库...")
    print(f"  • 文档数: {len(documents)}")
    
    device = "cuda" if use_cuda else "cpu"
    print(f"  • 设备: {device}")
    print(f"  • 嵌入模型: shibing624/text2vec-base-chinese")
    
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese",
            model_kwargs={"device": device}
        )
        
        print("📌 生成嵌入向量...")
        vector_db = FAISS.from_documents(documents, embeddings)
        
        # 保存向量库
        os.makedirs(output_path, exist_ok=True)
        vector_db.save_local(output_path)
        
        # 保存文档列表用于备用精确检索
        vector_db.documents = documents
        
        print(f"✅ 向量库已保存到: {output_path}")
        return vector_db
    
    except Exception as e:
        print(f"❌ 构建向量库失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description="构建法律检索向量库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python scripts/build_vector_db.py \\
    --json-root /path/to/json-laws \\
    --output-path ./data/vector_db
    
  # 或使用环境变量
  export LEGAL_JSON_ROOT=/path/to/json-laws
  export LEGAL_VECTOR_DB_PATH=./data/vector_db
  python scripts/build_vector_db.py
        """
    )
    
    parser.add_argument(
        '--json-root',
        type=str,
        default=os.getenv('LEGAL_JSON_ROOT', './data/json-laws'),
        help='JSON文件所在目录 (默认: ./data/json-laws)'
    )
    
    parser.add_argument(
        '--output-path',
        type=str,
        default=os.getenv('LEGAL_VECTOR_DB_PATH', './data/vector_db'),
        help='向量库输出路径 (默认: ./data/vector_db)'
    )
    
    parser.add_argument(
        '--no-cuda',
        action='store_true',
        help='使用CPU而不是GPU'
    )
    
    args = parser.parse_args()
    
    json_root = args.json_root
    output_path = args.output_path
    use_cuda = not args.no_cuda
    
    print("=" * 60)
    print("🚀 法律检索向量库构建工具")
    print("=" * 60)
    print(f"📂 JSON文件目录: {json_root}")
    print(f"💾 输出路径: {output_path}")
    print(f"🖥️  使用GPU: {use_cuda}")
    print("=" * 60)
    
    # 验证输入目录
    if not os.path.exists(json_root):
        print(f"❌ 错误: JSON目录不存在 - {json_root}")
        sys.exit(1)
    
    # 加载文档
    documents = build_documents_from_json(json_root)
    if not documents:
        print("❌ 无法加载任何文档")
        sys.exit(1)
    
    print(f"✅ 成功加载 {len(documents)} 个文档")
    
    # 构建向量库
    vector_db = build_vector_store(documents, output_path, use_cuda=use_cuda)
    if vector_db is None:
        sys.exit(1)
    
    # 测试查询
    print("\n" + "=" * 60)
    print("✅ 向量库构建完成！")
    print("=" * 60)
    print("\n💡 后续步骤:")
    print("1. 设置环境变量:")
    print(f"   export LEGAL_VECTOR_DB_PATH={output_path}")
    print("\n2. 启动后端服务:")
    print("   cd backend && python app.py")
    print("\n3. 测试API:")
    print("   curl -X POST http://localhost:8000/api/legal-research/search \\")
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"query": "《合同法》第六十条", "top_k": 3}\'')
    print("=" * 60)


if __name__ == "__main__":
    main()
