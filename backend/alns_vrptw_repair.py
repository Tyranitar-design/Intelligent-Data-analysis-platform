"""ALNS VRPTW Repair Operators - 带时间窗感知的修复算子"""
import numpy as np
from alns_vrptw_state import VRPTWState

# ============ Repair 算子 ============

def greedy_insert(state: VRPTWState, removed: list, rng: np.random.Generator):
    """贪心插入：每次选择插入代价最小的位置"""
    routes = [list(r) for r in state.routes]
    unassigned = list(removed)
    
    while unassigned:
        best_cost = float('inf')
        best_cust = None
        best_route_idx = None
        best_pos = None
        
        for cust_id in unassigned:
            cust = state.customers[cust_id]
            
            for route_idx, route in enumerate(routes):
                # 检查容量
                route_demand = sum(state.customers[c].demand for c in route)
                if route_demand + cust.demand > state.vehicle.capacity:
                    continue
                
                # 尝试每个插入位置
                for pos in range(len(route) + 1):
                    # 计算插入代价（距离增加）
                    if pos == 0:
                        if not route:
                            cost = state.distance(0, cust_id) + state.distance(cust_id, 0)
                        else:
                            cost = (state.distance(0, cust_id) + 
                                   state.distance(cust_id, route[0]) - 
                                   state.distance(0, route[0]))
                    elif pos == len(route):
                        cost = (state.distance(route[-1], cust_id) + 
                               state.distance(cust_id, 0) - 
                               state.distance(route[-1], 0))
                    else:
                        cost = (state.distance(route[pos-1], cust_id) + 
                               state.distance(cust_id, route[pos]) - 
                               state.distance(route[pos-1], route[pos]))
                    
                    # 时间窗惩罚（简化：检查是否会造成严重违规）
                    new_route = route[:pos] + [cust_id] + route[pos:]
                    tw_penalty = state.route_time_warp(new_route) * 1000
                    
                    total_cost = cost + tw_penalty
                    
                    if total_cost < best_cost:
                        best_cost = total_cost
                        best_cust = cust_id
                        best_route_idx = route_idx
                        best_pos = pos
            
            # 也尝试新开一条路线
            cost = state.distance(0, cust_id) + state.distance(cust_id, 0)
            new_route = [cust_id]
            tw_penalty = state.route_time_warp(new_route) * 1000
            total_cost = cost + tw_penalty
            
            if total_cost < best_cost:
                best_cost = total_cost
                best_cust = cust_id
                best_route_idx = len(routes)  # 新路线
                best_pos = 0
        
        if best_cust is None:
            # 无法插入，强制插入到第一条路线
            best_cust = unassigned[0]
            best_route_idx = 0 if routes else len(routes)
            best_pos = len(routes[0]) if routes else 0
        
        # 执行插入
        if best_route_idx == len(routes):
            routes.append([best_cust])
        else:
            routes[best_route_idx].insert(best_pos, best_cust)
        
        unassigned.remove(best_cust)
    
    return VRPTWState(routes, state.customers, state.vehicle, state.depot)


def regret2_insert(state: VRPTWState, removed: list, rng: np.random.Generator):
    """Regret-2 插入：考虑次优选择，避免客户无处可插"""
    routes = [list(r) for r in state.routes]
    unassigned = list(removed)
    
    while unassigned:
        best_regret = -1
        best_cust = None
        best_route_idx = None
        best_pos = None
        
        for cust_id in unassigned:
            cust = state.customers[cust_id]
            
            # 收集所有可能的插入位置及其代价
            insertions = []
            
            for route_idx, route in enumerate(routes):
                route_demand = sum(state.customers[c].demand for c in route)
                if route_demand + cust.demand > state.vehicle.capacity:
                    continue
                
                for pos in range(len(route) + 1):
                    if pos == 0:
                        if not route:
                            cost = state.distance(0, cust_id) + state.distance(cust_id, 0)
                        else:
                            cost = (state.distance(0, cust_id) + 
                                   state.distance(cust_id, route[0]) - 
                                   state.distance(0, route[0]))
                    elif pos == len(route):
                        cost = (state.distance(route[-1], cust_id) + 
                               state.distance(cust_id, 0) - 
                               state.distance(route[-1], 0))
                    else:
                        cost = (state.distance(route[pos-1], cust_id) + 
                               state.distance(cust_id, route[pos]) - 
                               state.distance(route[pos-1], route[pos]))
                    
                    new_route = route[:pos] + [cust_id] + route[pos:]
                    tw_penalty = state.route_time_warp(new_route) * 1000
                    total_cost = cost + tw_penalty
                    
                    insertions.append((total_cost, route_idx, pos))
            
            # 新开路线
            cost = state.distance(0, cust_id) + state.distance(cust_id, 0)
            new_route = [cust_id]
            tw_penalty = state.route_time_warp(new_route) * 1000
            insertions.append((cost + tw_penalty, len(routes), 0))
            
            if len(insertions) < 2:
                continue
            
            # 排序，取最优和次优
            insertions.sort(key=lambda x: x[0])
            regret = insertions[1][0] - insertions[0][0]  # 次优 - 最优
            
            if regret > best_regret:
                best_regret = regret
                best_cust = cust_id
                best_route_idx = insertions[0][1]
                best_pos = insertions[0][2]
        
        if best_cust is None:
            best_cust = unassigned[0]
            best_route_idx = 0 if routes else len(routes)
            best_pos = len(routes[0]) if routes else 0
        
        # 执行插入
        if best_route_idx == len(routes):
            routes.append([best_cust])
        else:
            routes[best_route_idx].insert(best_pos, best_cust)
        
        unassigned.remove(best_cust)
    
    return VRPTWState(routes, state.customers, state.vehicle, state.depot)


def random_insert(state: VRPTWState, removed: list, rng: np.random.Generator):
    """随机插入：增加多样性"""
    routes = [list(r) for r in state.routes]
    unassigned = list(removed)
    rng.shuffle(unassigned)
    
    for cust_id in unassigned:
        # 随机选择路线和位置
        route_idx = rng.integers(0, len(routes) + 1)
        
        if route_idx == len(routes):
            routes.append([cust_id])
        else:
            pos = rng.integers(0, len(routes[route_idx]) + 1)
            routes[route_idx].insert(pos, cust_id)
    
    return VRPTWState(routes, state.customers, state.vehicle, state.depot)


if __name__ == "__main__":
    from alns_vrptw_state import create_vrptw_instance
    from alns_vrptw_destroy import random_remove
    
    customers, depot, vehicle = create_vrptw_instance()
    routes = [[1,2,3,4,5], [6,7,8,9,10], [11,12,13,14,15], [16,17,18,19,20]]
    state = VRPTWState(routes, customers, vehicle, depot)
    
    rng = np.random.default_rng(42)
    
    # 先用 destroy 移除一些客户
    destroyed, removed = random_remove(state.copy(), rng, q=5)
    print(f"=== 测试 Repair 算子 ===")
    print(f"移除客户: {removed}")
    print(f"破坏后目标: {destroyed.objective():.2f}")
    print()
    
    # Greedy Insert
    s1 = greedy_insert(destroyed, removed, rng)
    print(f"Greedy Insert: 目标={s1.objective():.2f}, 可行={s1.is_feasible()}")
    
    # Regret-2 Insert
    s2 = regret2_insert(destroyed, removed, rng)
    print(f"Regret-2 Insert: 目标={s2.objective():.2f}, 可行={s2.is_feasible()}")
    
    # Random Insert
    s3 = random_insert(destroyed, removed, rng)
    print(f"Random Insert: 目标={s3.objective():.2f}, 可行={s3.is_feasible()}")
