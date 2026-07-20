"""Tests for the career domain."""

from __future__ import annotations

from datetime import datetime

import pytest

from aicos.career.enums import (
    CareerTrackCategory,
    Difficulty,
    LearningStyle,
    RecommendationPriority,
    RecommendationType,
    TechnologyLifecycle,
)
from aicos.career.exceptions import (
    BlueprintValidationError,
    CareerDomainError,
    RecommendationValidationError,
    SkillValidationError,
    TechnologyValidationError,
    ValidationError,
)
from aicos.career.interfaces import CareerDomainServiceProtocol
from aicos.career.models import (
    CareerProfile,
    CareerTrack,
    LearningResource,
    LearningTopic,
    Recommendation,
    RoleBlueprint,
    Skill,
    Technology,
    TechnologyWatchItem,
)
from aicos.career.service import CareerDomainService


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------

class TestDifficulty:
    def test_values(self) -> None:
        assert list(Difficulty) == [
            Difficulty.BEGINNER,
            Difficulty.INTERMEDIATE,
            Difficulty.ADVANCED,
            Difficulty.EXPERT,
        ]

    def test_string_access(self) -> None:
        assert Difficulty("beginner") == Difficulty.BEGINNER
        assert Difficulty.INTERMEDIATE.value == "intermediate"


class TestTechnologyLifecycle:
    def test_values(self) -> None:
        assert TechnologyLifecycle.INDUSTRY_STANDARD.value == "industry_standard"
        assert TechnologyLifecycle.EXPERIMENTAL.value == "experimental"


class TestRecommendationPriority:
    def test_order(self) -> None:
        assert RecommendationPriority.LOW.value == "low"
        assert RecommendationPriority.CRITICAL.value == "critical"


class TestRecommendationType:
    def test_values(self) -> None:
        assert RecommendationType.LEARN.value == "learn"
        assert RecommendationType.REMOVE.value == "remove"


class TestLearningStyle:
    def test_values(self) -> None:
        assert LearningStyle.HANDS_ON.value == "hands_on"


class TestCareerTrackCategory:
    def test_values(self) -> None:
        assert CareerTrackCategory.AI.value == "ai"
        assert CareerTrackCategory.MANAGEMENT.value == "management"


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestCareerTrack:
    def test_defaults(self) -> None:
        t = CareerTrack(id="ml", name="Machine Learning")
        assert t.description == ""
        assert t.category == CareerTrackCategory.SOFTWARE
        assert t.difficulty == Difficulty.INTERMEDIATE
        assert t.status == "active"

    def test_frozen(self) -> None:
        t = CareerTrack(id="ml", name="ML")
        with pytest.raises(AttributeError):
            t.name = "new"  # type: ignore[misc]


class TestCareerProfile:
    def test_defaults(self) -> None:
        p = CareerProfile(user_id="u1")
        assert p.skills == []
        assert p.preferred_learning_style == LearningStyle.MIXED
        assert p.years_of_experience == 0.0

    def test_frozen(self) -> None:
        p = CareerProfile(user_id="u1")
        with pytest.raises(AttributeError):
            p.user_id = "u2"  # type: ignore[misc]


class TestSkill:
    def test_defaults(self) -> None:
        s = Skill(id="py", name="Python")
        assert s.difficulty == Difficulty.INTERMEDIATE
        assert s.prerequisites == []
        assert s.status == "active"

    def test_frozen(self) -> None:
        s = Skill(id="py", name="Python")
        with pytest.raises(AttributeError):
            s.name = "Java"  # type: ignore[misc]


class TestTechnology:
    def test_defaults(self) -> None:
        t = Technology(id="py", name="Python")
        assert t.lifecycle == TechnologyLifecycle.EMERGING

    def test_frozen(self) -> None:
        t = Technology(id="py", name="Python")
        with pytest.raises(AttributeError):
            t.name = "Java"  # type: ignore[misc]


class TestRoleBlueprint:
    def test_defaults(self) -> None:
        b = RoleBlueprint(track="ml-engineer")
        assert b.required_skills == []
        assert b.version == "1.0"

    def test_frozen(self) -> None:
        b = RoleBlueprint(track="ml")
        with pytest.raises(AttributeError):
            b.track = "new"  # type: ignore[misc]


class TestLearningTopic:
    def test_defaults(self) -> None:
        t = LearningTopic(id="t1", title="Transformers")
        assert t.difficulty == Difficulty.INTERMEDIATE
        assert t.technologies == []


class TestLearningResource:
    def test_defaults(self) -> None:
        r = LearningResource(id="r1", title="Course")
        assert r.language == "en"
        assert r.status == "active"


class TestRecommendation:
    def test_defaults(self) -> None:
        r = Recommendation(id="r1", title="Learn Python")
        assert r.priority == RecommendationPriority.MEDIUM
        assert r.recommendation_type == RecommendationType.LEARN
        assert not r.accepted


class TestTechnologyWatchItem:
    def test_defaults(self) -> None:
        w = TechnologyWatchItem(technology="Kubernetes")
        assert w.status == "monitoring"
        assert w.relevant_tracks == []

    def test_with_datetime(self) -> None:
        dt = datetime(2025, 1, 1)
        w = TechnologyWatchItem(technology="Rust", discovered_at=dt)
        assert w.discovered_at == dt


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

class TestProfileValidation:
    def test_valid_profile(self) -> None:
        p = CareerProfile(user_id="u1", skills=["python", "java"])
        CareerDomainService().validate_profile(p)

    def test_empty_user_id(self) -> None:
        with pytest.raises(ValidationError, match="user_id"):
            CareerDomainService().validate_profile(CareerProfile(user_id=""))

    def test_negative_experience(self) -> None:
        with pytest.raises(ValidationError, match="negative"):
            CareerDomainService().validate_profile(CareerProfile(user_id="u1", years_of_experience=-1))

    def test_negative_learning_hours(self) -> None:
        with pytest.raises(ValidationError, match="negative"):
            CareerDomainService().validate_profile(CareerProfile(user_id="u1", weekly_learning_hours=-1))

    def test_duplicate_skills(self) -> None:
        with pytest.raises(SkillValidationError, match="skills"):
            CareerDomainService().validate_profile(
                CareerProfile(user_id="u1", skills=["python", "python"])
            )


class TestBlueprintValidation:
    def test_valid_blueprint(self) -> None:
        b = RoleBlueprint(track="ml", version="1.0")
        CareerDomainService().validate_blueprint(b)

    def test_empty_track(self) -> None:
        with pytest.raises(BlueprintValidationError, match="track"):
            CareerDomainService().validate_blueprint(RoleBlueprint(track=""))

    def test_empty_version(self) -> None:
        with pytest.raises(BlueprintValidationError, match="version"):
            CareerDomainService().validate_blueprint(RoleBlueprint(track="ml", version=""))

    def test_duplicate_required_skills(self) -> None:
        with pytest.raises(BlueprintValidationError, match="required_skills"):
            CareerDomainService().validate_blueprint(
                RoleBlueprint(track="ml", required_skills=["py", "py"])
            )


class TestSkillGraphValidation:
    def test_valid_skills(self) -> None:
        skills = [
            Skill(id="py", name="Python"),
            Skill(id="ml", name="Machine Learning", prerequisites=["py"]),
        ]
        CareerDomainService().validate_skill_graph(skills)

    def test_empty_id(self) -> None:
        with pytest.raises(SkillValidationError, match="id"):
            CareerDomainService().validate_skill_graph([Skill(id="", name="Python")])

    def test_empty_name(self) -> None:
        with pytest.raises(SkillValidationError, match="name"):
            CareerDomainService().validate_skill_graph([Skill(id="py", name="")])

    def test_duplicate_id(self) -> None:
        with pytest.raises(SkillValidationError, match="duplicate"):
            CareerDomainService().validate_skill_graph([
                Skill(id="py", name="Python"),
                Skill(id="py", name="Java"),
            ])

    def test_negative_hours(self) -> None:
        with pytest.raises(SkillValidationError, match="negative"):
            CareerDomainService().validate_skill_graph(
                [Skill(id="py", name="Python", estimated_learning_hours=-1)]
            )

    def test_invalid_difficulty(self) -> None:
        from aicos.career.validation import validate_skills
        s = Skill(id="py", name="Python", difficulty="invalid")  # type: ignore[arg-type]
        with pytest.raises(SkillValidationError, match="difficulty"):
            validate_skills([s])

    def test_valid_prerequisites(self) -> None:
        skills = [
            Skill(id="py", name="Python"),
            Skill(id="ml", name="ML", prerequisites=["py"]),
        ]
        CareerDomainService().validate_prerequisite_chains(skills)

    def test_missing_prerequisite(self) -> None:
        with pytest.raises(SkillValidationError, match="not found"):
            CareerDomainService().validate_prerequisite_chains(
                [Skill(id="ml", name="ML", prerequisites=["nonexistent"])]
            )

    def test_circular_prerequisite(self) -> None:
        with pytest.raises(SkillValidationError, match="circular"):
            CareerDomainService().validate_prerequisite_chains([
                Skill(id="a", name="A", prerequisites=["b"]),
                Skill(id="b", name="B", prerequisites=["a"]),
            ])

    def test_self_reference_prerequisite(self) -> None:
        with pytest.raises(SkillValidationError, match="circular"):
            CareerDomainService().validate_prerequisite_chains(
                [Skill(id="a", name="A", prerequisites=["a"])]
            )


class TestTechnologyValidation:
    def test_valid_technologies(self) -> None:
        from aicos.career.validation import validate_technologies
        validate_technologies([Technology(id="py", name="Python")])

    def test_empty_id(self) -> None:
        from aicos.career.validation import validate_technologies
        with pytest.raises(TechnologyValidationError, match="id"):
            validate_technologies([Technology(id="", name="Python")])

    def test_empty_name(self) -> None:
        from aicos.career.validation import validate_technologies
        with pytest.raises(TechnologyValidationError, match="name"):
            validate_technologies([Technology(id="py", name="")])

    def test_duplicate_id(self) -> None:
        from aicos.career.validation import validate_technologies
        with pytest.raises(TechnologyValidationError, match="duplicate"):
            validate_technologies([
                Technology(id="py", name="Python"),
                Technology(id="py", name="Java"),
            ])

    def test_negative_hours(self) -> None:
        from aicos.career.validation import validate_technologies
        with pytest.raises(TechnologyValidationError, match="negative"):
            validate_technologies(
                [Technology(id="py", name="Python", estimated_learning_hours=-1)]
            )

    def test_invalid_lifecycle(self) -> None:
        from aicos.career.validation import validate_technologies
        t = Technology(id="py", name="Python", lifecycle="invalid")  # type: ignore[arg-type]
        with pytest.raises(TechnologyValidationError, match="lifecycle"):
            validate_technologies([t])


class TestRecommendationValidation:
    def test_valid_recommendations(self) -> None:
        CareerDomainService().validate_recommendations(
            [Recommendation(id="r1", title="Learn Python")]
        )

    def test_empty_id(self) -> None:
        with pytest.raises(RecommendationValidationError, match="id"):
            CareerDomainService().validate_recommendations(
                [Recommendation(id="", title="Learn")]
            )

    def test_empty_title(self) -> None:
        with pytest.raises(RecommendationValidationError, match="title"):
            CareerDomainService().validate_recommendations(
                [Recommendation(id="r1", title="")]
            )

    def test_duplicate_id(self) -> None:
        with pytest.raises(RecommendationValidationError, match="duplicate"):
            CareerDomainService().validate_recommendations([
                Recommendation(id="r1", title="Learn"),
                Recommendation(id="r1", title="Review"),
            ])


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

class TestProtocolConformance:
    def test_service_conforms_to_protocol(self) -> None:
        assert isinstance(CareerDomainService(), CareerDomainServiceProtocol)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    def test_base_type(self) -> None:
        assert issubclass(ValidationError, CareerDomainError)
        assert issubclass(SkillValidationError, CareerDomainError)
        assert issubclass(TechnologyValidationError, CareerDomainError)
        assert issubclass(BlueprintValidationError, CareerDomainError)
        assert issubclass(RecommendationValidationError, CareerDomainError)
