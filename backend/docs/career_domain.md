# Career Intelligence Domain

## Architecture

```
Application
      │
      ▼
CareerDomainService
      │
      ▼
  ┌──────────────────────────────┐
  │  Domain Models (pure data)   │
  │  Enums                       │
  │  Validation (pure functions) │
  │  Exceptions                  │
  └──────────────────────────────┘
```

No AI, retrieval, or infrastructure dependencies.

## Domain Models

| Entity | Fields | Purpose |
|---|---|---|
| `CareerTrack` | id, name, description, category, difficulty, estimated_duration, target_roles, status | A named career pathway |
| `CareerProfile` | user_id, current_role, years_of_experience, education, skills, skill_levels, interests, learning_style, weekly_hours, career_goals, target_tracks, strengths, improvement_areas, completed_topics | A user's full career profile |
| `Skill` | id, name, description, category, difficulty, estimated_learning_hours, prerequisites, related_technologies, status | A learnable skill |
| `Technology` | id, name, description, category, lifecycle, industry_adoption, market_demand, relevant_tracks, prerequisites, estimated_learning_hours | A tracked technology |
| `RoleBlueprint` | track, required_skills, optional_skills, recommended_order, minimum_requirements, version, last_updated | Structured role requirements |
| `LearningTopic` | id, title, description, skill, technologies, difficulty, estimated_hours, prerequisites | A learning topic |
| `LearningResource` | id, title, resource_type, provider, language, quality_score, estimated_duration, url, last_verified, status | A curated resource |
| `Recommendation` | id, title, description, reason, priority, type, relevant_track, estimated_effort, accepted | A domain recommendation |
| `TechnologyWatchItem` | technology, summary, status, relevant_tracks, importance, recommended_action, discovered_at | A watched technology |

## Entity Relationships

```
CareerTrack
  ├── target_roles: list[str]
  └── category: CareerTrackCategory

CareerProfile
  ├── skills → Skill.id
  ├── skill_levels → Skill.id → Difficulty
  └── target_tracks → CareerTrack.id

Skill
  └── prerequisites → Skill.id

Technology
  ├── relevant_tracks → CareerTrack.id
  └── prerequisites → Skill.id

RoleBlueprint
  ├── required_skills → Skill.id
  ├── optional_skills → Skill.id
  └── recommended_order → Skill.id

LearningTopic
  ├── skill → Skill.id
  └── technologies → Technology.id

Recommendation
  └── relevant_track → CareerTrack.id
```

## Enums

| Enum | Values |
|---|---|
| `Difficulty` | beginner, intermediate, advanced, expert |
| `TechnologyLifecycle` | experimental, emerging, growing, recommended, industry_standard, legacy, deprecated |
| `RecommendationPriority` | low, medium, high, critical |
| `RecommendationType` | learn, review, upgrade, replace, remove |
| `LearningStyle` | reading, videos, hands_on, mixed |
| `CareerTrackCategory` | ai, cloud, devops, testing, data, security, software, management |

## Validation Rules

- IDs must not be empty
- Names must not be blank
- Learning hours must not be negative
- Years of experience must not be negative
- Duplicate IDs are rejected (skills, technologies, recommendations)
- Duplicate list entries are rejected (profile skills, blueprint skills)
- Prerequisites must reference existing skills
- Prerequisite chains must be acyclic
- Difficulty must be a valid enum value
- Technology lifecycle must be a valid enum value

## Domain Service

`CareerDomainService` provides five validation methods:

| Method | Validates | Raises |
|---|---|---|
| `validate_profile()` | CareerProfile | `ValidationError`, `SkillValidationError` |
| `validate_blueprint()` | RoleBlueprint | `BlueprintValidationError` |
| `validate_skill_graph()` | list[Skill] | `SkillValidationError` |
| `validate_prerequisite_chains()` | list[Skill] | `SkillValidationError` |
| `validate_recommendations()` | list[Recommendation] | `RecommendationValidationError` |

## Exception Hierarchy

```
CareerDomainError
├── ValidationError
├── SkillValidationError
├── TechnologyValidationError
├── BlueprintValidationError
└── RecommendationValidationError
```

## Dependency Injection

```python
from aicos.career import register_career, CareerDomainService

register_career(container, settings)
service = container.resolve(CareerDomainService)
```

## Logging

Logger name: `aicos.career`

Logged at `DEBUG` on validation success, `WARNING` on validation failure:
- user_id
- skill_count
- recommendation_count
- track

Personal information, skill names, and detailed entity data are never logged.

## Extension Points

- **New model**: add a frozen dataclass to `models.py`
- **New enum**: add to `enums.py`
- **New validation**: add a pure function to `validation.py`, expose via `CareerDomainService`
- **Custom service**: implement `CareerDomainServiceProtocol`
