import os
from typing import List, Dict, Any, Optional
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
from openai import OpenAI
from dotenv import load_dotenv
from dashscope import Generation

from .debate.models import StanceType
from .config import settings
from .clients import get_qdrant_client

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")

COLLECTION_CHUNKS = "debate_chunks"
COLLECTION_PROPOSITIONS = "debate_propositions"
COLLECTION_THEORY = "theory"
COLLECTION_MOMENT = "moment"


def get_embedding(text: str) -> List[float]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


class DebateRetriever:
    def __init__(self):
        self.client = get_qdrant_client()
        self.api_key = settings.api_key
        self.model = settings.llm_model
    
    def retrieve_for_debate(
        self,
        topic: str,
        stance_type: StanceType,
        role: str,
        my_position: str,
        theory_modules: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if self._should_block_retrieval(stance_type, role):
            return []
        
        results = []
        results.extend(self._retrieve_propositions(topic, my_position, theory_modules, top_k=2))
        results.extend(self._retrieve_chunks(topic, theory_modules, top_k=2))
        results.extend(self._retrieve_theory(topic, top_k=1))
        
        return self._deduplicate_and_rank(results, top_k)
    
    def _should_block_retrieval(self, stance_type: StanceType, role: str) -> bool:
        if stance_type == StanceType.NEUTRAL:
            return False
        if stance_type == StanceType.ALIGNED_PRO and role == "antagonist":
            return True
        if stance_type == StanceType.ALIGNED_CON and role == "protagonist":
            return True
        return False
    
    def _retrieve_propositions(
        self,
        topic: str,
        my_position: str,
        theory_modules: Optional[List[str]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        query_vector = get_embedding(topic)
        
        must_conditions = []
        if theory_modules:
            must_conditions.append(
                FieldCondition(key="theory_module", match=MatchAny(any=theory_modules))
            )
        
        res = self.client.query_points(
            collection_name=COLLECTION_PROPOSITIONS,
            query=query_vector,
            query_filter=Filter(must=must_conditions) if must_conditions else None,
            limit=top_k,
            with_payload=True
        )
        
        formatted = []
        for p in res.points:
            payload = p.payload or {}
            proposition = payload.get("proposition", "")
            
            angle_type = self._determine_angle_type(proposition, my_position)
            angle_key = "support_angle" if angle_type == "support" else "refute_angle"
            
            formatted.append({
                "type": "proposition",
                "proposition": proposition,
                "angle": payload.get(angle_key, ""),
                "angle_type": angle_type,
                "source": f"{payload.get('author', '')}《{payload.get('source_title', '')}》",
                "theory_module": payload.get("theory_module", ""),
                "score": p.score
            })
        
        return formatted
    
    def _retrieve_chunks(
        self,
        topic: str,
        theory_modules: Optional[List[str]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        query_vector = get_embedding(topic)
        
        must_conditions = []
        if theory_modules:
            must_conditions.append(
                FieldCondition(key="theory_modules", match=MatchAny(any=theory_modules))
            )
        
        res = self.client.query_points(
            collection_name=COLLECTION_CHUNKS,
            query=query_vector,
            query_filter=Filter(must=must_conditions) if must_conditions else None,
            limit=top_k,
            with_payload=True
        )
        
        formatted = []
        for p in res.points:
            payload = p.payload or {}
            formatted.append({
                "type": "chunk",
                "text": payload.get("text", ""),
                "source": f"{payload.get('author', '')}《{payload.get('source_title', '')}》",
                "theory_modules": payload.get("theory_modules", []),
                "score": p.score
            })
        
        return formatted
    
    def _retrieve_theory(
        self,
        topic: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        query_vector = get_embedding(topic)
        
        res = self.client.query_points(
            collection_name=COLLECTION_THEORY,
            query=query_vector,
            limit=top_k,
            with_payload=True
        )
        
        formatted = []
        for p in res.points:
            payload = p.payload or {}
            formatted.append({
                "type": "theory",
                "content": payload.get("content_chunk", payload.get("Content", "")),
                "source": payload.get("source", "理论文献"),
                "chapter": payload.get("Chapter", ""),
                "subsection": payload.get("Subsection", ""),
                "score": p.score
            })
        
        return formatted
    
    def _determine_angle_type(self, proposition: str, my_position: str) -> str:
        prompt = f"""判断以下命题与立场的关系：

命题：{proposition}
己方立场：{my_position}

请判断该命题是"支持"还是"反对"己方立场。
只回答"支持"或"反对"，不要其他内容。"""

        try:
            response = Generation.call(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.api_key,
                result_format="message",
            )
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                return "support" if "支持" in content else "refute"
        except:
            pass
        
        return "support"
    
    def _deduplicate_and_rank(
        self,
        results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for r in results:
            key = r.get("proposition", "") or r.get("text", "") or r.get("content", "")
            key = key[:50]
            if key not in seen:
                seen.add(key)
                unique.append(r)
        
        unique.sort(key=lambda x: x.get("score", 0), reverse=True)
        return unique[:top_k]
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        collection_name: str = COLLECTION_CHUNKS
    ) -> List[Dict[str, Any]]:
        query_vector = get_embedding(query)
        
        res = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True
        )
        
        references = []
        for p in res.points:
            payload = p.payload or {}
            
            # 根据集合类型获取正确的内容字段
            if collection_name == COLLECTION_PROPOSITIONS:
                content = payload.get("proposition", "")
                source = f"{payload.get('author', '')}《{payload.get('source_title', '')}》"
            elif collection_name == COLLECTION_CHUNKS:
                content = payload.get("text", "")
                source = f"{payload.get('author', '')}《{payload.get('source_title', '')}》"
            else:
                content = payload.get("content", payload.get("content_chunk", ""))
                source = payload.get("source", "未知来源")
            
            references.append({
                "content": content,
                "source": source,
                "score": p.score
            })
        
        return references
    
    def retrieve_by_category(
        self,
        query: str,
        category: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        query_vector = get_embedding(query)
        
        res = self.client.query_points(
            collection_name=COLLECTION_CHUNKS,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="category",
                        match=MatchValue(value=category)
                    )
                ]
            ),
            limit=top_k,
            with_payload=True
        )
        
        references = []
        for p in res.points:
            payload = p.payload or {}
            references.append({
                "content": payload.get("content", ""),
                "source": payload.get("source", "未知来源"),
                "category": category,
                "score": p.score
            })
        
        return references
    
    def retrieve_propositions(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        return self.retrieve(query, top_k, COLLECTION_PROPOSITIONS)
    
    def multi_path_retrieve(
        self,
        query: str,
        top_k_per_path: int = 2
    ) -> List[Dict[str, Any]]:
        all_results = []
        
        path1 = self.retrieve(query, top_k_per_path, COLLECTION_CHUNKS)
        for r in path1:
            r["path"] = "semantic_chunks"
        all_results.extend(path1)
        
        path2 = self.retrieve_propositions(query, top_k_per_path)
        for r in path2:
            r["path"] = "propositions"
        all_results.extend(path2)
        
        categories = ["马克思主义基本原理", "马克思主义哲学", "政治经济学", "科学社会主义"]
        for cat in categories:
            path_result = self.retrieve_by_category(query, cat, top_k_per_path=1)
            for r in path_result:
                r["path"] = f"category_{cat}"
            all_results.extend(path_result)
        
        seen = set()
        unique_results = []
        for r in all_results:
            content_hash = hash(r.get("content", "")[:100])
            if content_hash not in seen:
                seen.add(content_hash)
                unique_results.append(r)
        
        unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return unique_results[:top_k_per_path * 4]


def retrieve_for_debate(
    topic: str,
    stance: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    retriever = DebateRetriever()
    query = f"{topic} {stance}"
    return retriever.multi_path_retrieve(query, top_k_per_path=2)[:top_k]


if __name__ == "__main__":
    retriever = DebateRetriever()
    results = retriever.retrieve("实践是检验真理的唯一标准", top_k=3)
    for r in results:
        print(f"来源: {r['source']}")
        print(f"内容: {r['content'][:100]}...")
        print(f"得分: {r['score']}")
        print("-" * 50)
