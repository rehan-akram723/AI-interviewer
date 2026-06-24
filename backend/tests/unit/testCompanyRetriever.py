# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testCompanyRetriever.py
#
# Unit tests for:
#   - src.modules.retrieval.baseRetriever (BaseRetriever ABC)
#   - src.modules.retrieval.companyRetriever (CompanyRetriever, companyRetriever)
#   - src.agents.companyResearchAgent (companyResearchAgent)
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import patch, MagicMock


# ════════════════════════════════════════════════════════════════════════════════
# BaseRetriever
# ════════════════════════════════════════════════════════════════════════════════

class TestBaseRetriever:

    def test_base_retriever_cannot_be_instantiated_directly(self):
        """BaseRetriever is abstract — direct instantiation must fail."""
        from src.modules.retrieval.baseRetriever import BaseRetriever
        with pytest.raises(TypeError):
            BaseRetriever()

    def test_concrete_subclass_must_implement_retrieve(self):
        """Subclass without retrieve() implementation must fail at instantiation."""
        from src.modules.retrieval.baseRetriever import BaseRetriever

        class IncompleteRetriever(BaseRetriever):
            pass  # retrieve() not implemented

        with pytest.raises(TypeError):
            IncompleteRetriever()

    def test_concrete_subclass_with_retrieve_works(self):
        """Subclass implementing retrieve() should instantiate correctly."""
        from src.modules.retrieval.baseRetriever import BaseRetriever
        from src.schemas.retrievalSchema import RetrievedDocuments

        class ConcreteRetriever(BaseRetriever):
            def retrieve(self, query: str) -> RetrievedDocuments:
                return RetrievedDocuments(company_name=query, documents=[], demo_mode=True)

        retriever = ConcreteRetriever()
        result = retriever.retrieve("TestCo")
        assert result.company_name == "TestCo"


# ════════════════════════════════════════════════════════════════════════════════
# CompanyRetriever — demo mode
# ════════════════════════════════════════════════════════════════════════════════

class TestCompanyRetrieverDemoMode:

    def test_returns_empty_documents_in_demo_mode(self):
        """In demo mode, documents list must be empty."""
        from src.modules.retrieval.companyRetriever import CompanyRetriever
        retriever = CompanyRetriever()
        with patch("src.modules.retrieval.companyRetriever.settings") as mockSettings:
            mockSettings.is_demo = True
            result = retriever.retrieve("Acme Corp")
        assert result.documents == []

    def test_demo_mode_flag_is_true(self):
        """demo_mode field must be True in demo mode."""
        from src.modules.retrieval.companyRetriever import CompanyRetriever
        retriever = CompanyRetriever()
        with patch("src.modules.retrieval.companyRetriever.settings") as mockSettings:
            mockSettings.is_demo = True
            result = retriever.retrieve("Acme Corp")
        assert result.demo_mode is True

    def test_company_name_preserved_in_demo_mode(self):
        """company_name field must match the input query."""
        from src.modules.retrieval.companyRetriever import CompanyRetriever
        retriever = CompanyRetriever()
        with patch("src.modules.retrieval.companyRetriever.settings") as mockSettings:
            mockSettings.is_demo = True
            result = retriever.retrieve("DeepMind")
        assert result.company_name == "DeepMind"

    def test_returns_retrieved_documents_schema(self):
        """Return type must be RetrievedDocuments."""
        from src.modules.retrieval.companyRetriever import CompanyRetriever
        from src.schemas.retrievalSchema import RetrievedDocuments
        retriever = CompanyRetriever()
        with patch("src.modules.retrieval.companyRetriever.settings") as mockSettings:
            mockSettings.is_demo = True
            result = retriever.retrieve("Acme Corp")
        assert isinstance(result, RetrievedDocuments)

    def test_no_network_call_in_demo_mode(self):
        """In demo mode, _productionRetrieve must NOT be called."""
        from src.modules.retrieval.companyRetriever import CompanyRetriever
        retriever = CompanyRetriever()
        with patch("src.modules.retrieval.companyRetriever.settings") as mockSettings:
            mockSettings.is_demo = True
            with patch.object(retriever, "_productionRetrieve") as mockProd:
                retriever.retrieve("TestCo")
        mockProd.assert_not_called()

    def test_production_mode_raises_not_implemented(self):
        """Production retrieval is not yet implemented — must raise."""
        from src.modules.retrieval.companyRetriever import CompanyRetriever
        retriever = CompanyRetriever()
        with patch("src.modules.retrieval.companyRetriever.settings") as mockSettings:
            mockSettings.is_demo = False
            with pytest.raises(NotImplementedError):
                retriever.retrieve("Acme Corp")


# ════════════════════════════════════════════════════════════════════════════════
# companyRetriever singleton
# ════════════════════════════════════════════════════════════════════════════════

class TestCompanyRetrieverSingleton:

    def test_singleton_is_importable(self):
        from src.modules.retrieval.companyRetriever import companyRetriever
        assert companyRetriever is not None

    def test_singleton_is_company_retriever_instance(self):
        from src.modules.retrieval.companyRetriever import companyRetriever, CompanyRetriever
        assert isinstance(companyRetriever, CompanyRetriever)

    def test_singleton_behaves_in_demo_mode(self):
        from src.modules.retrieval.companyRetriever import companyRetriever
        with patch("src.modules.retrieval.companyRetriever.settings") as mockSettings:
            mockSettings.is_demo = True
            result = companyRetriever.retrieve("Google")
        assert result.demo_mode is True
        assert result.documents == []


# ════════════════════════════════════════════════════════════════════════════════
# companyResearchAgent
# ════════════════════════════════════════════════════════════════════════════════

class TestCompanyResearchAgent:

    def _makeState(self, companyName: str = "Acme Corp", targetRole: str = "Engineer") -> dict:
        return {
            "session_id": "test-session-001",
            "candidate": {
                "target_company": companyName,
                "target_role": targetRole,
            },
            "step_log": [],
        }

    def test_returns_empty_context_in_demo_mode(self):
        """In demo mode, company_context must be empty string."""
        from src.agents.companyResearchAgent import companyResearchAgent
        from src.schemas.retrievalSchema import RetrievedDocuments

        emptyDocs = RetrievedDocuments(company_name="Acme Corp", documents=[], demo_mode=True)
        with patch("src.agents.companyResearchAgent.companyRetriever") as mockRetriever:
            mockRetriever.retrieve.return_value = emptyDocs
            result = companyResearchAgent(self._makeState())

        assert result["company_context"] == ""

    def test_llm_not_called_in_demo_mode(self):
        """LLM must NOT be invoked when no documents are retrieved."""
        from src.agents.companyResearchAgent import companyResearchAgent
        from src.schemas.retrievalSchema import RetrievedDocuments

        emptyDocs = RetrievedDocuments(company_name="Acme Corp", documents=[], demo_mode=True)
        with patch("src.agents.companyResearchAgent.companyRetriever") as mockRetriever:
            mockRetriever.retrieve.return_value = emptyDocs
            with patch("src.agents.companyResearchAgent.callLlm") as mockLlm:
                companyResearchAgent(self._makeState())
        mockLlm.assert_not_called()

    def test_retriever_called_before_llm(self):
        """companyRetriever.retrieve() must be called (retrieval always happens first)."""
        from src.agents.companyResearchAgent import companyResearchAgent
        from src.schemas.retrievalSchema import RetrievedDocuments

        emptyDocs = RetrievedDocuments(company_name="Acme Corp", documents=[], demo_mode=True)
        with patch("src.agents.companyResearchAgent.companyRetriever") as mockRetriever:
            mockRetriever.retrieve.return_value = emptyDocs
            companyResearchAgent(self._makeState("Acme Corp"))

        mockRetriever.retrieve.assert_called_once_with("Acme Corp")

    def test_returns_step_log(self):
        """Return value must include step_log with agent entries."""
        from src.agents.companyResearchAgent import companyResearchAgent
        from src.schemas.retrievalSchema import RetrievedDocuments

        emptyDocs = RetrievedDocuments(company_name="Acme Corp", documents=[], demo_mode=True)
        with patch("src.agents.companyResearchAgent.companyRetriever") as mockRetriever:
            mockRetriever.retrieve.return_value = emptyDocs
            result = companyResearchAgent(self._makeState())

        assert "step_log" in result
        assert isinstance(result["step_log"], list)
        assert any("[companyResearchAgent]" in entry for entry in result["step_log"])

    def test_skips_when_no_company_name(self):
        """If target_company is empty, agent skips cleanly."""
        from src.agents.companyResearchAgent import companyResearchAgent
        state = self._makeState(companyName="")
        with patch("src.agents.companyResearchAgent.companyRetriever") as mockRetriever:
            result = companyResearchAgent(state)
        mockRetriever.retrieve.assert_not_called()
        assert result["company_context"] == ""

    def test_llm_called_when_documents_available(self):
        """When real documents are retrieved, LLM must be called for summarisation."""
        from src.agents.companyResearchAgent import companyResearchAgent
        from src.schemas.retrievalSchema import RetrievedDocuments, RetrievedDocument

        realDocs = RetrievedDocuments(
            company_name="Acme Corp",
            documents=[
                RetrievedDocument(
                    source="https://acme.com/about",
                    content="Acme Corp is a leading AI company founded in 2010.",
                    doc_type="website",
                    retrieved_at="2026-01-01T00:00:00Z",
                )
            ],
            demo_mode=False,
        )

        with patch("src.agents.companyResearchAgent.companyRetriever") as mockRetriever:
            mockRetriever.retrieve.return_value = realDocs
            with patch("src.agents.companyResearchAgent.callLlm",
                       return_value="Acme Corp is a leading AI company.") as mockLlm:
                result = companyResearchAgent(self._makeState())

        mockLlm.assert_called_once()
        assert result["company_context"] == "Acme Corp is a leading AI company."

    def test_company_context_is_string(self):
        """company_context must always be a string (never None)."""
        from src.agents.companyResearchAgent import companyResearchAgent
        from src.schemas.retrievalSchema import RetrievedDocuments

        emptyDocs = RetrievedDocuments(company_name="Acme", documents=[], demo_mode=True)
        with patch("src.agents.companyResearchAgent.companyRetriever") as mockRetriever:
            mockRetriever.retrieve.return_value = emptyDocs
            result = companyResearchAgent(self._makeState())

        assert isinstance(result["company_context"], str)
