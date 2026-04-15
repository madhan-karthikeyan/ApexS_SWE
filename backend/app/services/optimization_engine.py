from __future__ import annotations

from dataclasses import dataclass, field
import logging
import random
import time
from typing import Dict, List

import pulp

try:
    from pulp import LpBinary, LpMaximize, LpProblem, LpVariable, PULP_CBC_CMD, lpSum, value
except Exception:  # pragma: no cover
    LpBinary = None

from app.models.story import UserStory
from app.services.preprocessing import normalize_skill, normalize_skills, normalize_status, parse_depends_on


logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    selected_stories: list[UserStory]
    rejected_stories: list[UserStory]
    total_value: float
    total_risk: float
    capacity_used: int
    solver_status: str
    risk_threshold: float = 0.0
    available_skills: list[str] | None = None
    capacity_limit: int = 0
    warnings: list[str] = field(default_factory=list)
    feasibility_counts: dict[str, int] = field(default_factory=dict)
    score_distribution: dict[str, float] = field(default_factory=dict)
    objective_score: float = 0.0
    runtime_ms: float = 0.0
    sprint_completion_ratio: float | None = None
    skill_coverage: float = 0.0
    selected_count: int = 0


class OptimizationEngine:
    NON_PLANNABLE_STATUSES = {"done", "closed", "resolved", "completed"}
    STORY_POINTS_MAX = 13.0
    BUSINESS_VALUE_MAX = 10.0

    def __init__(
        self,
        *,
        enforce_capacity: bool = True,
        enforce_risk: bool = True,
        enforce_skill: bool = True,
        enforce_dependencies: bool = True,
        random_seed: int = 42,
        use_milp: bool = True,
    ) -> None:
        self.enforce_capacity = enforce_capacity
        self.enforce_risk = enforce_risk
        self.enforce_skill = enforce_skill
        self.enforce_dependencies = enforce_dependencies
        self.random_seed = int(random_seed)
        self.use_milp = use_milp

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(maximum, float(value)))

    def _normalized_weights(self, weights: Dict[str, float]) -> dict[str, float]:
        raw = {
            "urgency_weight": max(0.0, float(weights.get("urgency_weight", 0.33))),
            "value_weight": max(0.0, float(weights.get("value_weight", 0.33))),
            "alignment_weight": max(0.0, float(weights.get("alignment_weight", 0.33))),
        }
        total = raw["urgency_weight"] + raw["value_weight"] + raw["alignment_weight"]
        if total <= 0:
            return {"urgency_weight": 0.33, "value_weight": 0.34, "alignment_weight": 0.33}
        return {key: value / total for key, value in raw.items()}

    def _score_components(self, story: UserStory, weights: Dict[str, float]) -> dict[str, float]:
        normalized_weights = self._normalized_weights(weights)
        normalized_story_points = self._clamp(float(story.story_points) / self.STORY_POINTS_MAX)
        normalized_business_value = self._clamp(float(story.business_value) / self.BUSINESS_VALUE_MAX)
        normalized_risk_score = self._clamp(float(story.risk_score))

        effort_component = self._clamp(1.0 - normalized_story_points)
        value_component = normalized_business_value
        risk_component = self._clamp(1.0 - normalized_risk_score)

        urgency_contribution = normalized_weights["urgency_weight"] * effort_component
        value_contribution = normalized_weights["value_weight"] * value_component
        alignment_contribution = normalized_weights["alignment_weight"] * risk_component
        total_score = self._clamp(urgency_contribution + value_contribution + alignment_contribution)

        return {
            "score": total_score,
            "urgency_contribution": urgency_contribution,
            "value_contribution": value_contribution,
            "alignment_contribution": alignment_contribution,
            "normalized_story_points": normalized_story_points,
            "normalized_business_value": normalized_business_value,
            "normalized_risk_score": normalized_risk_score,
        }

    def _story_score(self, story: UserStory, weights: Dict[str, float]) -> float:
        return self._score_components(story, weights)["score"]

    def _score_distribution(self, stories: list[UserStory], weights: Dict[str, float]) -> dict[str, float]:
        if not stories:
            return {"min": 0.0, "max": 0.0, "mean": 0.0}
        scores = [self._story_score(story, weights) for story in stories]
        return {
            "min": float(min(scores)),
            "max": float(max(scores)),
            "mean": float(sum(scores) / len(scores)),
        }

    def _objective_score(self, stories: list[UserStory], weights: Dict[str, float]) -> float:
        if not stories:
            return 0.0
        return float(sum(self._story_score(story, weights) for story in stories))

    @staticmethod
    def _is_plannable_status(status: str | None) -> bool:
        normalized = normalize_status(status)
        if not normalized:
            return True
        return normalized not in OptimizationEngine.NON_PLANNABLE_STATUSES

    def _build_result(
        self,
        *,
        stories: list[UserStory],
        selected: list[UserStory],
        weights: Dict[str, float],
        solver_status: str,
        risk_threshold: float,
        available_skills: list[str],
        capacity: int,
        warnings: list[str] | None = None,
        feasibility_counts: dict[str, int] | None = None,
        score_distribution: dict[str, float] | None = None,
        runtime_ms: float = 0.0,
    ) -> OptimizationResult:
        selected_ids = {s.story_id for s in selected}
        rejected = [s for s in stories if s.story_id not in selected_ids]
        total_value = float(sum(s.business_value for s in selected))
        total_risk = float(sum(s.risk_score for s in selected) / max(len(selected), 1))
        objective_score = self._objective_score(selected, weights)
        selected_count = len(selected)

        completion_values = [
            self._clamp(float(getattr(story, "sprint_completed", 0.0)))
            for story in selected
            if hasattr(story, "sprint_completed")
        ]
        sprint_completion_ratio = float(sum(completion_values) / len(completion_values)) if completion_values else None

        feasible_skill_set = {s.required_skill for s in stories if s.required_skill}
        selected_skill_set = {s.required_skill for s in selected if s.required_skill}
        skill_coverage = float(len(selected_skill_set) / len(feasible_skill_set)) if feasible_skill_set else 1.0

        return OptimizationResult(
            selected_stories=selected,
            rejected_stories=rejected,
            total_value=total_value,
            total_risk=total_risk,
            capacity_used=sum(s.story_points for s in selected),
            solver_status=solver_status,
            risk_threshold=risk_threshold,
            available_skills=available_skills,
            capacity_limit=capacity,
            warnings=warnings or [],
            feasibility_counts=feasibility_counts
            or {
                "total": len(stories),
                "filtered_by_risk": 0,
                "filtered_by_skill": 0,
                "filtered_by_dependency": 0,
                "filtered_by_status": 0,
            },
            score_distribution=score_distribution or self._score_distribution(selected, weights),
            objective_score=objective_score,
            runtime_ms=float(runtime_ms),
            sprint_completion_ratio=sprint_completion_ratio,
            skill_coverage=skill_coverage,
            selected_count=selected_count,
        )

    def _preprocess_stories(self, stories: list[UserStory]) -> list[UserStory]:
        processed: list[UserStory] = []
        for story in stories:
            story.status = normalize_status(story.status) or "backlog"
            story.required_skill = normalize_skill(story.required_skill) if story.required_skill else None
            story.depends_on = parse_depends_on(story.depends_on)
            processed.append(story)
        return processed

    def _filter_feasible_stories(
        self,
        stories: list[UserStory],
        *,
        risk_threshold: float,
        available_skills: list[str],
    ) -> tuple[list[UserStory], dict[str, int], list[str]]:
        allowed: list[UserStory] = []
        counts = {
            "total": len(stories),
            "filtered_by_risk": 0,
            "filtered_by_skill": 0,
            "filtered_by_dependency": 0,
            "filtered_by_status": 0,
        }
        warnings: list[str] = []
        story_map = {s.story_id: s for s in stories}

        for story in stories:
            deps = list(story.depends_on or [])
            deps_ok = all(dep in story_map for dep in deps)
            risk_ok = story.risk_score <= risk_threshold
            skill_ok = not story.required_skill or story.required_skill in available_skills or not available_skills
            status_ok = self._is_plannable_status(story.status)

            if self.enforce_dependencies and not deps_ok:
                counts["filtered_by_dependency"] += 1
                missing = [dep for dep in deps if dep not in story_map]
                message = f"Story {story.story_id} filtered: dependency missing ({', '.join(missing)})."
                logger.warning(message)
                warnings.append(message)
                continue
            if self.enforce_skill and not skill_ok:
                counts["filtered_by_skill"] += 1
                message = f"Story {story.story_id} filtered: skill mismatch ('{story.required_skill}')."
                logger.warning(message)
                warnings.append(message)
                continue
            if self.enforce_risk and not risk_ok:
                counts["filtered_by_risk"] += 1
                message = f"Story {story.story_id} filtered: risk {story.risk_score:.2f} above threshold {risk_threshold:.2f}."
                logger.warning(message)
                warnings.append(message)
                continue
            if not status_ok:
                counts["filtered_by_status"] += 1
                message = f"Story {story.story_id} filtered: status '{story.status}' not plannable."
                logger.warning(message)
                warnings.append(message)
                continue

            allowed.append(story)

        return allowed, counts, warnings

    def _greedy_selection(
        self,
        *,
        stories: list[UserStory],
        weights: Dict[str, float],
        capacity: int,
        deterministic_random: bool = False,
    ) -> list[UserStory]:
        ranked = sorted(stories, key=lambda story: (self._story_score(story, weights), story.story_id), reverse=True)
        if deterministic_random:
            rng = random.Random(self.random_seed)
            rng.shuffle(ranked)

        selected: list[UserStory] = []
        selected_ids: set[str] = set()
        used_capacity = 0
        changed = True

        while changed:
            changed = False
            for story in ranked:
                if story.story_id in selected_ids:
                    continue
                if self.enforce_capacity and (used_capacity + story.story_points > capacity):
                    continue
                if self.enforce_dependencies and any(dep not in selected_ids for dep in (story.depends_on or [])):
                    continue
                selected.append(story)
                selected_ids.add(story.story_id)
                used_capacity += story.story_points
                changed = True

        return selected

    def _milp_select(
        self,
        *,
        stories: list[UserStory],
        weights: Dict[str, float],
        capacity: int,
    ) -> tuple[list[UserStory], str]:
        prob = LpProblem("SprintBacklogOptimization", LpMaximize)
        x = {s.story_id: LpVariable(f"x_{s.story_id}", cat=LpBinary) for s in stories}

        prob += lpSum(x[s.story_id] * self._story_score(s, weights) for s in stories)

        if self.enforce_capacity:
            prob += lpSum(x[s.story_id] * s.story_points for s in stories) <= capacity

        if self.enforce_dependencies:
            for story in stories:
                for dep_id in story.depends_on or []:
                    if dep_id in x:
                        prob += x[story.story_id] <= x[dep_id]
                    else:
                        prob += x[story.story_id] == 0

        solver = PULP_CBC_CMD(msg=0, timeLimit=15, threads=1)
        prob.solve(solver)
        status_name = pulp.LpStatus.get(prob.status, str(prob.status))
        if status_name != "Optimal":
            return [], status_name

        selected = [story for story in stories if value(x[story.story_id]) == 1]
        return selected, status_name

    def solve(
        self,
        stories: List[UserStory],
        weights: Dict[str, float],
        capacity: int,
        risk_threshold: float,
        available_skills: List[str],
    ) -> OptimizationResult:
        start = time.perf_counter()
        normalized_skills = normalize_skills(available_skills)
        prepared = self._preprocess_stories(list(stories))

        if not prepared:
            return self._build_result(
                stories=[],
                selected=[],
                weights=weights,
                solver_status="empty",
                risk_threshold=risk_threshold,
                available_skills=normalized_skills,
                capacity=capacity,
                feasibility_counts={
                    "total": 0,
                    "filtered_by_risk": 0,
                    "filtered_by_skill": 0,
                    "filtered_by_dependency": 0,
                    "filtered_by_status": 0,
                },
                score_distribution={"min": 0.0, "max": 0.0, "mean": 0.0},
                runtime_ms=(time.perf_counter() - start) * 1000.0,
            )

        feasible, counts, filter_warnings = self._filter_feasible_stories(
            prepared,
            risk_threshold=risk_threshold,
            available_skills=normalized_skills,
        )
        score_distribution = self._score_distribution(feasible, weights)

        if not feasible:
            return self._build_result(
                stories=prepared,
                selected=[],
                weights=weights,
                solver_status="no-feasible-stories",
                risk_threshold=risk_threshold,
                available_skills=normalized_skills,
                capacity=capacity,
                warnings=[
                    "No stories passed feasibility checks.",
                    *filter_warnings,
                ],
                feasibility_counts=counts,
                score_distribution={"min": 0.0, "max": 0.0, "mean": 0.0},
                runtime_ms=(time.perf_counter() - start) * 1000.0,
            )

        if not self.use_milp or LpBinary is None:
            selected = self._greedy_selection(stories=feasible, weights=weights, capacity=capacity)
            warnings = ["MILP failed -> using greedy approximation (milp-disabled-or-unavailable).", *filter_warnings]
            return self._build_result(
                stories=prepared,
                selected=selected,
                weights=weights,
                solver_status="greedy-fallback:milp-disabled-or-unavailable",
                risk_threshold=risk_threshold,
                available_skills=normalized_skills,
                capacity=capacity,
                warnings=warnings,
                feasibility_counts=counts,
                score_distribution=score_distribution,
                runtime_ms=(time.perf_counter() - start) * 1000.0,
            )

        try:
            selected, status_name = self._milp_select(stories=feasible, weights=weights, capacity=capacity)
        except Exception as exc:
            logger.exception("MILP execution error: %s", exc)
            selected = []
            status_name = "ExecutionError"

        if status_name != "Optimal":
            fallback_selected = self._greedy_selection(stories=feasible, weights=weights, capacity=capacity)
            warnings = [f"MILP failed -> using greedy approximation (milp-status-{status_name.lower()}).", *filter_warnings]
            return self._build_result(
                stories=prepared,
                selected=fallback_selected,
                weights=weights,
                solver_status=f"greedy-fallback:milp-status-{status_name.lower()}",
                risk_threshold=risk_threshold,
                available_skills=normalized_skills,
                capacity=capacity,
                warnings=warnings,
                feasibility_counts=counts,
                score_distribution=score_distribution,
                runtime_ms=(time.perf_counter() - start) * 1000.0,
            )

        return self._build_result(
            stories=prepared,
            selected=selected,
            weights=weights,
            solver_status=f"milp-cbc:{status_name}",
            risk_threshold=risk_threshold,
            available_skills=normalized_skills,
            capacity=capacity,
            warnings=filter_warnings,
            feasibility_counts=counts,
            score_distribution=score_distribution,
            runtime_ms=(time.perf_counter() - start) * 1000.0,
        )

    def solve_baseline(
        self,
        *,
        stories: List[UserStory],
        mode: str,
        context_weights: Dict[str, float],
        learned_weights: Dict[str, float],
        capacity: int,
        risk_threshold: float,
        available_skills: List[str],
        random_seed: int | None = None,
    ) -> OptimizationResult:
        mode_key = mode.strip().lower()
        if mode_key == "fixed_weight_milp":
            fixed = {"urgency_weight": 1.0 / 3.0, "value_weight": 1.0 / 3.0, "alignment_weight": 1.0 / 3.0}
            engine = OptimizationEngine(
                enforce_capacity=self.enforce_capacity,
                enforce_risk=self.enforce_risk,
                enforce_skill=self.enforce_skill,
                enforce_dependencies=self.enforce_dependencies,
                random_seed=self.random_seed,
                use_milp=True,
            )
            result = engine.solve(stories, fixed, capacity, risk_threshold, available_skills)
            result.solver_status = f"baseline:fixed_weight_milp:{result.solver_status}"
            return result

        if mode_key == "context_only":
            engine = OptimizationEngine(
                enforce_capacity=self.enforce_capacity,
                enforce_risk=self.enforce_risk,
                enforce_skill=self.enforce_skill,
                enforce_dependencies=self.enforce_dependencies,
                random_seed=self.random_seed,
                use_milp=True,
            )
            result = engine.solve(stories, context_weights, capacity, risk_threshold, available_skills)
            result.solver_status = f"baseline:context_only:{result.solver_status}"
            return result

        if mode_key == "greedy_feasible":
            engine = OptimizationEngine(
                enforce_capacity=self.enforce_capacity,
                enforce_risk=self.enforce_risk,
                enforce_skill=self.enforce_skill,
                enforce_dependencies=self.enforce_dependencies,
                random_seed=self.random_seed,
                use_milp=False,
            )
            result = engine.solve(stories, learned_weights, capacity, risk_threshold, available_skills)
            result.solver_status = "baseline:greedy_feasible"
            return result

        if mode_key == "random_feasible":
            rng_seed = self.random_seed if random_seed is None else int(random_seed)
            start = time.perf_counter()
            normalized_skills = normalize_skills(available_skills)
            prepared = self._preprocess_stories(list(stories))
            feasible, counts, warnings = self._filter_feasible_stories(
                prepared,
                risk_threshold=risk_threshold,
                available_skills=normalized_skills,
            )
            rng = random.Random(rng_seed)
            feasible = sorted(feasible, key=lambda s: s.story_id)
            rng.shuffle(feasible)
            selected = self._greedy_selection(
                stories=feasible,
                weights={"urgency_weight": 1 / 3, "value_weight": 1 / 3, "alignment_weight": 1 / 3},
                capacity=capacity,
                deterministic_random=True,
            )
            result = self._build_result(
                stories=prepared,
                selected=selected,
                weights={"urgency_weight": 1 / 3, "value_weight": 1 / 3, "alignment_weight": 1 / 3},
                solver_status=f"baseline:random_feasible:seed-{rng_seed}",
                risk_threshold=risk_threshold,
                available_skills=normalized_skills,
                capacity=capacity,
                warnings=warnings,
                feasibility_counts=counts,
                score_distribution=self._score_distribution(feasible, {"urgency_weight": 1 / 3, "value_weight": 1 / 3, "alignment_weight": 1 / 3}),
                runtime_ms=(time.perf_counter() - start) * 1000.0,
            )
            return result

        raise ValueError(f"Unsupported baseline mode: {mode}")
