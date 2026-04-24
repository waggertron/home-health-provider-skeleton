"""Google OR-Tools VRP solver.

Consumes a Problem built by scheduling.adapter and returns per-vehicle
visit sequences that honor time windows, service times, and credential-
based skill constraints. Each clinician is one vehicle with a depot at
their home coords. Service time defaults to 30 minutes per visit.

Unassignable visits (no credentialed clinician available, or no feasible
time) are returned in `unassigned_visit_ids`; the solver uses a large
drop penalty so it prefers assigning everyone when possible.
"""

from __future__ import annotations

from dataclasses import dataclass

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from scheduling.adapter import Problem

_DAY_SECONDS = 24 * 3600
_DROP_PENALTY = 10_000_000


@dataclass(frozen=True)
class VehicleRoute:
    clinician_id: int
    visit_ids: list[int]
    travel_seconds: int


@dataclass(frozen=True)
class Solution:
    routes: list[VehicleRoute]
    total_travel_s: int
    unassigned_visit_ids: list[int]


def solve(problem: Problem, time_budget_s: int = 10) -> Solution:
    num_clinicians = len(problem.clinicians)
    num_visits = len(problem.visits)
    if num_visits == 0 or num_clinicians == 0:
        return Solution(
            routes=[
                VehicleRoute(clinician_id=c.id, visit_ids=[], travel_seconds=0)
                for c in problem.clinicians
            ],
            total_travel_s=0,
            unassigned_visit_ids=[v.id for v in problem.visits],
        )

    num_nodes = num_clinicians + num_visits
    starts = list(range(num_clinicians))
    ends = list(range(num_clinicians))
    manager = pywrapcp.RoutingIndexManager(num_nodes, num_clinicians, starts, ends)
    routing = pywrapcp.RoutingModel(manager)

    def transit_cb(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        travel = problem.distance_matrix[from_node][to_node]
        service = 0
        if from_node >= num_clinicians:
            service = problem.visits[from_node - num_clinicians].service_time_s
        return travel + service

    transit_idx = routing.RegisterTransitCallback(transit_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    routing.AddDimension(
        transit_idx,
        _DAY_SECONDS,  # slack — waiting time allowed at any node
        _DAY_SECONDS,  # max per-vehicle cumulative time
        False,  # don't force start cumul to zero (allow late starts)
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    for v_idx, visit in enumerate(problem.visits):
        node = num_clinicians + v_idx
        index = manager.NodeToIndex(node)
        time_dim.CumulVar(index).SetRange(visit.window_start_s, visit.window_end_s)
        routing.AddDisjunction([index], _DROP_PENALTY)

    for v_idx, allowed in enumerate(problem.allowed_vehicles):
        node = num_clinicians + v_idx
        index = manager.NodeToIndex(node)
        # Restrict vehicle assignment; -1 permits the visit to be dropped.
        routing.VehicleVar(index).SetValues([-1, *allowed])

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.seconds = max(1, time_budget_s)

    assignment = routing.SolveWithParameters(params)
    if assignment is None:
        return Solution(
            routes=[
                VehicleRoute(clinician_id=c.id, visit_ids=[], travel_seconds=0)
                for c in problem.clinicians
            ],
            total_travel_s=0,
            unassigned_visit_ids=[v.id for v in problem.visits],
        )

    routes: list[VehicleRoute] = []
    assigned: set[int] = set()
    total_travel = 0
    for vehicle in range(num_clinicians):
        index = routing.Start(vehicle)
        visit_ids: list[int] = []
        route_travel = 0
        prev_node = manager.IndexToNode(index)
        index = assignment.Value(routing.NextVar(index))
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route_travel += problem.distance_matrix[prev_node][node]
            v_idx = node - num_clinicians
            visit_id = problem.visits[v_idx].id
            visit_ids.append(visit_id)
            assigned.add(visit_id)
            prev_node = node
            index = assignment.Value(routing.NextVar(index))
        end_node = manager.IndexToNode(index)
        route_travel += problem.distance_matrix[prev_node][end_node]
        total_travel += route_travel
        routes.append(
            VehicleRoute(
                clinician_id=problem.clinicians[vehicle].id,
                visit_ids=visit_ids,
                travel_seconds=route_travel,
            )
        )

    unassigned = [v.id for v in problem.visits if v.id not in assigned]
    return Solution(routes=routes, total_travel_s=total_travel, unassigned_visit_ids=unassigned)
