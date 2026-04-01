"""
Genetic Algorithm Traffic Signal Controller
============================================
Periodically evolves optimal green-light durations for a 4-way
intersection based on current queue lengths.

Chromosome
----------
    [NS_green_duration, EW_green_duration]
    Each gene ∈ [MIN_GREEN, MAX_GREEN]  (default 10–60 s)
    Total cycle constrained to ≤ MAX_CYCLE_LENGTH

GA Parameters (defaults)
------------------------
    Population size : 30
    Generations     : 50
    Selection       : Tournament  (k = 3)
    Crossover       : Single-point, rate = 0.80
    Mutation        : Gaussian σ = 5, rate = 0.05
    Elitism         : Top 2 individuals preserved

Fitness
-------
    f = 1 / (1 + simulated_avg_wait_time)

    A *mini-simulation* runs one full signal cycle for a candidate
    chromosome, using the current queue snapshot.  The lower the
    resulting average wait time, the higher the fitness.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from core.vehicle_physics import (
    MIN_GREEN,
    MAX_GREEN,
    MAX_CYCLE_LENGTH,
    SATURATION_FLOW_RATE,
    YELLOW_DURATION,
)

# ── Configuration ───────────────────────────────────────────────────────────

@dataclass
class GAConfig:
    population_size: int   = 30    # was 20
    generations: int       = 50    # was 30
    tournament_k: int      = 3
    crossover_rate: float  = 0.80
    mutation_rate: float   = 0.10
    mutation_sigma: float  = 5.0
    elitism_count: int     = 2
    eval_cycles: int       = 2
    random_seed: Optional[int] = None


# ── Chromosome helpers ──────────────────────────────────────────────────────

def _random_chromosome(rng: np.random.Generator) -> np.ndarray:
    """Create a random [NS_green, EW_green] chromosome."""
    ns = rng.uniform(MIN_GREEN, MAX_GREEN)
    ew = rng.uniform(MIN_GREEN, MAX_GREEN)
    return _enforce_constraints(np.array([ns, ew]))


def _enforce_constraints(chrom: np.ndarray) -> np.ndarray:
    """Clamp genes to [MIN, MAX] and enforce total cycle limit."""
    chrom = np.clip(chrom, MIN_GREEN, MAX_GREEN)
    total = chrom.sum() + 2 * YELLOW_DURATION  # two yellow phases per cycle
    if total > MAX_CYCLE_LENGTH:
        excess = total - MAX_CYCLE_LENGTH
        # Proportionally reduce both green durations
        ratio = chrom / chrom.sum()
        chrom = chrom - ratio * excess
        chrom = np.clip(chrom, MIN_GREEN, MAX_GREEN)
    return chrom


# ── Fitness evaluation — multi-cycle residual-queue simulation ────────────────

def _evaluate_fitness(
    chromosome: np.ndarray,
    queue_snapshot: dict[str, int],
    num_cycles: int = 2,
    arrival_rate: float = 0.3,
) -> float:
    """
    Multi-cycle residual-queue fitness.

    Simulates *num_cycles* full signal cycles from the current queue snapshot.
    Between cycles, new vehicles arrive at *arrival_rate* veh/s, distributed
    proportionally to current demand. Lower residual queue → higher fitness.
    """
    ns_green = chromosome[0]
    ew_green = chromosome[1]

    ns_demand = queue_snapshot.get("N", 0) + queue_snapshot.get("S", 0)
    ew_demand = queue_snapshot.get("E", 0) + queue_snapshot.get("W", 0)
    total_demand = ns_demand + ew_demand

    if total_demand == 0:
        return 1.0

    # Demand split for proportional arrival distribution
    ns_demand_ratio = ns_demand / total_demand
    ew_demand_ratio = ew_demand / total_demand

    # Duration of one full signal cycle (both greens + two yellows)
    cycle_time = ns_green + ew_green + 2 * YELLOW_DURATION

    # Max vehicles dischargeable per phase per cycle (2 approaches each)
    ns_capacity = SATURATION_FLOW_RATE * ns_green * 2
    ew_capacity = SATURATION_FLOW_RATE * ew_green * 2

    # Multi-cycle simulation
    ns_queue = float(ns_demand)
    ew_queue = float(ew_demand)
    total_wait = 0.0

    for _ in range(num_cycles):
        # All currently queued vehicles accumulate wait for this cycle
        total_wait += (ns_queue + ew_queue) * cycle_time

        # Discharge (capped at queue size)
        ns_queue -= min(ns_queue, ns_capacity)
        ew_queue -= min(ew_queue, ew_capacity)

        # New arrivals between cycles
        new_arrivals = arrival_rate * cycle_time
        ns_queue += new_arrivals * ns_demand_ratio
        ew_queue += new_arrivals * ew_demand_ratio

    total_residual = ns_queue + ew_queue

    # Penalise starving the busier direction
    ns_green_ratio = ns_green / (ns_green + ew_green)
    ew_green_ratio = ew_green / (ns_green + ew_green)
    imbalance = (
        abs(ns_demand_ratio - ns_green_ratio) * ns_demand +
        abs(ew_demand_ratio - ew_green_ratio) * ew_demand
    )

    cost = total_residual + 0.3 * imbalance + 0.01 * total_wait
    return 1.0 / (1.0 + cost)


# ── GA Controller ───────────────────────────────────────────────────────────

class GAController:
    """
    Evolves optimal signal timings using a Genetic Algorithm.

    Usage
    -----
        controller = GAController()
        # When it's time to re-optimise (every ~60 sim-seconds):
        ns, ew = controller.evolve(current_queues)
        # Between evolutions:
        ns, ew = controller.get_current_timings()

    Parameters
    ----------
    config : GAConfig, optional
        Hyper-parameters for the GA.
    """

    def __init__(self, config: GAConfig | None = None):
        self.config = config or GAConfig()
        self.rng = np.random.default_rng(self.config.random_seed)

        # Current best solution (starts with equal split)
        self._best_chromosome = np.array([30.0, 30.0])
        self._best_fitness = 0.0

        # Generation tracking
        self.generation_count = 0
        self.evolution_history: list[dict] = []

    def evolve(self, current_queues: dict[str, int]) -> tuple[float, float]:
        """
        Run a full GA evolution and return the best timings found.

        Parameters
        ----------
        current_queues : dict
            Current vehicle counts, e.g. {"N": 12, "S": 8, "E": 25, "W": 3}

        Returns
        -------
        tuple[float, float]
            (NS_green_duration, EW_green_duration) of the best solution.
        """
        cfg = self.config

        # 1. Initialise population — mix of random + smart seeds
        population = [_random_chromosome(self.rng) for _ in range(cfg.population_size)]

        # Seed 0: previous best (warm start)
        population[0] = self._best_chromosome.copy()

        # Seed 1: proportional timing based on current queue demand
        ns_demand = current_queues.get("N", 0) + current_queues.get("S", 0)
        ew_demand = current_queues.get("E", 0) + current_queues.get("W", 0)
        total_demand = ns_demand + ew_demand
        if total_demand > 0:
            usable = MAX_CYCLE_LENGTH - 2 * YELLOW_DURATION
            prop_ns = max(MIN_GREEN, min(MAX_GREEN, usable * ns_demand / total_demand))
            prop_ew = max(MIN_GREEN, min(MAX_GREEN, usable * ew_demand / total_demand))
            population[1] = _enforce_constraints(np.array([prop_ns, prop_ew]))

        best_ever = None
        best_ever_fitness = -1.0

        for gen in range(cfg.generations):
            # 2. Evaluate fitness
            fitnesses = np.array([
                _evaluate_fitness(ind, current_queues, cfg.eval_cycles)
                for ind in population
            ])

            # Track best
            gen_best_idx = int(np.argmax(fitnesses))
            if fitnesses[gen_best_idx] > best_ever_fitness:
                best_ever_fitness = fitnesses[gen_best_idx]
                best_ever = population[gen_best_idx].copy()

            # 3. Elitism — carry over top individuals
            elite_indices = np.argsort(fitnesses)[-cfg.elitism_count:]
            elites = [population[i].copy() for i in elite_indices]

            # 4. Build next generation
            next_gen: list[np.ndarray] = list(elites)

            while len(next_gen) < cfg.population_size:
                # Selection (tournament)
                parent_a = self._tournament_select(population, fitnesses)
                parent_b = self._tournament_select(population, fitnesses)

                # Crossover (BLX-α blend)
                if self.rng.random() < cfg.crossover_rate:
                    child = self._crossover(parent_a, parent_b)
                else:
                    child = parent_a.copy()

                # Mutation
                child = self._mutate(child)

                # Enforce constraints
                child = _enforce_constraints(child)
                next_gen.append(child)

            population = next_gen

        # Store best result
        if best_ever is not None:
            self._best_chromosome = best_ever
            self._best_fitness = best_ever_fitness

        self.generation_count += cfg.generations

        # Log this evolution run
        self.evolution_history.append({
            "generation": self.generation_count,
            "best_fitness": round(best_ever_fitness, 6),
            "best_ns_green": round(self._best_chromosome[0], 2),
            "best_ew_green": round(self._best_chromosome[1], 2),
            "queues_at_evolution": dict(current_queues),
        })

        return self.get_current_timings()

    def get_current_timings(self) -> tuple[float, float]:
        """Return the last-evolved (NS_green, EW_green) durations."""
        return (
            round(float(self._best_chromosome[0]), 2),
            round(float(self._best_chromosome[1]), 2),
        )

    def get_evolution_history(self) -> list[dict]:
        """Return a log of all evolution runs for analysis."""
        return self.evolution_history

    # ── GA Operators ────────────────────────────────────────────────────

    def _tournament_select(
        self,
        population: list[np.ndarray],
        fitnesses: np.ndarray,
    ) -> np.ndarray:
        """Tournament selection with k competitors."""
        indices = self.rng.choice(
            len(population), size=self.config.tournament_k, replace=False
        )
        best_idx = indices[np.argmax(fitnesses[indices])]
        return population[best_idx].copy()

    def _crossover(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        BLX-α blend crossover for real-valued chromosomes.
        More effective than single-point for continuous gene values.
        α = 0.5 allows children to fall slightly outside the parent range.
        """
        alpha = 0.5
        child = np.empty_like(a)
        for i in range(len(a)):
            lo = min(a[i], b[i])
            hi = max(a[i], b[i])
            span = hi - lo
            child[i] = self.rng.uniform(lo - alpha * span, hi + alpha * span)
        return child

    def _mutate(self, chrom: np.ndarray) -> np.ndarray:
        """Apply Gaussian mutation to each gene independently."""
        for i in range(len(chrom)):
            if self.rng.random() < self.config.mutation_rate:
                chrom[i] += self.rng.normal(0, self.config.mutation_sigma)
        return chrom

    def __repr__(self) -> str:
        ns, ew = self.get_current_timings()
        return (
            f"GAController(ns={ns}s, ew={ew}s, "
            f"generations_run={self.generation_count}, "
            f"fitness={self._best_fitness:.4f})"
        )
