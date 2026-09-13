"""ALNS VRPTW State - 带时间窗约束"""
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Customer:
    id: int
    x: float
    y: float
    demand: float
    tw_early: float   # 最早到达时间
    tw_late: float    # 最晚到达时间
    service: float    # 服务时间

@dataclass
class Vehicle:
    capacity: float
    max_time: float   # 最大行驶时间

class VRPTWState:
    """VRPTW 状态：路线列表 + 客户集合"""
    
    def __init__(self, routes: List[List[int]], customers: dict, 
                 vehicle: Vehicle, depot: Customer, unassigned: set = None):
        self.routes = [list(r) for r in routes]  # 深拷贝
        self.customers = customers
        self.vehicle = vehicle
        self.depot = depot
        self.unassigned = set(unassigned) if unassigned else set()
    
    def copy(self):
        return VRPTWState(self.routes, self.customers, self.vehicle, 
                         self.depot, self.unassigned.copy())
    
    def distance(self, i: int, j: int) -> float:
        """计算两点欧氏距离"""
        a = self.depot if i == 0 else self.customers[i]
        b = self.depot if j == 0 else self.customers[j]
        return ((a.x - b.x)**2 + (a.y - b.y)**2) ** 0.5
    
    def route_distance(self, route: List[int]) -> float:
        """单条路线总距离"""
        if not route:
            return 0.0
        dist = self.distance(0, route[0])
        for i in range(len(route) - 1):
            dist += self.distance(route[i], route[i+1])
        dist += self.distance(route[-1], 0)
        return dist
    
    def route_time_warp(self, route: List[int]) -> float:
        """计算单条路线的时间窗违规量"""
        if not route:
            return 0.0
        
        time = 0.0
        tw_violation = 0.0
        prev = 0  # depot
        
        for cust_id in route:
            cust = self.customers[cust_id]
            # 行驶到客户
            time += self.distance(prev, cust_id)
            # 等待窗口开放
            time = max(time, cust.tw_early)
            # 检查是否迟到
            if time > cust.tw_late:
                tw_violation += time - cust.tw_late
            # 服务时间
            time += cust.service
            prev = cust_id
        
        # 返回车场
        time += self.distance(prev, 0)
        
        return tw_violation
    
    def route_demand(self, route: List[int]) -> float:
        """单条路线总需求"""
        return sum(self.customers[c].demand for c in route)
    
    def objective(self) -> float:
        """目标函数：距离 + 容量惩罚 + 时间窗惩罚"""
        total_dist = sum(self.route_distance(r) for r in self.routes)
        
        # 容量惩罚
        cap_penalty = 0.0
        for r in self.routes:
            excess = max(0, self.route_demand(r) - self.vehicle.capacity)
            cap_penalty += excess * 1000
        
        # 时间窗惩罚
        tw_penalty = 0.0
        for r in self.routes:
            tw_penalty += self.route_time_warp(r) * 1000
        
        return total_dist + cap_penalty + tw_penalty
    
    def is_feasible(self) -> bool:
        """检查是否完全可行"""
        for r in self.routes:
            if self.route_demand(r) > self.vehicle.capacity:
                return False
            if self.route_time_warp(r) > 0:
                return False
        return len(self.unassigned) == 0


def create_vrptw_instance(n=20, seed=42):
    """创建 VRPTW 测试实例（与 PyVRP 相同）"""
    rng = np.random.RandomState(seed)
    
    customers = {}
    for i in range(1, n+1):
        customers[i] = Customer(
            id=i,
            x=rng.uniform(0, 100),
            y=rng.uniform(0, 100),
            demand=rng.uniform(1, 5),
            tw_early=rng.uniform(0, 200),
            tw_late=rng.uniform(400, 800),
            service=rng.uniform(5, 15)
        )
    
    depot = Customer(id=0, x=50, y=50, demand=0, tw_early=0, tw_late=9999, service=0)
    vehicle = Vehicle(capacity=20, max_time=9999)
    
    return customers, depot, vehicle


if __name__ == "__main__":
    # 测试
    customers, depot, vehicle = create_vrptw_instance()
    
    # 简单路线测试
    routes = [[1,2,3,4,5], [6,7,8,9,10], [11,12,13,14,15], [16,17,18,19,20]]
    state = VRPTWState(routes, customers, vehicle, depot)
    
    print(f"总距离: {sum(state.route_distance(r) for r in state.routes):.2f}")
    print(f"时间窗违规: {sum(state.route_time_warp(r) for r in state.routes):.2f}")
    print(f"目标函数: {state.objective():.2f}")
    print(f"可行?: {state.is_feasible()}")
