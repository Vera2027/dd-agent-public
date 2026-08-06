from __future__ import annotations

from collections import defaultdict

from dd_agent.kb.index import LocalKnowledgeBase
from dd_agent.reporting.models import EvidenceItem, ModuleSpec


class ModuleEvidenceRetriever:
    def __init__(self, kb: LocalKnowledgeBase) -> None:
        self.kb = kb

    def retrieve(self, spec: ModuleSpec, *, top_k_per_query: int = 5, final_top_k: int = 8) -> list[EvidenceItem]:
        aggregated: dict[str, dict] = {}
        hit_counts: defaultdict[str, int] = defaultdict(int)

        for query in spec.search_queries:
            results = self.kb.search(query, top_k=top_k_per_query)
            for result in results:
                hit_counts[result.chunk_id] += 1
                if result.chunk_id not in aggregated:
                    aggregated[result.chunk_id] = {
                        'score': result.score,
                        'document_name': result.document_name,
                        'locator_type': result.locator_type,
                        'locator_value': result.locator_value,
                        'text': result.text,
                        'metadata': result.metadata,
                    }
                else:
                    aggregated[result.chunk_id]['score'] = max(aggregated[result.chunk_id]['score'], result.score)

        ranked = sorted(
            aggregated.items(),
            key=lambda kv: (kv[1]['score'] + 0.01 * hit_counts[kv[0]], hit_counts[kv[0]], len(kv[1]['text'])),
            reverse=True,
        )[:final_top_k]

        items: list[EvidenceItem] = []
        for chunk_id, payload in ranked:
            items.append(
                EvidenceItem(
                    chunk_id=chunk_id,
                    score=float(payload['score']),
                    document_name=payload['document_name'],
                    locator_type=payload['locator_type'],
                    locator_value=int(payload['locator_value']),
                    text=payload['text'],
                    support=f'支持模块“{spec.module_name}”的候选证据',
                    metadata={**payload.get('metadata', {}), 'query_hit_count': hit_counts[chunk_id]},
                )
            )
        return items
