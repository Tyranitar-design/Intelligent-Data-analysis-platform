"""ALNS VRPTW Solver - Step 1f
主循环：Destroy + Repair + SA 接受准则 + 自适应权重更新"""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

from alns_vrptw_state import VRPTWState, create_vrptw_instance
from alns_vrptw_destroy import random_remove, worst_remove, time_warp_remove, shaw_remove
from alns_vrptw_repair import greedy_insert, regret2_insert, random_insert


@dataclass
class ALNSConfig:
    iterations: int = 300
    q_min: int = 3
    q_max: int = 6
    temperature: float = 1000.0
    cooling: float = 0.995
    min_temperature: float = 1e-3
    segment_length: int = 50
    reaction: float = 0.2
    sigma_best: float = 5.0
    sigma_improve: float = 3.0
    sigma_accept: float = 1.0
    sigma_reject: float = 0.0


def roulette_select(weights: np.ndarray, rng: np.random.Generator) -> int:
    weights = np.asarray(weights, dtype=float)
    total = weights.sum()
    if total <= 0:
        return int(rng.integers(0, len(weights)))
    probs = weights / total
    return int(rng.choice(len(weights), p=probs))


def build_initial_state(n: int = 20, seed: int = 42) -> VRPTWState:
    """用单客户路线构造一个可行初始解。"""
    customers, depot, vehicle = create_vrptw_instance(n=n, seed=seed)
    routes = [[i] for i in range(1, n + 1)]
    return VRPTWState(routes, customers, vehicle, depot)


def alns_vrptw(initial_state: VRPTWState, config: ALNSConfig = ALNSConfig(), seed: int = 42):
    rng = np.random.default_rng(seed)

    destroy_ops: List[Tuple[str, callable]] = [
        ("random_remove", random_remove),
        ("worst_remove", worst_remove),
        ("time_warp_remove", time_warp_remove),
        ("shaw_remove", shaw_remove),
    ]
    repair_ops: List[Tuple[str, callable]] = [
        ("greedy_insert", greedy_insert),
        ("regret2_insert", regret2_insert),
        ("random_insert", random_insert),
    ]

    d_weights = np.ones(len(destroy_ops), dtype=float)
    r_weights = np.ones(len(repair_ops), dtype=float)
    d_scores = np.zeros(len(destroy_ops), dtype=float)
    r_scores = np.zeros(len(repair_ops), dtype=float)
    d_uses = np.zeros(len(destroy_ops), dtype=float)
    r_uses = np.zeros(len(repair_ops), dtype=float)

    current = initial_state.copy()
    current_cost = current.objective()
    best = current.copy()
    best_cost = current_cost
    T = config.temperature
    history = []

    for it in range(1, config.iterations + 1):
        d_idx = roulette_select(d_weights, rng)
        r_idx = roulette_select(r_weights, rng)
        q = int(rng.integers(config.q_min, config.q_max + 1))

        _, d_op = destroy_ops[d_idx]
        _, r_op = repair_ops[r_idx]

        destroyed_state, removed = d_op(current.copy(), rng, q=q)
        candidate = r_op(destroyed_state, removed, rng)
        candidate_cost = candidate.objective()

        accepted = False
        reward = config.sigma_reject

        if candidate_cost < best_cost:
            best = candidate.copy()
            best_cost = candidate_cost
            current = candidate
            current_cost = candidate_cost
            accepted = True
            reward = config.sigma_best
        elif candidate_cost < current_cost:
            current = candidate
            current_cost = candidate_cost
            accepted = True
            reward = config.sigma_improve
        else:
            delta = candidate_cost - current_cost
            if T > config.min_temperature:
                p = float(np.exp(-delta / max(T, 1e-9)))
                if rng.random() < p:
                    current = candidate
                    current_cost = candidate_cost
                    accepted = True
                    reward = config.sigma_accept

        d_scores[d_idx] += reward
        r_scores[r_idx] += reward
        d_uses[d_idx] += 1
        r_uses[r_idx] += 1

        if it % config.segment_length == 0:
            for i in range(len(d_weights)):
                avg = d_scores[i] / max(1.0, d_uses[i])
                d_weights[i] = (1 - config.reaction) * d_weights[i] + config.reaction * avg
                d_scores[i] = 0.0
                d_uses[i] = 0.0
            for i in range(len(r_weights)):
                avg = r_scores[i] / max(1.0, r_uses[i])
                r_weights[i] = (1 - config.reaction) * r_weights[i] + config.reaction * avg
                r_scores[i] = 0.0
                r_uses[i] = 0.0

        T = max(T * config.cooling, config.min_temperature)

        history.append({
            "iter": it,
            "current_cost": current_cost,
            "best_cost": best_cost,
            "temperature": T,
            "destroy": destroy_ops[d_idx][0],
            "repair": repair_ops[r_idx][0],
            "accepted": accepted,
            "candidate_cost": candidate_cost,
        })

    return best, history, {
        "destroy_weights": d_weights,
        "repair_weights": r_weights,
        "destroy_names": [n for n, _ in destroy_ops],
        "repair_names": [n for n, _ in repair_ops],
    }


if __name__ == "__main__":
    init_state = build_initial_state(n=20, seed=42)
    print("=== Step 1f: ALNS VRPTW 主循环测试 ===")
    print(f"初始目标: {init_state.objective():.2f}")
    print(f"初始路线数: {len(init_state.routes)}")
    print(f"初始可行性: {init_state.is_feasible()}")
    print()

    best, history, info = alns_vrptw(init_state, ALNSConfig(iterations=300), seed=42)

    initial_cost = init_state.objective()
    best_cost = best.objective()
    improvement = (initial_cost - best_cost) / initial_cost * 100

    print("=== Step 1f 结果 ===")
    print(f"初始目标: {initial_cost:.2f}")
    print(f"最优目标: {best_cost:.2f}")
    print(f"改善率: {improvement:.2f}%")
    print(f"路线数: {len(best.routes)}")
    print(f"时间窗违规: {sum(best.route_time_warp(r) for r in best.routes):.2f}")
    print(f"可行性: {best.is_feasible()}")
    print()
    print("=== 算子权重 ===")
    for name, weight in zip(info["destroy_names"], info["destroy_weights"]):
        print(f"Destroy {name}: {weight:.3f}")
    for name, weight in zip(info["repair_names"], info["repair_weights"]):
        print(f"Repair  {name}: {weight:.3f}")
