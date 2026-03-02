# RAG在DMFB项目中的实现指南

> 详细解释如何在你的项目中实现Retrieval-Augmented Generation (RAG)

---

## 一、RAG整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAG系统架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  【离线阶段：构建知识库】                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │  历史问题    │ → │  编码器     │ → │  向量数据库(FAISS)  │ │
│  │  +解决方案   │    │ (Embedding) │    │                     │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│         ▲                                                      │
│         │                                                      │
│  【在线阶段：检索增强】                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │  新问题      │ → │  相似度检索  │ → │  Top-K相似案例      │ │
│  │  (查询)     │    │             │    │                     │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│                                                 │               │
│                                                 ▼               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    LLM (GPT-4/Claude)                      │ │
│  │  Prompt: 新问题描述 + 相似案例示例 → 生成解决方案          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、具体实现步骤

### 步骤1：安装依赖

```bash
pip install faiss-cpu  # 或 faiss-gpu（如果有GPU）
pip install sentence-transformers  # 文本编码模型
pip install chromadb  # 备选方案
```

### 步骤2：定义数据结构

```python
# src/agents/rag/types.py

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np


@dataclass
class RAGExample:
    """RAG检索的示例数据结构"""
    example_id: str  # 唯一标识

    # 问题描述（用于检索匹配）
    problem_text: str  # 文本化的问题描述
    problem_vector: Optional[np.ndarray] = None  # 编码后的向量

    # 完整的问题数据
    num_operations: int  # 操作数量
    dag_structure: str  # DAG结构描述（如"linear", "parallel", "fork_join"）
    chip_size: tuple  # (width, height)

    # 解决方案（作为Few-shot示例）
    solution: Dict[str, Any]  # 布局/调度/路由方案
    makespan: int  # 解的质量

    # 元数据
    source: str  # "ga", "sa", "ilp", "human"
    tags: List[str]  # ["small", "pcr", "high_quality"]


@dataclass
class RAGQuery:
    """查询数据结构"""
    problem: 'Problem'  # 你的Problem类
    top_k: int = 5  # 检索Top-K个相似案例
    filters: Optional[Dict] = None  # 过滤条件
```

### 步骤3：实现编码器

```python
# src/agents/rag/encoder.py

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List


class DMFBEncoder:
    """将DMFB问题编码为向量的编码器"""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        初始化编码器

        Args:
            model_name: 预训练的sentence-transformer模型
                       'all-MiniLM-L6-v2' - 轻量级，384维
                       'all-mpnet-base-v2' - 更好质量，768维
        """
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def encode_problem(self, problem: 'Problem') -> np.ndarray:
        """
        将Problem对象编码为向量

        策略：将问题的关键特征转换为文本，然后编码
        """
        # 构建问题描述文本
        description = self._problem_to_text(problem)

        # 编码为向量
        embedding = self.model.encode(description)
        return embedding

    def _problem_to_text(self, problem: 'Problem') -> str:
        """
        将Problem对象转换为文本描述

        这是RAG的关键：如何描述问题决定检索质量
        """
        parts = []

        # 1. 基本信息
        parts.append(f"Chip size: {problem.chip_width}x{problem.chip_height}")
        parts.append(f"Number of operations: {len(problem.operations)}")

        # 2. DAG结构特征
        dag_features = self._analyze_dag_structure(problem)
        parts.append(f"DAG pattern: {dag_features['pattern']}")
        parts.append(f"Max depth: {dag_features['max_depth']}")
        parts.append(f"Parallelism: {dag_features['parallelism']}")

        # 3. 模块类型分布
        module_counts = {}
        for op in problem.operations:
            mod_type = op.module_type if hasattr(op, 'module_type') else 'general'
            module_counts[mod_type] = module_counts.get(mod_type, 0) + 1

        parts.append(f"Module distribution: {module_counts}")

        # 4. 关键路径信息
        cpl = problem.critical_path_length if hasattr(problem, 'critical_path_length') else 'unknown'
        parts.append(f"Critical path length: {cpl}")

        return "; ".join(parts)

    def _analyze_dag_structure(self, problem: 'Problem') -> dict:
        """分析DAG结构特征"""
        n_ops = len(problem.operations)

        # 计算入度和出度
        in_degrees = [0] * n_ops
        out_degrees = [0] * n_ops

        for op in problem.operations:
            out_degrees[op.id] = len(op.successors)
            for succ_id in op.successors:
                in_degrees[succ_id] += 1

        # 判断结构模式
        sources = sum(1 for d in in_degrees if d == 0)
        sinks = sum(1 for d in out_degrees if d == 0)

        if sources == 1 and sinks == 1 and max(out_degrees) <= 1:
            pattern = "linear"
        elif sources > 1 and sinks == 1:
            pattern = "join"
        elif sources == 1 and sinks > 1:
            pattern = "fork"
        elif sources > 1 and sinks > 1:
            pattern = "fork_join"
        else:
            pattern = "complex"

        # 计算深度（最长路径）
        max_depth = self._compute_dag_depth(problem)

        # 计算并行度
        parallelism = n_ops / max_depth if max_depth > 0 else 1

        return {
            'pattern': pattern,
            'max_depth': max_depth,
            'parallelism': round(parallelism, 2)
        }

    def _compute_dag_depth(self, problem: 'Problem') -> int:
        """计算DAG深度（最长路径）"""
        # 使用动态规划计算每个节点的深度
        depth = {}

        def get_depth(op_id):
            if op_id in depth:
                return depth[op_id]

            op = problem.operations[op_id]
            if not op.predecessors:
                depth[op_id] = 1
            else:
                depth[op_id] = 1 + max(get_depth(p) for p in op.predecessors)
            return depth[op_id]

        max_depth = max(get_depth(op.id) for op in problem.operations)
        return max_depth

    def encode_problems_batch(self, problems: List['Problem']) -> np.ndarray:
        """批量编码多个问题"""
        texts = [self._problem_to_text(p) for p in problems]
        embeddings = self.model.encode(texts, show_progress_bar=True)
        return embeddings
```

### 步骤4：实现向量数据库

```python
# src/agents/rag/vector_store.py

import faiss
import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json


class DMFBVectorStore:
    """基于FAISS的向量数据库"""

    def __init__(self, embedding_dim: int, index_type: str = 'flat'):
        """
        初始化向量数据库

        Args:
            embedding_dim: 向量维度（如384或768）
            index_type: 'flat'（精确）, 'ivf'（倒排文件）, 'hnsw'（近似）
        """
        self.embedding_dim = embedding_dim
        self.index_type = index_type
        self.index = None
        self.examples: List[RAGExample] = []  # 存储完整示例数据
        self.example_id_to_index: Dict[str, int] = {}  # ID到索引的映射

        self._create_index()

    def _create_index(self):
        """创建FAISS索引"""
        if self.index_type == 'flat':
            # 精确搜索，适合小数据集（<10K）
            self.index = faiss.IndexFlatIP(self.embedding_dim)  # 内积相似度
        elif self.index_type == 'ivf':
            # 倒排文件，适合中等数据集（10K-1M）
            quantizer = faiss.IndexFlatIP(self.embedding_dim)
            nlist = 100  # 聚类中心数
            self.index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, nlist)
        elif self.index_type == 'hnsw':
            # HNSW图索引，适合大数据集，快速近似搜索
            self.index = faiss.IndexHNSWFlat(self.embedding_dim, 32)
            self.index.hnsw.efConstruction = 200
        else:
            raise ValueError(f"Unknown index type: {self.index_type}")

    def add_examples(self, examples: List[RAGExample]):
        """
        添加示例到数据库

        Args:
            examples: RAGExample列表
        """
        if not examples:
            return

        # 收集向量
        vectors = []
        for ex in examples:
            if ex.problem_vector is None:
                raise ValueError(f"Example {ex.example_id} has no vector")
            vectors.append(ex.problem_vector)

            # 建立ID映射
            self.example_id_to_index[ex.example_id] = len(self.examples)
            self.examples.append(ex)

        # 转换为numpy数组并归一化（用于余弦相似度）
        vectors_np = np.array(vectors).astype('float32')
        faiss.normalize_L2(vectors_np)  # L2归一化

        # 添加到索引
        if self.index_type == 'ivf' and not self.index.is_trained:
            # IVF索引需要先训练
            self.index.train(vectors_np)

        self.index.add(vectors_np)

    def search(self, query_vector: np.ndarray, top_k: int = 5,
               filters: Optional[Dict] = None) -> List[Tuple[RAGExample, float]]:
        """
        搜索相似示例

        Args:
            query_vector: 查询向量
            top_k: 返回最相似的K个
            filters: 过滤条件，如{"min_makespan": 30, "source": "ga"}

        Returns:
            [(example, similarity_score), ...]
        """
        # 归一化查询向量
        query_np = np.array([query_vector]).astype('float32')
        faiss.normalize_L2(query_np)

        # 搜索（获取更多结果以便过滤）
        search_k = min(top_k * 3, len(self.examples)) if filters else top_k
        distances, indices = self.index.search(query_np, search_k)

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx == -1:  # FAISS返回-1表示没有更多结果
                continue

            example = self.examples[idx]

            # 应用过滤条件
            if filters and not self._apply_filters(example, filters):
                continue

            # FAISS内积归一化后等价于余弦相似度
            results.append((example, float(dist)))

            if len(results) >= top_k:
                break

        return results

    def _apply_filters(self, example: RAGExample, filters: Dict) -> bool:
        """应用过滤条件"""
        if 'min_makespan' in filters and example.makespan < filters['min_makespan']:
            return False
        if 'max_makespan' in filters and example.makespan > filters['max_makespan']:
            return False
        if 'source' in filters and example.source != filters['source']:
            return False
        if 'dag_pattern' in filters and example.dag_structure != filters['dag_pattern']:
            return False
        if 'min_operations' in filters and example.num_operations < filters['min_operations']:
            return False
        if 'max_operations' in filters and example.num_operations > filters['max_operations']:
            return False
        return True

    def save(self, directory: Path):
        """保存索引和数据到磁盘"""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        # 保存FAISS索引
        faiss.write_index(self.index, str(directory / 'faiss.index'))

        # 保存示例数据
        with open(directory / 'examples.pkl', 'wb') as f:
            pickle.dump({
                'examples': self.examples,
                'id_to_index': self.example_id_to_index
            }, f)

        # 保存元数据
        metadata = {
            'embedding_dim': self.embedding_dim,
            'index_type': self.index_type,
            'num_examples': len(self.examples)
        }
        with open(directory / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)

    @classmethod
    def load(cls, directory: Path) -> 'DMFBVectorStore':
        """从磁盘加载索引和数据"""
        directory = Path(directory)

        # 加载元数据
        with open(directory / 'metadata.json', 'r') as f:
            metadata = json.load(f)

        # 创建实例
        store = cls(metadata['embedding_dim'], metadata['index_type'])

        # 加载索引
        store.index = faiss.read_index(str(directory / 'faiss.index'))

        # 加载示例数据
        with open(directory / 'examples.pkl', 'rb') as f:
            data = pickle.load(f)
            store.examples = data['examples']
            store.example_id_to_index = data['id_to_index']

        return store

    def get_stats(self) -> Dict:
        """获取数据库统计信息"""
        return {
            'total_examples': len(self.examples),
            'embedding_dim': self.embedding_dim,
            'index_type': self.index_type,
            'sources': list(set(ex.source for ex in self.examples)),
            'dag_patterns': list(set(ex.dag_structure for ex in self.examples))
        }
```

### 步骤5：实现RAG检索器

```python
# src/agents/rag/retriever.py

from typing import List, Optional
from pathlib import Path


class RAGRetriever:
    """RAG检索器：检索相似案例用于Few-shot学习"""

    def __init__(self,
                 encoder: DMFBEncoder,
                 vector_store: DMFBVectorStore,
                 cache_dir: Optional[Path] = None):
        """
        初始化RAG检索器

        Args:
            encoder: 问题编码器
            vector_store: 向量数据库
            cache_dir: 缓存目录（可选）
        """
        self.encoder = encoder
        self.vector_store = vector_store
        self.cache_dir = cache_dir

    def retrieve(self,
                 problem: 'Problem',
                 top_k: int = 5,
                 filters: Optional[dict] = None) -> List[RAGExample]:
        """
        检索相似案例

        Args:
            problem: 当前问题
            top_k: 检索数量
            filters: 过滤条件

        Returns:
            相似案例列表（按相似度排序）
        """
        # 1. 编码当前问题
        query_vector = self.encoder.encode_problem(problem)

        # 2. 检索相似案例
        results = self.vector_store.search(query_vector, top_k, filters)

        # 3. 返回示例（去掉相似度分数）
        similar_examples = [ex for ex, _ in results]

        return similar_examples

    def build_few_shot_prompt(self,
                              problem: 'Problem',
                              task_type: str = 'placement',
                              top_k: int = 3) -> str:
        """
        构建包含Few-shot示例的Prompt

        Args:
            problem: 当前问题
            task_type: 'placement', 'scheduling', 'routing'
            top_k: 示例数量

        Returns:
            完整的Prompt文本
        """
        # 1. 检索相似案例
        # 过滤条件：只检索相同规模的案例
        filters = {
            'min_operations': max(1, len(problem.operations) - 5),
            'max_operations': len(problem.operations) + 5
        }

        similar_examples = self.retrieve(problem, top_k, filters)

        # 2. 构建Prompt
        prompt_parts = []

        # 系统指令
        prompt_parts.append(
            f"你是一名DMFB设计专家。请参考以下{len(similar_examples)}个相似案例，"
            f"为当前问题设计最优的{task_type}方案。"
        )
        prompt_parts.append("\n" + "="*50 + "\n")

        # Few-shot示例
        prompt_parts.append("【参考案例】\n")
        for i, example in enumerate(similar_examples, 1):
            prompt_parts.append(f"\n案例{i}:")
            prompt_parts.append(f"问题: {example.problem_text}")
            prompt_parts.append(f"解决方案质量: makespan={example.makespan}")

            # 根据任务类型选择展示方案的部分
            if task_type == 'placement' and 'placements' in example.solution:
                placements = example.solution['placements']
                prompt_parts.append(f"布局方案: {placements}")
            elif task_type == 'scheduling' and 'schedule' in example.solution:
                schedule = example.solution['schedule']
                prompt_parts.append(f"调度方案: {schedule}")
            elif task_type == 'routing' and 'routes' in example.solution:
                routes = example.solution['routes']
                prompt_parts.append(f"路由方案: {routes}")

        prompt_parts.append("\n" + "="*50 + "\n")

        # 当前问题
        prompt_parts.append("【当前问题】\n")
        prompt_parts.append(self.encoder._problem_to_text(problem))
        prompt_parts.append("\n请根据参考案例的经验，为当前问题设计最优方案。\n")

        return "\n".join(prompt_parts)

    def add_solution_to_knowledge_base(self,
                                       problem: 'Problem',
                                       solution: dict,
                                       makespan: int,
                                       source: str = 'llm'):
        """
        将新的解决方案添加到知识库（在线学习）

        Args:
            problem: 问题
            solution: 解决方案
            makespan: 解的质量
            source: 来源标识
        """
        # 1. 编码问题
        problem_vector = self.encoder.encode_problem(problem)
        problem_text = self.encoder._problem_to_text(problem)

        # 2. 创建示例
        example = RAGExample(
            example_id=f"{source}_{len(self.vector_store.examples)}",
            problem_text=problem_text,
            problem_vector=problem_vector,
            num_operations=len(problem.operations),
            dag_structure='unknown',  # 可以从problem中获取
            chip_size=(problem.chip_width, problem.chip_height),
            solution=solution,
            makespan=makespan,
            source=source,
            tags=[source, 'online_added']
        )

        # 3. 添加到向量数据库
        self.vector_store.add_examples([example])
```

### 步骤6：构建知识库（离线处理）

```python
# scripts/build_rag_knowledge_base.py

"""
构建RAG知识库脚本

用法:
    python scripts/build_rag_knowledge_base.py \
        --data data/training \
        --output data/rag_kb \
        --encoder all-MiniLM-L6-v2
"""

import json
import pickle
from pathlib import Path
from tqdm import tqdm
import sys
sys.path.insert(0, 'src')

from baseline.problem import Problem
from agents.rag.encoder import DMFBEncoder
from agents.rag.vector_store import DMFBVectorStore, RAGExample
from agents.rag.types import RAGExample


def load_solutions(data_dir: Path) -> list:
    """加载baseline生成的解决方案"""
    solutions = []

    for solution_file in data_dir.glob('*_solution.json'):
        with open(solution_file, 'r') as f:
            data = json.load(f)
            solutions.append(data)

    return solutions


def build_knowledge_base(data_dir: Path,
                         output_dir: Path,
                         encoder_model: str = 'all-MiniLM-L6-v2'):
    """构建知识库"""

    print(f"1. 初始化编码器: {encoder_model}")
    encoder = DMFBEncoder(encoder_model)

    print(f"2. 初始化向量数据库 (dim={encoder.embedding_dim})")
    vector_store = DMFBVectorStore(
        embedding_dim=encoder.embedding_dim,
        index_type='flat'  # 小数据集用flat即可
    )

    print(f"3. 加载解决方案从: {data_dir}")
    solutions = load_solutions(data_dir)
    print(f"   找到 {len(solutions)} 个解决方案")

    print("4. 编码并添加到知识库...")
    examples = []

    for sol_data in tqdm(solutions):
        # 加载问题
        problem = Problem.from_dict(sol_data['problem'])

        # 编码问题
        problem_vector = encoder.encode_problem(problem)
        problem_text = encoder._problem_to_text(problem)

        # 创建RAG示例
        example = RAGExample(
            example_id=sol_data.get('id', f'ex_{len(examples)}'),
            problem_text=problem_text,
            problem_vector=problem_vector,
            num_operations=len(problem.operations),
            dag_structure=sol_data.get('dag_pattern', 'unknown'),
            chip_size=(problem.chip_width, problem.chip_height),
            solution=sol_data['solution'],
            makespan=sol_data['makespan'],
            source=sol_data.get('source', 'unknown'),
            tags=sol_data.get('tags', [])
        )

        examples.append(example)

    # 批量添加到向量数据库
    print(f"5. 添加 {len(examples)} 个示例到向量数据库")
    vector_store.add_examples(examples)

    # 保存
    print(f"6. 保存知识库到: {output_dir}")
    vector_store.save(output_dir)

    # 打印统计
    stats = vector_store.get_stats()
    print(f"\n知识库统计:")
    print(f"  - 总示例数: {stats['total_examples']}")
    print(f"  - 向量维度: {stats['embedding_dim']}")
    print(f"  - 索引类型: {stats['index_type']}")
    print(f"  - 数据来源: {stats['sources']}")
    print(f"  - DAG模式: {stats['dag_patterns']}")

    print("\n✅ 知识库构建完成!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True,
                       help='包含解决方案的目录')
    parser.add_argument('--output', type=Path, required=True,
                       help='知识库输出目录')
    parser.add_argument('--encoder', type=str, default='all-MiniLM-L6-v2',
                       help='编码器模型名称')

    args = parser.parse_args()

    build_knowledge_base(args.data, args.output, args.encoder)
```

### 步骤7：在Agent中使用RAG

```python
# src/agents/placement/agent.py (使用RAG的版本)

from agents.rag.retriever import RAGRetriever


class PlacementAgent:
    """使用RAG增强的Placement Agent"""

    def __init__(self, llm_client, retriever: RAGRetriever):
        self.llm_client = llm_client
        self.retriever = retriever

    def solve(self, problem: Problem, use_rag: bool = True) -> dict:
        """
        解决布局问题

        Args:
            problem: DMFB问题
            use_rag: 是否使用RAG增强
        """
        if use_rag:
            # 使用RAG构建prompt
            prompt = self.retriever.build_few_shot_prompt(
                problem=problem,
                task_type='placement',
                top_k=3  # 使用3个相似案例
            )
        else:
            # 不使用RAG，使用基础prompt
            prompt = self._build_basic_prompt(problem)

        # 调用LLM
        response = self.llm_client.generate(prompt)

        # 解析响应
        placement = self._parse_placement(response)

        return placement

    def _build_basic_prompt(self, problem: Problem) -> str:
        """构建基础prompt（无RAG）"""
        # 基础prompt实现...
        pass
```

---

## 三、完整使用流程

```python
# 示例：完整使用RAG的流程

from agents.rag.encoder import DMFBEncoder
from agents.rag.vector_store import DMFBVectorStore
from agents.rag.retriever import RAGRetriever

# 1. 初始化组件
encoder = DMFBEncoder('all-MiniLM-L6-v2')
vector_store = DMFBVectorStore(embedding_dim=384, index_type='flat')

# 2. 构建知识库（离线，只需做一次）
examples = []  # 从baseline结果中加载
for solution in baseline_solutions:
    example = RAGExample(
        problem_vector=encoder.encode_problem(solution.problem),
        solution=solution.placement,
        makespan=solution.makespan,
        ...
    )
    examples.append(example)

vector_store.add_examples(examples)
vector_store.save(Path('data/rag_kb'))

# 3. 在线检索（每次Agent调用时使用）
retriever = RAGRetriever(encoder, vector_store)

# 4. 在Agent中使用
agent = PlacementAgent(llm_client, retriever)
placement = agent.solve(problem, use_rag=True)
```

---

## 四、关键技巧与注意事项

### 4.1 问题描述文本的设计

RAG的效果很大程度上取决于`problem_to_text()`的质量：

```python
# 好的描述：包含结构特征
def good_description(problem):
    return (
        f"10x10 chip, 15 operations, "
        f"fork-join pattern, critical path length 8, "
        f"3 mixers and 2 heaters"
    )

# 差的描述：只有基本信息
def bad_description(problem):
    return f"Problem with 15 operations on 10x10 chip"
```

### 4.2 相似度阈值

```python
def retrieve_with_threshold(retriever, problem, threshold=0.7):
    """只返回相似度超过阈值的案例"""
    examples = retriever.retrieve(problem, top_k=5)

    # 计算相似度（实际中vector_store.search已经返回）
    filtered = [ex for ex in examples if ex.similarity > threshold]

    return filtered if filtered else examples[:1]  # 至少返回1个
```

### 4.3 过滤策略

```python
# 根据问题规模过滤
filters = {
    'min_operations': n_ops * 0.5,  # 规模相近
    'max_operations': n_ops * 1.5,
    'dag_pattern': current_pattern,  # 结构相同
}

similar = retriever.retrieve(problem, top_k=5, filters=filters)
```

---

## 五、性能优化

| 优化策略 | 效果 | 实现难度 |
|---------|------|---------|
| 使用HNSW索引 | 搜索速度提升10-100倍 | 低 |
| 向量量化 | 内存减少70% | 中 |
| 缓存热门查询 | 减少重复编码 | 低 |
| 增量更新 | 避免全量重建 | 中 |

---

## 六、总结

RAG在你的项目中的核心价值：

1. **知识复用**：自动找到相似问题的成功解决方案
2. **Few-shot学习**：无需训练，通过示例让LLM快速适应
3. **可解释性**：可以查看"参考了哪些案例"
4. **在线更新**：可以不断添加新的成功案例

**下一步建议**：先实现基础的编码器和向量数据库，然后逐步添加过滤策略和优化。

---

**相关文件**:
- 编码器: `src/agents/rag/encoder.py`
- 向量数据库: `src/agents/rag/vector_store.py`
- 检索器: `src/agents/rag/retriever.py`
- 构建脚本: `scripts/build_rag_knowledge_base.py`
