from qubots.base_problem import BaseProblem
import sys
import os

def read_integers(filename):

    # Resolve relative path with respect to this module’s directory.
    if not os.path.isabs(filename):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(base_dir, filename)

    with open(filename) as f:
        return [int(elem) for elem in f.read().split()]

class MssInstance:
    def __init__(self, filename):
        file_it = iter(read_integers(filename))
        self.nb_actors = next(file_it)
        self.nb_scenes = next(file_it)
        self.nb_locations = next(file_it)
        self.nb_precedences = next(file_it)
        self.actor_cost = [next(file_it) for _ in range(self.nb_actors)]
        self.location_cost = [next(file_it) for _ in range(self.nb_locations)]
        self.scene_duration = [next(file_it) for _ in range(self.nb_scenes)]
        self.scene_location = [next(file_it) for _ in range(self.nb_scenes)]
        # For each actor, for each scene: presence (0/1)
        self.is_actor_in_scene = [
            [next(file_it) for _ in range(self.nb_scenes)]
            for _ in range(self.nb_actors)
        ]
        # Precedence pairs: each is two integers (scene indices)
        self.precedences = [
            [next(file_it) for _ in range(2)]
            for _ in range(self.nb_precedences)
        ]
        self.actor_nb_worked_days = self._compute_nb_worked_days()

    def _compute_nb_worked_days(self):
        actor_nb_worked_days = [0] * self.nb_actors
        for a in range(self.nb_actors):
            for s in range(self.nb_scenes):
                if self.is_actor_in_scene[a][s]:
                    actor_nb_worked_days[a] += self.scene_duration[s]
        return actor_nb_worked_days

class CostFunction:
    def __init__(self, data):
        self.data = data

    def compute_cost(self, shoot_order):
        if len(shoot_order) < self.data.nb_scenes:
            return sys.maxsize
        location_cost = self._compute_location_cost(shoot_order)
        actor_cost = self._compute_actor_cost(shoot_order)
        return location_cost + actor_cost

    def _compute_location_cost(self, shoot_order):
        nb_location_visits = [0] * self.data.nb_locations
        previous_location = -1
        for i in range(self.data.nb_scenes):
            current_location = self.data.scene_location[shoot_order[i]]
            if previous_location != current_location:
                nb_location_visits[current_location] += 1
                previous_location = current_location
        # Only cost extra visits beyond the first one per location.
        loc_cost = sum(cost * (visits - 1)
                       for cost, visits in zip(self.data.location_cost, nb_location_visits))
        return loc_cost

    def _compute_actor_cost(self, shoot_order):
        actor_first_day = [0] * self.data.nb_actors
        actor_last_day = [0] * self.data.nb_actors
        for a in range(self.data.nb_actors):
            has_started = False
            start_day = 0
            for i in range(self.data.nb_scenes):
                current_scene = shoot_order[i]
                end_day = start_day + self.data.scene_duration[current_scene] - 1
                if self.data.is_actor_in_scene[a][current_scene]:
                    actor_last_day[a] = end_day
                    if not has_started:
                        has_started = True
                        actor_first_day[a] = start_day
                start_day = end_day + 1
        extra_cost = 0
        for a in range(self.data.nb_actors):
            nb_paid_days = actor_last_day[a] - actor_first_day[a] + 1
            extra_cost += (nb_paid_days - self.data.actor_nb_worked_days[a]) * self.data.actor_cost[a]
        return extra_cost

class MovieShootSchedulingProblem(BaseProblem):
    """
    Movie Shoot Scheduling Problem for Qubots.
    
    Given a set of scenes (with fixed durations and associated locations) and a set of actors (with daily costs),
    along with precedence constraints between scenes, the goal is to find a shooting order that minimizes the sum of:
      - A location cost: each time a new location is visited (after the first), its cost is incurred.
      - An actor cost: actors are paid for all days between their first and last scene; the extra days (beyond the actual scene durations) are penalized.
    """
    
    def __init__(self, instance_file: str, **kwargs):
        self.data = MssInstance(instance_file)
    
    def evaluate_solution(self, solution) -> int:
        """
        Expects:
          solution: a list (of length equal to nb_scenes) representing the shoot order (a permutation of scene indices, 0-indexed).
        Returns:
          The total cost computed by the cost function.
        """
        if not isinstance(solution, list) or len(solution) != self.data.nb_scenes:
            return sys.maxsize
        cost_function = CostFunction(self.data)
        return cost_function.compute_cost(solution)
    
    def random_solution(self):
        """
        Generates a random permutation of scene indices.
        """
        order = list(range(self.data.nb_scenes))
        import random
        random.shuffle(order)
        return order
