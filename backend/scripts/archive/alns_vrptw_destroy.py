"""ALNS VRPTW Destroy Operators - 带时间窗感知的破坏算子"""
import numpy as np
from alns_vrptw_state import VRPTWState

# ============ Destroy 算子 ============

def random_remove(state: VRPTWState, rng: np.random.Generator, q: int = 5):
    """随机移除 q 个客户"""
    removed = []
    
    # 收集所有客户
    all_customers = []
    for route in state.routes:
        all_customers.extend(route)
    
    if len(all_customers) < q:
        q = len(all_customers)
    
    # 随机选择
    indices = rng.choice(len(all_customers), size=q, replace=False)
    to_remove = {all_customers[i] for i in indices}
    
    # 从路线中移除
    new_routes = []
    for route in state.routes:
        new_route = [c for c in route if c not in to_remove]
        if new_route:  # 保留非空路线
            new_routes.append(new_route)
    
    new_state = VRPTWState(new_routes, state.customers, state.vehicle, state.depot)
    new_state.unassigned = set(to_remove)
    
    return new_state, list(to_remove)


def worst_remove(state: VRPTWState, rng: np.random.Generator, q: int = 5):
    """移除对目标函数贡献最大的客户（距离 + 时间窗）"""
    removed = []
    
    # 计算每个客户的"代价"（移除后的改善）
    customer_cost = {}
    
    for route_idx, route in enumerate(state.routes):
        for pos, cust_id in enumerate(route):
            # 计算移除该客户后的距离变化
            if pos == 0:
                before = state.distance(0, cust_id)
                after = 0
                if len(route) > 1:
                    after = state.distance(0, route[1])
            elif pos == len(route) - 1:
                before = state.distance(route[pos-1], cust_id) + state.distance(cust_id, 0)
                after = state.distance(route[pos-1], 0)
            else:
                before = state.distance(route[pos-1], cust_id) + state.distance(cust_id, route[pos+1])
                after = state.distance(route[pos-1], route[pos+1])
            
            # 时间窗贡献（简化：该客户的时间窗违规）
            # 实际应该计算移除前后的路线时间窗变化，这里简化处理
            tw_cost = state.customers[cust_id].tw_late - state.customers[cust_id].tw_early
            
            customer_cost[cust_id] = (before - after) + tw_cost * 0.01
    
    # 按代价排序，移除代价最高的
    sorted_customers = sorted(customer_cost.keys(), key=lambda c: customer_cost[c], reverse=True)
    to_remove = set(sorted_customers[:q])
    
    # 从路线中移除
    new_routes = []
    for route in state.routes:
        new_route = [c for c in route if c not in to_remove]
        if new_route:
            new_routes.append(new_route)
    
    new_state = VRPTWState(new_routes, state.customers, state.vehicle, state.depot)
    new_state.unassigned = set(to_remove)
    
    return new_state, list(to_remove)


def time_warp_remove(state: VRPTWState, rng: np.random.Generator, q: int = 5):
    """移除造成时间窗违规的客户（VRPTW专用）"""
    removed = []
    
    # 找出所有时间窗违规的客户
    violating_customers = []
    
    for route in state.routes:
        if not route:
            continue
        
        # 计算路线的时间窗违规详情
        time = 0.0
        prev = 0
        
        for cust_id in route:
            cust = state.customers[cust_id]
            time += state.distance(prev, cust_id)
            time = max(time, cust.tw_early)
            
            if time > cust.tw_late:
                # 记录违规客户和违规量
                violating_customers.append((cust_id, time - cust.tw_late))
            
            time += cust.service
            prev = cust_id
    
    # 按违规量排序
    violating_customers.sort(key=lambda x: x[1], reverse=True)
    
    # 优先移除违规客户
    to_remove = set()
    for cust_id, _ in violating_customers[:q]:
        to_remove.add(cust_id)
    
    # 如果违规客户不够，随机补充
    all_customers = []
    for route in state.routes:
        all_customers.extend(route)
    
    remaining = [c for c in all_customers if c not in to_remove]
    need_more = q - len(to_remove)
    if need_more > 0 and remaining:
        extra = rng.choice(remaining, size=min(need_more, len(remaining)), replace=False)
        to_remove.update(extra)
    
    # 从路线中移除
    new_routes = []
    for route in state.routes:
        new_route = [c for c in route if c not in to_remove]
        if new_route:
            new_routes.append(new_route)
    
    new_state = VRPTWState(new_routes, state.customers, state.vehicle, state.depot)
    new_state.unassigned = set(to_remove)
    
    return new_state, list(to_remove)


def shaw_remove(state: VRPTWState, rng: np.random.Generator, q: int = 5):
    """Shaw Remove：移除相似的客户（距离+时间窗+需求）"""
    removed = []
    
    # 收集所有客户
    all_customers = []
    for route in state.routes:
        all_customers.extend(route)
    
    if not all_customers:
        return state.copy(), []
    
    # 随机选一个种子客户
    seed = rng.choice(all_customers)
    seed_cust = state.customers[seed]
    
    # 计算相似度（越小越相似）
    similarities = []
    for cust_id in all_customers:
        if cust_id == seed:
            continue
        cust = state.customers[cust_id]
        
        # 距离相似度
        dist_sim = state.distance(seed, cust_id)
        
        # 时间窗相似度
        tw_sim = abs(seed_cust.tw_early - cust.tw_early) + abs(seed_cust.tw_late - cust.tw_late)
        
        # 需求相似度
        dem_sim = abs(seed_cust.demand - cust.demand)
        
        # 综合相似度
        total_sim = dist_sim + tw_sim * 0.1 + dem_sim * 5
        similarities.append((cust_id, total_sim))
    
    # 按相似度排序，移除最相似的
    similarities.sort(key=lambda x: x[1])
    to_remove = {seed}
    for cust_id, _ in similarities[:q-1]:
        to_remove.add(cust_id)
    
    # 从路线中移除
    new_routes = []
    for route in state.routes:
        new_route = [c for c in route if c not in to_remove]
        if new_route:
            new_routes.append(new_route)
    
    new_state = VRPTWState(new_routes, state.customers, state.vehicle, state.depot)
    new_state.unassigned = set(to_remove)
    
    return new_state, list(to_remove)


if __name__ == "__main__":
    from alns_vrptw_state import create_vrptw_instance
    
    customers, depot, vehicle = create_vrptw_instance()
    routes = [[1,2,3,4,5], [6,7,8,9,10], [11,12,13,14,15], [16,17,18,19,20]]
    state = VRPTWState(routes, customers, vehicle, depot)
    
    rng = np.random.default_rng(42)
    
    print("=== 测试 Destroy 算子 ===")
    print(f"初始目标: {state.objective():.2f}")
    print(f"初始时间窗违规: {sum(state.route_time_warp(r) for r in state.routes):.2f}")
    print()
    
    # Random Remove
    s1, removed1 = random_remove(state.copy(), rng, q=5)
    print(f"Random Remove: 移除{removed1}, 新目标={s1.objective():.2f}")
    
    # Worst Remove
    s2, removed2 = worst_remove(state.copy(), rng, q=5)
    print(f"Worst Remove: 移除{removed2}, 新目标={s2.objective():.2f}")
    
    # Time Warp Remove
    s3, removed3 = time_warp_remove(state.copy(), rng, q=5)
    print(f"Time Warp Remove: 移除{removed3}, 新目标={s3.objective():.2f}")
    print(f"  新时间窗违规: {sum(s3.route_time_warp(r) for r in s3.routes):.2f}")
    
    # Shaw Remove
    s4, removed4 = shaw_remove(state.copy(), rng, q=5)
    print(f"Shaw Remove: 移除{removed4}, 新目标={s4.objective():.2f}")
