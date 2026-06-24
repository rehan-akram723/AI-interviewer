# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testQuestionBank.py
#
# Unit tests for src.modules.interviewEngine.questionBank
#
# Tests cover:
#   1. MODE_DISTRIBUTIONS — completeness, value types, sum-to-1 validation
#   2. QUESTION_BANK — all roles present, phase coverage, minimum question counts
#   3. detectRoleCategory — explicit title matches, prefix/suffix variants,
#      case insensitivity, empty input, unknown title defaults
#   4. getBaseQuestions — correct retrieval, fallback for unknown role/phase
#   5. Helper functions — getQuestionCount, getAllSupportedRoles, getAllSupportedModes
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from src.modules.interviewEngine.questionBank import (
    QUESTION_BANK,
    MODE_DISTRIBUTIONS,
    detectRoleCategory,
    getBaseQuestions,
    getQuestionCount,
    getAllSupportedRoles,
    getAllSupportedModes,
)


# ════════════════════════════════════════════════════════════════════════════════
# MODE_DISTRIBUTIONS
# ════════════════════════════════════════════════════════════════════════════════

class TestModeDistributions:

    REQUIRED_MODES = {"mixed", "technical", "behavioral", "hr_culture_fit", "system_design"}

    def test_all_modes_present(self):
        assert self.REQUIRED_MODES.issubset(set(MODE_DISTRIBUTIONS.keys()))

    def test_each_mode_is_dict(self):
        for mode, dist in MODE_DISTRIBUTIONS.items():
            assert isinstance(dist, dict), f"Mode '{mode}' distribution is not a dict"

    def test_each_distribution_values_are_floats(self):
        for mode, dist in MODE_DISTRIBUTIONS.items():
            for category, value in dist.items():
                assert isinstance(value, (int, float)), (
                    f"Mode '{mode}', category '{category}': value must be numeric"
                )

    def test_each_distribution_values_are_between_0_and_1(self):
        for mode, dist in MODE_DISTRIBUTIONS.items():
            for category, value in dist.items():
                assert 0.0 <= value <= 1.0, (
                    f"Mode '{mode}', category '{category}': value {value} out of range"
                )

    def test_distributions_sum_to_approximately_1(self):
        """Each mode's distribution values should sum to 1.0 (±0.01 for float precision)."""
        for mode, dist in MODE_DISTRIBUTIONS.items():
            total = sum(dist.values())
            assert abs(total - 1.0) < 0.01, (
                f"Mode '{mode}' distribution sums to {total}, expected 1.0"
            )

    def test_technical_mode_heavily_technical(self):
        """Technical mode must have >= 70% technical questions."""
        assert MODE_DISTRIBUTIONS["technical"]["technical"] >= 0.70

    def test_hr_culture_fit_no_technical_questions(self):
        """HR/culture mode should have 0% technical allocation."""
        assert MODE_DISTRIBUTIONS["hr_culture_fit"].get("technical", 0.0) == 0.0

    def test_system_design_mode_mostly_system_design(self):
        """System design mode must allocate >= 80% to system_design category."""
        assert MODE_DISTRIBUTIONS["system_design"].get("system_design", 0.0) >= 0.80

    def test_behavioral_mode_mostly_behavioral(self):
        """Behavioral mode must allocate >= 70% to behavioral category."""
        assert MODE_DISTRIBUTIONS["behavioral"]["behavioral"] >= 0.70


# ════════════════════════════════════════════════════════════════════════════════
# QUESTION_BANK — Structure
# ════════════════════════════════════════════════════════════════════════════════

class TestQuestionBankStructure:

    REQUIRED_ROLES = {
        "software_engineer", "data_scientist", "ml_engineer",
        "product_manager", "business_analyst",
    }
    REQUIRED_PHASES = {"icebreaker", "technical", "behavioral", "system_design", "closing"}

    def test_all_required_roles_present(self):
        bankRoles = set(QUESTION_BANK.keys())
        missing = self.REQUIRED_ROLES - bankRoles
        assert not missing, f"Missing roles in QUESTION_BANK: {missing}"

    def test_each_role_has_all_required_phases(self):
        for role in self.REQUIRED_ROLES:
            roleBank = QUESTION_BANK[role]
            missingPhases = self.REQUIRED_PHASES - set(roleBank.keys())
            assert not missingPhases, (
                f"Role '{role}' is missing phases: {missingPhases}"
            )

    def test_each_phase_has_list_of_questions(self):
        for role, phases in QUESTION_BANK.items():
            for phase, questions in phases.items():
                assert isinstance(questions, list), (
                    f"QUESTION_BANK['{role}']['{phase}'] must be a list"
                )

    def test_each_question_is_a_string(self):
        for role, phases in QUESTION_BANK.items():
            for phase, questions in phases.items():
                for i, q in enumerate(questions):
                    assert isinstance(q, str), (
                        f"QUESTION_BANK['{role}']['{phase}'][{i}] is not a string"
                    )
                    assert q.strip(), (
                        f"QUESTION_BANK['{role}']['{phase}'][{i}] is empty/whitespace"
                    )

    def test_minimum_question_counts_per_role(self):
        """Each role must have at least 3 icebreakers and 5 technical questions."""
        for role in self.REQUIRED_ROLES:
            icebreakerCount = len(QUESTION_BANK[role].get("icebreaker", []))
            technicalCount = len(QUESTION_BANK[role].get("technical", []))
            assert icebreakerCount >= 3, (
                f"Role '{role}' has only {icebreakerCount} icebreaker questions (min 3)"
            )
            assert technicalCount >= 5, (
                f"Role '{role}' has only {technicalCount} technical questions (min 5)"
            )

    def test_minimum_behavioral_questions_per_role(self):
        for role in self.REQUIRED_ROLES:
            count = len(QUESTION_BANK[role].get("behavioral", []))
            assert count >= 4, (
                f"Role '{role}' has only {count} behavioral questions (min 4)"
            )

    def test_minimum_system_design_questions_per_role(self):
        for role in self.REQUIRED_ROLES:
            count = len(QUESTION_BANK[role].get("system_design", []))
            assert count >= 2, (
                f"Role '{role}' has only {count} system_design questions (min 2)"
            )

    def test_closing_questions_present_for_all_roles(self):
        for role in self.REQUIRED_ROLES:
            count = len(QUESTION_BANK[role].get("closing", []))
            assert count >= 1, f"Role '{role}' has no closing questions"

    def test_default_fallback_role_exists(self):
        assert "default" in QUESTION_BANK

    def test_no_duplicate_questions_within_phase(self):
        """No exact duplicate question strings within the same role+phase."""
        for role, phases in QUESTION_BANK.items():
            for phase, questions in phases.items():
                assert len(questions) == len(set(questions)), (
                    f"Duplicate questions in QUESTION_BANK['{role}']['{phase}']"
                )


# ════════════════════════════════════════════════════════════════════════════════
# detectRoleCategory
# ════════════════════════════════════════════════════════════════════════════════

class TestDetectRoleCategory:

    # ── Exact / common matches ────────────────────────────────────────────────

    def test_software_engineer_title(self):
        assert detectRoleCategory("Software Engineer") == "software_engineer"

    def test_backend_engineer_title(self):
        assert detectRoleCategory("Backend Engineer") == "software_engineer"

    def test_frontend_engineer_title(self):
        assert detectRoleCategory("Frontend Engineer") == "software_engineer"

    def test_fullstack_engineer_title(self):
        assert detectRoleCategory("Full Stack Engineer") == "software_engineer"

    def test_sde_abbreviation(self):
        assert detectRoleCategory("SDE II at Amazon") == "software_engineer"

    def test_data_scientist_title(self):
        assert detectRoleCategory("Data Scientist") == "data_scientist"

    def test_research_scientist_title(self):
        assert detectRoleCategory("Research Scientist") == "data_scientist"

    def test_applied_scientist_title(self):
        # "Applied Scientist" is in the data_scientist keyword list.
        # "Applied Scientist, Machine Learning" correctly maps to data_scientist
        # because data_scientist keywords are checked before ml_engineer keywords.
        assert detectRoleCategory("Applied Scientist, Machine Learning") == "data_scientist"

    def test_ml_platform_engineer_title(self):
        assert detectRoleCategory("ML Platform Engineer") == "ml_engineer"

    def test_ml_engineer_title(self):
        assert detectRoleCategory("ML Engineer") == "ml_engineer"

    def test_machine_learning_engineer_full(self):
        assert detectRoleCategory("Machine Learning Engineer") == "ml_engineer"

    def test_mlops_engineer_title(self):
        assert detectRoleCategory("MLOps Engineer") == "ml_engineer"

    def test_ai_engineer_title(self):
        assert detectRoleCategory("AI Engineer") == "ml_engineer"

    def test_deep_learning_engineer_title(self):
        assert detectRoleCategory("Deep Learning Engineer") == "ml_engineer"

    def test_product_manager_title(self):
        assert detectRoleCategory("Product Manager") == "product_manager"

    def test_product_owner_title(self):
        assert detectRoleCategory("Product Owner") == "product_manager"

    def test_senior_pm_title(self):
        assert detectRoleCategory("Senior Product Manager") == "product_manager"

    def test_business_analyst_title(self):
        assert detectRoleCategory("Business Analyst") == "business_analyst"

    def test_systems_analyst_title(self):
        assert detectRoleCategory("Systems Analyst") == "business_analyst"

    # ── Case insensitivity ────────────────────────────────────────────────────

    def test_uppercase_input(self):
        assert detectRoleCategory("SOFTWARE ENGINEER") == "software_engineer"

    def test_mixed_case_input(self):
        assert detectRoleCategory("MaChInE LeArNiNg EnGiNEeR") == "ml_engineer"

    def test_all_lowercase_input(self):
        assert detectRoleCategory("product manager") == "product_manager"

    # ── Compound titles ────────────────────────────────────────────────────────

    def test_senior_prefix(self):
        assert detectRoleCategory("Senior Software Engineer") == "software_engineer"

    def test_lead_prefix(self):
        assert detectRoleCategory("Lead ML Engineer") == "ml_engineer"

    def test_principal_prefix(self):
        assert detectRoleCategory("Principal Data Scientist") == "data_scientist"

    def test_staff_level_title(self):
        assert detectRoleCategory("Staff Software Engineer") == "software_engineer"

    # ── ML engineer takes precedence over software engineer ───────────────────

    def test_ml_engineer_not_classified_as_software_engineer(self):
        """
        Critical precedence test: 'ML Engineer' contains 'Engineer' which could
        match software_engineer. The ml_engineer keywords must be checked first.
        """
        result = detectRoleCategory("ML Engineer")
        assert result == "ml_engineer", (
            f"Expected 'ml_engineer', got '{result}'. "
            "Check keyword precedence in _ROLE_KEYWORD_MAP."
        )

    def test_machine_learning_engineer_not_software_engineer(self):
        result = detectRoleCategory("Machine Learning Engineer")
        assert result == "ml_engineer"

    # ── Edge cases ─────────────────────────────────────────────────────────────

    def test_empty_string_returns_default(self):
        assert detectRoleCategory("") == "software_engineer"

    def test_whitespace_only_returns_default(self):
        assert detectRoleCategory("   ") == "software_engineer"

    def test_none_like_empty_returns_default(self):
        # None would be a type error, but test empty string as None equivalent
        assert detectRoleCategory("") == "software_engineer"

    def test_unknown_role_returns_software_engineer_default(self):
        assert detectRoleCategory("Professional Juggler") == "software_engineer"

    def test_role_with_numbers_still_works(self):
        assert detectRoleCategory("Software Engineer II") == "software_engineer"

    def test_devops_engineer_title(self):
        assert detectRoleCategory("DevOps Engineer") == "software_engineer"

    def test_sre_title(self):
        assert detectRoleCategory("Site Reliability Engineer") == "software_engineer"


# ════════════════════════════════════════════════════════════════════════════════
# getBaseQuestions
# ════════════════════════════════════════════════════════════════════════════════

class TestGetBaseQuestions:

    def test_returns_list_for_valid_role_and_phase(self):
        result = getBaseQuestions("software_engineer", "icebreaker")
        assert isinstance(result, list)

    def test_returns_non_empty_list_for_valid_combo(self):
        result = getBaseQuestions("software_engineer", "technical")
        assert len(result) > 0

    def test_questions_are_strings(self):
        questions = getBaseQuestions("ml_engineer", "system_design")
        for q in questions:
            assert isinstance(q, str)

    def test_returns_empty_list_for_invalid_phase(self):
        result = getBaseQuestions("software_engineer", "cv_deep_dive")
        assert result == []

    def test_returns_default_for_unknown_role(self):
        """Unknown role should fall back to 'default' bank."""
        result = getBaseQuestions("quantum_philosopher", "icebreaker")
        assert isinstance(result, list)
        assert len(result) > 0  # Default bank should have icebreakers

    def test_returns_copy_not_reference(self):
        """Modifying the returned list must not affect the original bank."""
        questions1 = getBaseQuestions("software_engineer", "technical")
        questions2 = getBaseQuestions("software_engineer", "technical")
        questions1.append("INJECTED")
        assert "INJECTED" not in questions2

    def test_all_roles_and_phases_return_lists(self):
        roles = ["software_engineer", "data_scientist", "ml_engineer",
                 "product_manager", "business_analyst"]
        phases = ["icebreaker", "technical", "behavioral", "system_design", "closing"]
        for role in roles:
            for phase in phases:
                result = getBaseQuestions(role, phase)
                assert isinstance(result, list), (
                    f"getBaseQuestions('{role}', '{phase}') did not return a list"
                )


# ════════════════════════════════════════════════════════════════════════════════
# getQuestionCount
# ════════════════════════════════════════════════════════════════════════════════

class TestGetQuestionCount:

    def test_returns_integer(self):
        result = getQuestionCount("software_engineer", "technical")
        assert isinstance(result, int)

    def test_count_matches_list_length(self):
        questions = getBaseQuestions("data_scientist", "behavioral")
        count = getQuestionCount("data_scientist", "behavioral")
        assert count == len(questions)

    def test_returns_zero_for_invalid_phase(self):
        assert getQuestionCount("software_engineer", "nonexistent_phase") == 0

    def test_all_technical_roles_have_at_least_5_technical_questions(self):
        technicalRoles = ["software_engineer", "data_scientist", "ml_engineer"]
        for role in technicalRoles:
            count = getQuestionCount(role, "technical")
            assert count >= 5, (
                f"Role '{role}' has only {count} technical questions in bank"
            )


# ════════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ════════════════════════════════════════════════════════════════════════════════

class TestHelperFunctions:

    def test_getAllSupportedRoles_returns_list(self):
        assert isinstance(getAllSupportedRoles(), list)

    def test_getAllSupportedRoles_excludes_default(self):
        roles = getAllSupportedRoles()
        assert "default" not in roles

    def test_getAllSupportedRoles_contains_required_roles(self):
        roles = getAllSupportedRoles()
        for required in ["software_engineer", "data_scientist", "ml_engineer",
                         "product_manager", "business_analyst"]:
            assert required in roles

    def test_getAllSupportedModes_returns_list(self):
        assert isinstance(getAllSupportedModes(), list)

    def test_getAllSupportedModes_contains_all_modes(self):
        modes = getAllSupportedModes()
        for mode in ["mixed", "technical", "behavioral", "hr_culture_fit", "system_design"]:
            assert mode in modes
