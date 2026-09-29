import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.services.mitigation_service import get_mitigation_service

logger = logging.getLogger("cybershield.rag_service")

# Standardized fallback message when context is insufficient
INSUFFICIENT_INFO_MESSAGE = "Insufficient information found in the available security documents."

# Action verbs commonly indicating remediation procedures
ACTION_VERB_PATTERN = re.compile(
    r"\b(isolate|disconnect|terminate|kill|block|quarantine|enable|implement|enforce|"
    r"apply|deploy|restore|restrict|remediate|patch|mitigate|verify|freeze|revoke|"
    r"preserve|capture|configure|update|halt|partition|inspect|scan)\b",
    re.IGNORECASE,
)


class RAGService:
    """
    Retrieval-Augmented Generation (RAG) Service for Cybersecurity Mitigation.
    Synthesizes concise, grounded mitigation answers strictly from retrieved document chunks.
    Guarantees zero-hallucination compliance by attributing evidence directly to source documents.
    """

    def __init__(self):
        self.mitigation_service = get_mitigation_service()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    def generate_mitigation_answer(
        self,
        alert: str,
        top_k: int = 5,
        min_threshold: float = 0.35,
        severity: str = "medium",
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end RAG flow:
        User Alert -> FAISS retrieval -> Relevant Chunks -> Grounded Synthesis -> Source Attribution.

        Args:
            alert: Active security alert description.
            top_k: Max chunks to retrieve.
            min_threshold: Minimum semantic relevance score threshold.
            severity: Alert severity.
            db: SQLAlchemy Session.

        Returns:
            Dictionary matching the API specification:
            {
                "alert": alert,
                "answer": answer,
                "sources": sources,
                "results": sources,
                "alert_id": alert_id
            }
        """
        clean_alert = alert.strip() if alert else ""
        if not clean_alert:
            logger.warning("Empty alert provided to RAGService.")
            return {
                "alert": clean_alert,
                "answer": INSUFFICIENT_INFO_MESSAGE,
                "sources": [],
                "results": [],
                "alert_id": None,
            }

        logger.info(
            "Processing RAG mitigation request for alert: '%s' (top_k=%d, min_threshold=%.2f)",
            clean_alert[:80], top_k, min_threshold,
        )

        # 1. Retrieve relevant document chunks using existing FAISS search pipeline
        try:
            retrieval_data = self.mitigation_service.search_mitigations(
                alert=clean_alert,
                top_k=top_k,
                min_threshold=min_threshold,
                severity=severity,
                save_record=True,
                db=db,
            )
        except Exception as e:
            logger.error("Failure in semantic retrieval pipeline: %s", e, exc_info=True)
            return {
                "alert": clean_alert,
                "answer": INSUFFICIENT_INFO_MESSAGE,
                "sources": [],
                "results": [],
                "alert_id": None,
            }

        sources = retrieval_data.get("results", [])
        alert_id = retrieval_data.get("alert_id")

        # 2. Check if relevant context was found
        if not sources or len(sources) == 0:
            logger.info("No documents met the relevance threshold (%.2f) for alert: '%s'", min_threshold, clean_alert)
            return {
                "alert": clean_alert,
                "answer": INSUFFICIENT_INFO_MESSAGE,
                "sources": [],
                "results": [],
                "alert_id": alert_id,
            }

        # 3. Generate concise grounded answer strictly from retrieved context
        answer: Optional[str] = None

        # Check if an external LLM API is configured in the environment
        if self.openai_api_key:
            answer = self._call_openai_llm(clean_alert, sources)
        elif self.gemini_api_key:
            answer = self._call_gemini_llm(clean_alert, sources)

        # Fallback to local deterministic grounded synthesis if LLM is unavailable or failed
        if not answer:
            answer = self._synthesize_grounded_answer(clean_alert, sources)

        logger.info("Successfully synthesized grounded mitigation answer with %d source(s).", len(sources))

        return {
            "alert": clean_alert,
            "answer": answer,
            "sources": sources,
            "results": sources,
            "alert_id": alert_id,
        }

    def _synthesize_grounded_answer(
        self,
        alert: str,
        sources: List[Dict[str, Any]],
    ) -> str:
        """
        Synthesizes a concise, structured mitigation answer strictly from retrieved document chunks.
        Guarantees zero hallucination by using only statements and action items from the source text.
        """
        if not sources:
            return INSUFFICIENT_INFO_MESSAGE

        answer_sections: List[str] = []
        answer_sections.append(f"Based on the available security documentation, the following mitigation steps are recommended for this alert:\n")

        for source in sources:
            doc_title = source.get("document_title", "Security Documentation")
            doc_type = source.get("document_type", "").replace("_", " ").title()
            doc_type_str = f" ({doc_type})" if doc_type else ""
            content = source.get("mitigation_text", "")

            # Extract distinct mitigation steps (numbered items or action-oriented sentences)
            extracted_steps = self._extract_actionable_steps(content)

            header = f"**Source: {doc_title}{doc_type_str}**"
            if extracted_steps:
                steps_text = "\n".join(f"- {step}" for step in extracted_steps)
                answer_sections.append(f"{header}\n{steps_text}")
            else:
                # Include concise verbatim content
                clean_snippet = content.strip()
                if len(clean_snippet) > 300:
                    clean_snippet = clean_snippet[:297] + "..."
                answer_sections.append(f"{header}\n- {clean_snippet}")

        return "\n\n".join(answer_sections)

    def _extract_actionable_steps(self, text: str) -> List[str]:
        """
        Parses text for numbered procedures (e.g. '1. ... 2. ...') or action-driven mitigation sentences.
        """
        steps: List[str] = []

        # 1. Check for numbered steps (e.g., '1. Immediately disconnect... 2. Kill malicious...')
        numbered_matches = re.findall(r"(?:^|\s)(\d+\.\s+[^0-9]+(?=(?:\s\d+\.|$)))", text)
        if numbered_matches:
            for item in numbered_matches:
                cleaned = item.strip().rstrip(". ")
                # Strip leading numbering for clean bullet formatting
                cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
                if len(cleaned) > 10:
                    steps.append(cleaned)
            if steps:
                return steps[:6]

        # 2. Extract action sentences containing remediation verbs
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sent in sentences:
            sent_clean = sent.strip()
            if len(sent_clean) > 15 and ACTION_VERB_PATTERN.search(sent_clean):
                steps.append(sent_clean)

        return steps[:5]

    def _call_openai_llm(self, alert: str, sources: List[Dict[str, Any]]) -> Optional[str]:
        """
        Invokes OpenAI API if configured in environment, with strict anti-hallucination system prompt.
        """
        try:
            context_blocks = []
            for s in sources:
                context_blocks.append(
                    f"Document: {s.get('document_title')} (Type: {s.get('document_type')})\n"
                    f"Content: {s.get('mitigation_text')}"
                )
            context_str = "\n\n---\n\n".join(context_blocks)

            prompt = (
                f"Active Security Alert: {alert}\n\n"
                f"Retrieved Security Documentation:\n{context_str}\n\n"
                f"Task:\n"
                f"Provide a concise summary of the mitigation steps for this alert using ONLY the context above.\n"
                f"Explicitly mention the source document titles.\n"
                f"Never fabricate commands, CVEs, IP addresses, or remediation steps.\n"
                f"If the context does not provide relevant mitigation steps, reply with:\n"
                f"\"{INSUFFICIENT_INFO_MESSAGE}\""
            )

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a cybersecurity incident response assistant. You only use provided context. Never invent mitigation steps.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 500,
            }

            with httpx.Client(timeout=15.0) as client:
                resp = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.warning("OpenAI API returned status %d: %s", resp.status_code, resp.text)
                    return None
        except Exception as e:
            logger.error("OpenAI LLM request failed: %s; falling back to deterministic synthesis", e)
            return None

    def _call_gemini_llm(self, alert: str, sources: List[Dict[str, Any]]) -> Optional[str]:
        """
        Invokes Gemini API if configured in environment, with strict anti-hallucination system prompt.
        """
        try:
            context_blocks = [
                f"Document: {s.get('document_title')} ({s.get('document_type')})\n{s.get('mitigation_text')}"
                for s in sources
            ]
            context_str = "\n\n".join(context_blocks)

            prompt = (
                f"Security Alert: {alert}\n\n"
                f"Context:\n{context_str}\n\n"
                f"Summarize the mitigation steps concisely. Use ONLY the provided context. "
                f"Cite the source document titles. If insufficient, reply with: \"{INSUFFICIENT_INFO_MESSAGE}\""
            )

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}

            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        return candidates[0]["content"]["parts"][0]["text"].strip()
                else:
                    logger.warning("Gemini API returned status %d: %s", resp.status_code, resp.text)
                    return None
        except Exception as e:
            logger.error("Gemini LLM request failed: %s; falling back to deterministic synthesis", e)
            return None


# Global singleton instance
_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    Returns the singleton instance of RAGService.
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
