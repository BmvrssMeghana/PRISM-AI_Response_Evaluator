"""
PRISM — Agent Pipeline Unit Tests
Uses unittest standard library to mock call_llm and test orchestrator logic.
"""
import unittest
from unittest.mock import patch, AsyncMock
import asyncio

# Setup mock modules for testing
class TestEvaluationPipeline(unittest.IsolatedAsyncioTestCase):

    @patch("services.agents.call_llm")
    async def test_claim_extractor(self, mock_call):
        from services.agents import extract_claims
        mock_call.return_value = {"claims": ["Factual claim 1", "Factual claim 2"]}
        
        claims = await extract_claims("This is a response containing two claims.")
        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0], "Factual claim 1")

    @patch("services.agents.call_llm")
    async def test_relevance_agent(self, mock_call):
        from services.agents import evaluate_relevance
        mock_call.return_value = {"score": 9.5, "justification": "Very relevant response"}
        
        res = await evaluate_relevance("What is Python?", "Python is a programming language.")
        self.assertEqual(res["score"], 9.5)
        self.assertEqual(res["justification"], "Very relevant response")

    @patch("services.agents.call_llm")
    async def test_accuracy_agent(self, mock_call):
        from services.agents import evaluate_accuracy
        mock_call.return_value = {
            "score": 10.0,
            "justification": "All facts match source documentation.",
            "verifications": [
                {"claim": "Claim 1", "status": "supported", "evidence": "Confirmed by page 4"}
            ]
        }
        
        res = await evaluate_accuracy(["Claim 1"], [{"text": "Passage text", "dataset": "squad"}])
        self.assertEqual(res["score"], 10.0)
        self.assertEqual(res["verifications"][0]["status"], "supported")

    @patch("services.agents.call_llm")
    async def test_safety_sentinel_clean(self, mock_call):
        from services.agents import evaluate_safety
        mock_call.return_value = {"vetoed": False, "reason": "Clean"}
        
        res = await evaluate_safety("How do I make cookies?", "Mix flour, sugar, and butter.")
        self.assertFalse(res["vetoed"])
        self.assertEqual(res["reason"], "Clean")

    @patch("services.agents.call_llm")
    async def test_safety_sentinel_veto(self, mock_call):
        from services.agents import evaluate_safety
        mock_call.return_value = {"vetoed": True, "reason": "Harmful instruction: explosive materials"}
        
        res = await evaluate_safety("How do I make a bomb?", "Step 1: Get chemicals...")
        self.assertTrue(res["vetoed"])
        self.assertEqual(res["reason"], "Harmful instruction: explosive materials")


if __name__ == "__main__":
    unittest.main()
