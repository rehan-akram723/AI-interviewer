# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/interviewEngine/questionBank.py
#
# Static Question Bank — Role × Phase × Mode question sets
#
# Architecture rationale:
#   LLM-only question generation risks hallucinated, generic, or off-topic questions.
#   This bank provides a curated, high-quality baseline that the InterviewPlanner
#   agent enriches with candidate-specific follow-ups — not replaces.
#
# Roles covered:
#   "software_engineer"  — backend, frontend, fullstack, devops variants
#   "data_scientist"     — analytics, statistics, ML modelling
#   "ml_engineer"        — MLOps, model deployment, training infrastructure
#   "product_manager"    — roadmap, prioritisation, metrics, stakeholder management
#   "business_analyst"   — requirements, data analysis, process mapping
#
# Phases:
#   "icebreaker"       — rapport building, background, motivation
#   "technical"        — role-specific technical depth
#   "behavioral"       — STAR-format competency questions
#   "system_design"    — architecture and design thinking
#   "closing"          — candidate questions, expectations, wrap-up signals
#
# Mode distributions (MODE_DISTRIBUTIONS):
#   Controls the ratio of question types the InterviewPlanner should draw from
#   when building the question_plan for a given interview_mode.
#
# Exports:
#   QUESTION_BANK, MODE_DISTRIBUTIONS, detectRoleCategory, getBaseQuestions
# ─────────────────────────────────────────────────────────────────────────────

from typing import List


# ══════════════════════════════════════════════════════════════════════════════
# MODE DISTRIBUTIONS
# Each value is a float ratio summing to 1.0.
# The InterviewPlanner uses these to determine how many questions of each
# category to include in the question_plan for a given interview_mode.
# ══════════════════════════════════════════════════════════════════════════════

MODE_DISTRIBUTIONS: dict[str, dict[str, float]] = {
    "mixed": {
        "technical":   0.35,
        "behavioral":  0.35,
        "motivational": 0.20,
        "situational": 0.10,
    },
    "technical": {
        "technical":   0.80,
        "behavioral":  0.15,
        "motivational": 0.05,
        "situational": 0.00,
    },
    "behavioral": {
        "technical":   0.10,
        "behavioral":  0.80,
        "motivational": 0.05,
        "situational": 0.05,
    },
    "hr_culture_fit": {
        "technical":   0.00,
        "behavioral":  0.30,
        "motivational": 0.60,
        "situational": 0.10,
    },
    "system_design": {
        "technical":   0.05,
        "behavioral":  0.05,
        "motivational": 0.00,
        "system_design": 0.90,
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# QUESTION BANK
# Structure: QUESTION_BANK[role_category][phase] = List[str]
#
# Naming note: The role category keys are snake_case because they are stored
# as data values in JSON (not Python identifiers). Phase keys follow the exact
# Literal values defined in InterviewSession.current_phase.
# ══════════════════════════════════════════════════════════════════════════════

QUESTION_BANK: dict[str, dict[str, List[str]]] = {

    # ──────────────────────────────────────────────────────────────────────────
    # SOFTWARE ENGINEER
    # ──────────────────────────────────────────────────────────────────────────
    "software_engineer": {

        "icebreaker": [
            "Tell me about yourself and the journey that led you to software engineering.",
            "What drew you to apply for this role at {company}, and what excites you most about it?",
            "Walk me through the project on your CV you're most proud of — what was your contribution?",
            "How do you stay current with evolving technologies and industry trends?",
            "Describe your ideal engineering team culture. What makes a team exceptional?",
        ],

        "technical": [
            # Systems & fundamentals
            "Explain the difference between a process and a thread. When would you choose "
            "multi-threading over multi-processing in Python?",
            "What is the CAP theorem? How did it influence a technical decision you've made?",
            "Walk me through what happens — from network to rendering — when a user types "
            "a URL into a browser and hits Enter.",
            "How do you approach debugging a production service that is returning 500 errors "
            "intermittently? Walk me through your methodology.",
            "Explain ACID properties. In which scenarios would you deliberately relax one of "
            "them and why?",
            # APIs & architecture
            "What are the key differences between REST, GraphQL, and gRPC? "
            "When would you choose each?",
            "How do you design an API for backward compatibility when you need to make "
            "a breaking change?",
            "Describe your approach to handling race conditions in a distributed system "
            "where multiple services write to the same resource.",
            # Code quality & delivery
            "How do you approach writing code that is easy to test? Walk me through "
            "a specific example from your experience.",
            "What does observability mean to you in production? What metrics, logs, and "
            "traces would you instrument for a new service?",
            "Explain the difference between optimistic and pessimistic locking. "
            "Give a concrete use case for each.",
            "How do you think about technical debt? Describe how you've managed it in a "
            "previous role — when to pay it down and when to let it accrue.",
        ],

        "behavioral": [
            "Tell me about a time you had to push back on a product requirement because "
            "it was technically infeasible within the given timeline. What was the outcome?",
            "Describe a situation where you identified a significant bug or security "
            "vulnerability in production. How did you handle it, and what did you learn?",
            "Give me an example of a time you disagreed with a senior engineer's technical "
            "decision. How did you handle the disagreement?",
            "Tell me about a project where the scope changed significantly mid-delivery. "
            "How did you adapt, and what was the result?",
            "Describe a time you had to onboard yourself onto a large, unfamiliar codebase "
            "very quickly. What was your strategy?",
            "Give me an example of a time you improved the performance of an existing system. "
            "What was the bottleneck, what did you do, and what was the measurable impact?",
            "Tell me about a time you mentored or helped a junior engineer. "
            "What approach did you take and what was the impact?",
        ],

        "system_design": [
            "Design a URL shortening service like bit.ly. Walk me through the "
            "full system — data model, API, scaling strategy, and failure modes.",
            "How would you design a rate-limiting system for a high-traffic REST API? "
            "Consider distributed deployments.",
            "Design a notification delivery system that handles email, SMS, and push "
            "notifications at scale. How do you ensure at-least-once delivery?",
            "Design a distributed job scheduling system similar to Airflow or Celery. "
            "How do you handle retries, failures, and observability?",
            "How would you architect a multi-tenant SaaS application? "
            "What are the key data isolation and performance considerations?",
            "Walk me through designing a real-time collaborative document editing "
            "system — like Google Docs. What are the hardest problems?",
        ],

        "closing": [
            "What aspects of software engineering do you find most energising right now, "
            "and what skills are you actively developing?",
            "Where do you see yourself in three years, and how does this role fit into "
            "that trajectory?",
            "Do you have any questions for us about the team, the tech stack, or "
            "how success is measured in this role?",
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # DATA SCIENTIST
    # ──────────────────────────────────────────────────────────────────────────
    "data_scientist": {

        "icebreaker": [
            "Tell me about yourself and what first drew you to data science.",
            "Which project on your CV best represents your data science capabilities, "
            "and why?",
            "What types of problems do you find most intellectually engaging in data science?",
            "How do you keep up with the latest research and tooling in the field?",
            "Describe the data science team structure you've worked in and what worked well.",
        ],

        "technical": [
            # Statistics & ML fundamentals
            "Explain the bias-variance trade-off. How do you diagnose each problem "
            "in a model, and what are your go-to remedies?",
            "What is p-hacking, and how do you design experiments to avoid it? "
            "Walk me through how you'd set up an A/B test for a product feature.",
            "Explain the difference between L1 (Lasso) and L2 (Ridge) regularisation. "
            "When would you choose each, and why?",
            "How do you handle class imbalance in a classification problem? "
            "Which techniques have you used and in what contexts?",
            "Walk me through how gradient boosting works under the hood. "
            "How does it differ from bagging approaches like Random Forest?",
            "Explain what cross-validation is, why we use it, and what the risks are "
            "of using it incorrectly (e.g., data leakage).",
            # Data & practical skills
            "How do you approach feature engineering for a new prediction problem? "
            "What is your process from raw data to final feature set?",
            "Describe how you would detect and handle outliers in a dataset used "
            "for regression modelling.",
            "What is the difference between Pearson and Spearman correlation? "
            "When does the distinction matter?",
            "How do you evaluate whether a deployed model is still performing well "
            "over time? What metrics do you monitor and at what cadence?",
        ],

        "behavioral": [
            "Tell me about a time your model performed excellently in validation "
            "but failed in production. What did you discover and how did you fix it?",
            "Describe a project where the data was significantly messier than expected. "
            "How did you handle it and what was the impact on your timeline?",
            "Tell me about a time you had to communicate a complex statistical finding "
            "to a non-technical stakeholder. How did you approach it?",
            "Give me an example of a time you had to push back on a request to "
            "'just run the numbers' and instead reframed the problem. What happened?",
            "Describe a situation where you had to make a decision with limited data. "
            "What was your reasoning and what was the outcome?",
            "Tell me about a time you collaborated closely with a software engineer "
            "to productionise one of your models. What friction did you encounter?",
        ],

        "system_design": [
            "Design a machine learning pipeline that takes raw event data, trains a "
            "churn prediction model weekly, and serves predictions via an API. "
            "What does the end-to-end architecture look like?",
            "How would you design a feature store for a team of 20 data scientists "
            "working on a dozen different models? What are the key design decisions?",
            "Design an A/B testing platform that tracks user behaviour, assigns users "
            "to experiment groups, and computes statistical significance automatically.",
            "You need to build a recommendation engine for an e-commerce platform. "
            "Walk me through the architecture from data collection to prediction serving.",
        ],

        "closing": [
            "What modelling techniques or domains are you most interested in exploring "
            "or deepening over the next year?",
            "How do you think about the boundary between data science and machine "
            "learning engineering in a well-functioning team?",
            "What questions do you have for us about the data infrastructure, the "
            "types of problems we work on, or how data science is used to make decisions?",
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # ML ENGINEER
    # ──────────────────────────────────────────────────────────────────────────
    "ml_engineer": {

        "icebreaker": [
            "Tell me about yourself and how you came to specialise in ML engineering.",
            "Which ML system you've built or contributed to are you most proud of, "
            "and what made it technically challenging?",
            "What does a well-engineered ML platform look like to you?",
            "How do you stay on top of new tooling in the MLOps and ML infrastructure space?",
            "Describe the relationship between data scientists and ML engineers on the "
            "best team you've worked on.",
        ],

        "technical": [
            # Training infrastructure
            "Walk me through how you would set up a distributed training job for a "
            "large transformer model across multiple GPUs. What frameworks and strategies "
            "would you use?",
            "Explain the difference between data parallelism and model parallelism. "
            "When is each approach appropriate?",
            "How do you detect and handle data drift in a live ML system? "
            "What monitoring pipelines have you built?",
            "Describe how you would implement a feature pipeline that ensures "
            "training-serving skew is eliminated.",
            # Deployment & serving
            "Walk me through how you would deploy a PyTorch model to production with "
            "a latency target of under 50ms. What optimisations would you apply?",
            "Explain the trade-offs between real-time inference, batch inference, and "
            "approximate nearest neighbour (ANN) serving for recommendation models.",
            "What strategies do you use to reduce the size of a model for edge deployment "
            "without unacceptable accuracy degradation?",
            # MLOps
            "How would you implement a canary deployment strategy for a new model version? "
            "What metrics do you watch to decide whether to roll forward or rollback?",
            "Describe how you'd design an experiment tracking system for a team of "
            "10 ML engineers. What metadata would you capture, and how?",
            "What is your approach to versioning datasets, models, and their "
            "associated code together for full reproducibility?",
        ],

        "behavioral": [
            "Tell me about a time an ML model you deployed caused an unexpected production "
            "issue. How did you diagnose and resolve it, and what did you change afterwards?",
            "Describe a situation where you had to significantly refactor an existing "
            "ML pipeline. What was the trigger, and how did you manage the migration?",
            "Tell me about a time you improved inference latency or throughput by a "
            "significant margin. What was your approach and what was the impact?",
            "Give me an example of a disagreement with a data scientist about model "
            "architecture or deployment strategy. How did you resolve it?",
            "Describe a time you had to balance technical best practices with delivery "
            "speed. What trade-offs did you make and would you make them again?",
            "Tell me about a time you built tooling or infrastructure that other teams "
            "adopted. How did you socialise it and what was the adoption journey like?",
        ],

        "system_design": [
            "Design a recommendation system for a streaming platform with 50M daily "
            "active users. Walk through data collection, model training, serving, and "
            "how you'd handle cold-start for new users and new content.",
            "Design an experimentation platform for ML models that supports shadow mode, "
            "canary deployments, and full A/B experiments — with automated statistical "
            "significance calculations.",
            "How would you design a model monitoring system that detects performance "
            "degradation across 200 models in production, with different SLA requirements "
            "per model?",
            "Design a feature store that serves both online (low-latency) and offline "
            "(batch training) use cases from a single source of truth.",
            "Walk me through architecting an MLOps platform from scratch for a team "
            "that currently has no standardised infrastructure. What do you build first?",
        ],

        "closing": [
            "What area of ML infrastructure or tooling are you most excited about "
            "right now — and what are you actively learning?",
            "How do you think the ML engineering role will evolve over the next "
            "three to five years?",
            "What questions do you have about our model serving infrastructure, "
            "training stack, or how we handle model governance?",
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # PRODUCT MANAGER
    # ──────────────────────────────────────────────────────────────────────────
    "product_manager": {

        "icebreaker": [
            "Tell me about yourself and the product domains you've worked in.",
            "Walk me through a product you've shipped that you're particularly proud of. "
            "What was your role and what was the impact?",
            "What drew you to product management, and why are you interested in this role?",
            "How do you describe your product management style to a new engineering team?",
            "What's a product you use daily that you think is poorly designed? How would "
            "you fix it?",
        ],

        "technical": [
            "How do you prioritise a backlog when you have more requests than capacity? "
            "Walk me through a specific framework you've used.",
            "How do you define and measure product success? Give me an example of a "
            "North Star metric you've worked with and how you decomposed it.",
            "Explain the difference between output metrics and outcome metrics. "
            "Why does the distinction matter for roadmap planning?",
            "How do you decide whether to build, buy, or partner for a new capability?",
            "Walk me through how you would structure a discovery sprint for a problem "
            "you've never worked on before.",
            "How do you manage technical debt requests from engineering when you have "
            "competing feature demands from the business?",
        ],

        "behavioral": [
            "Tell me about a time a product you launched underperformed expectations. "
            "What did you learn and how did you respond?",
            "Describe a situation where you had to say no to a feature request from "
            "a senior stakeholder. How did you handle it?",
            "Give me an example of how you used customer research or data to change "
            "the direction of a product. What was the process?",
            "Tell me about a time you had to align multiple cross-functional teams "
            "with conflicting priorities. How did you get consensus?",
            "Describe a time you had to make a significant product decision with "
            "incomplete information. What was your reasoning?",
            "Tell me about a time you worked very closely with engineering to solve "
            "a complex technical constraint in a product. What was your contribution?",
        ],

        "system_design": [
            "You've been asked to redesign the onboarding experience for a B2B SaaS "
            "product with a 60% drop-off at step 3. How do you approach this?",
            "Design a notification system for a mobile app. What are the key product "
            "decisions, metrics, and failure modes you'd consider?",
            "How would you design a pricing page for a product with three tiers? "
            "What research and experimentation would inform your decisions?",
            "Walk me through how you would build a product roadmap for a zero-to-one "
            "product in an established company. What are your first 90-day milestones?",
        ],

        "closing": [
            "What type of product problems do you find most energising, and what "
            "domains are you hoping to develop deeper expertise in?",
            "How do you think about your own growth as a PM — what skills are you "
            "actively working on right now?",
            "What questions do you have about our product vision, team structure, or "
            "how product decisions get made here?",
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # BUSINESS ANALYST
    # ──────────────────────────────────────────────────────────────────────────
    "business_analyst": {

        "icebreaker": [
            "Tell me about yourself and the industries and domains you've analysed.",
            "Walk me through the most complex business problem you've helped solve. "
            "What was your role?",
            "What drew you to business analysis, and what do you find most rewarding "
            "about the work?",
            "How do you prefer to work with stakeholders — and what makes a great "
            "stakeholder relationship?",
            "Describe the collaboration between business analysts and developers on "
            "the best project you've been part of.",
        ],

        "technical": [
            "Walk me through how you would write a SQL query to find the top 10 "
            "customers by revenue, excluding customers who churned in the last 30 days.",
            "How do you approach requirements gathering for a new system when "
            "stakeholders have conflicting needs?",
            "Explain the difference between functional and non-functional requirements. "
            "Give an example of each from a project you've worked on.",
            "How do you validate that the system built by the engineering team actually "
            "meets the business requirements you defined?",
            "Describe how you create and maintain a business requirements document (BRD) "
            "or user story map. What tools do you use?",
            "How do you perform gap analysis? Walk me through a specific example.",
            "What techniques do you use for process mapping, and when would you choose "
            "a swimlane diagram over a BPMN model?",
        ],

        "behavioral": [
            "Tell me about a time a stakeholder changed the requirements late in a "
            "project. How did you handle it?",
            "Describe a situation where your analysis revealed that the business was "
            "solving the wrong problem. How did you communicate this?",
            "Give me an example of a time you had to facilitate a difficult workshop "
            "or meeting with opposing stakeholders. What was your approach?",
            "Tell me about a time your business case or analysis directly influenced "
            "a significant investment or strategic decision.",
            "Describe a project where you had to learn a new domain very quickly "
            "to be effective. How did you get up to speed?",
            "Tell me about a time you identified a process inefficiency that wasn't "
            "originally in scope. How did you handle it?",
        ],

        "system_design": [
            "You've been asked to map and optimise a manual customer onboarding "
            "process that currently takes 10 business days. How do you approach this?",
            "Design the requirements gathering and sign-off process for a new CRM "
            "system replacing a legacy platform used by 500 staff. "
            "What are the risks and how do you mitigate them?",
            "How would you structure a business case for a new data warehouse "
            "implementation? What sections would you include and why?",
        ],

        "closing": [
            "What domains or industries are you most interested in deepening your "
            "expertise in over the next few years?",
            "What aspects of business analysis do you find most challenging, and how "
            "are you working to improve in those areas?",
            "What questions do you have for us about the types of projects we work on, "
            "the team structure, or how analysts collaborate with product and engineering?",
        ],
    },
}


# ── Fallback for unrecognised roles ───────────────────────────────────────────
# When detectRoleCategory returns "default", these generic questions are used.
QUESTION_BANK["default"] = {
    "icebreaker": [
        "Tell me about yourself and your professional background.",
        "What motivated you to apply for this role?",
        "Walk me through a recent project or achievement you're proud of.",
    ],
    "technical": [
        "Describe the technical skills you'd bring to this role.",
        "Walk me through a technical challenge you solved recently.",
        "How do you approach learning a new tool or technology?",
    ],
    "behavioral": [
        "Tell me about a time you had to work under significant pressure. "
        "How did you manage it?",
        "Describe a situation where you had to collaborate with a difficult colleague. "
        "What was your approach?",
        "Give me an example of a time you took initiative on a project without being asked.",
    ],
    "system_design": [
        "Describe how you would approach designing a solution for a problem "
        "you've never encountered before.",
    ],
    "closing": [
        "What are you looking for in your next role?",
        "Do you have any questions for us?",
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# ROLE KEYWORD MAPPING
# Order matters: check more specific roles first.
# Each entry is a tuple of (role_category_key, [keywords]).
# Keywords are matched against the lowercase job title string.
# ══════════════════════════════════════════════════════════════════════════════

_ROLE_KEYWORD_MAP: list[tuple[str, list[str]]] = [
    # Most specific first — prevents "ml engineer" matching "software engineer"
    ("ml_engineer", [
        "machine learning engineer", "ml engineer", "mlops", "ai engineer",
        "deep learning engineer", "computer vision engineer", "nlp engineer",
        "model engineer", "applied ml", "ml platform", "ml infrastructure",
        "machine learning platform", "machine learning infra",
    ]),
    ("data_scientist", [
        "data scientist", "data science", "research scientist", "applied scientist",
        "applied researcher", "quantitative analyst", "quant analyst",
        "statistician", "analytics scientist", "computational scientist",
        "ai researcher", "ml researcher",
    ]),
    ("product_manager", [
        "product manager", "product owner", "senior product", "lead pm",
        "group product manager", "principal pm", "director of product",
        "vp of product", "head of product", "product lead", "program manager",
    ]),
    ("business_analyst", [
        "business analyst", "systems analyst", "requirements analyst",
        "functional analyst", "process analyst", "it analyst",
        "data analyst",  # treated as BA when not clearly data science
    ]),
    ("software_engineer", [
        "software engineer", "software developer", "backend engineer",
        "frontend engineer", "fullstack engineer", "full stack engineer",
        "full-stack", "web developer", "web engineer", "application developer",
        "sde", "swe", "devops engineer", "platform engineer", "site reliability",
        "sre", "infrastructure engineer", "cloud engineer", "java developer",
        "python developer", "golang developer", "node developer", "react developer",
        "mobile developer", "ios developer", "android developer",
    ]),
]


def detectRoleCategory(targetRole: str) -> str:
    """
    Map a free-text job title to one of the predefined role category keys.

    Algorithm:
        1. Lowercase and strip the input string.
        2. Iterate through _ROLE_KEYWORD_MAP in order (most specific first).
        3. For each role, check if ANY keyword is a substring of the title.
        4. Return the first match found.
        5. If no match → return "software_engineer" as the safe default
           (most common technical role; prevents empty question banks).

    Args:
        targetRole: Free-text job title extracted from the JD (e.g., "Senior ML Engineer").

    Returns:
        One of: "software_engineer" | "data_scientist" | "ml_engineer" |
                "product_manager" | "business_analyst"
    """
    if not targetRole or not targetRole.strip():
        return "software_engineer"

    normalised = targetRole.lower().strip()

    for roleKey, keywords in _ROLE_KEYWORD_MAP:
        for keyword in keywords:
            if keyword in normalised:
                return roleKey

    # No keyword matched — default to software_engineer
    return "software_engineer"


def getBaseQuestions(roleCategory: str, phase: str) -> List[str]:
    """
    Retrieve the list of base questions for a given role category and interview phase.

    Args:
        roleCategory: One of the role category keys (e.g., "software_engineer").
                      Unrecognised values fall back to "default".
        phase:        One of: "icebreaker" | "technical" | "behavioral" |
                      "system_design" | "closing".
                      Note: "cv_deep_dive" and "dynamic_followup" phases are
                      handled entirely by LLM agents — no static bank exists for them.

    Returns:
        List of question strings. Returns [] if phase has no static questions.
    """
    roleQuestions = QUESTION_BANK.get(roleCategory) or QUESTION_BANK.get("default", {})
    return list(roleQuestions.get(phase, []))


def getQuestionCount(roleCategory: str, phase: str) -> int:
    """Return the number of base questions available for a role/phase combination."""
    return len(getBaseQuestions(roleCategory, phase))


def getAllSupportedRoles() -> List[str]:
    """Return the list of all supported role category keys."""
    return [key for key in QUESTION_BANK.keys() if key != "default"]


def getAllSupportedModes() -> List[str]:
    """Return the list of all supported interview modes."""
    return list(MODE_DISTRIBUTIONS.keys())
