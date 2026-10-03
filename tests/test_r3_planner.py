import unittest
from sailboat_routing.planner import StaticMap, CircleObstacle, PlannerInput, PlannerDecision, NoRouteError
from sailboat_routing.r1_planner import RouteWaypointPlanner, R1Config
from sailboat_routing.r2_planner import RelayPlanner, RelayConfig
from sailboat_routing.r3_planner import RiskManagedPlanner, RiskConfig

class R3Tests(unittest.TestCase):

    def test_disabled_intervention_matches_original_planners(self):
        chart = StaticMap((-1500, 2500, -1500, 1500), (CircleObstacle((500, 0), 55, 70),), 25)
        for kind in ['r1', 'relay']:
            old = RouteWaypointPlanner(chart) if kind == 'r1' else RelayPlanner(chart, RelayConfig(handoff=100, trigger_clearance=80))
            new = RiskManagedPlanner(chart, RiskConfig(base=kind, threshold=0))
            current = None
            for t, p in [(0, (0, 0)), (10, (15, -2)), (30, (65, -30)), (50, (110, -90))]:
                v = PlannerInput(p, 0.3, current, ((0, 0), (1500, 0)), t, None)
                x, y = (old.plan(v), new.plan(v))
                self.assertEqual(x, y)
                current = x.target_xy

    def test_closing_gate_uses_past_positions_and_does_not_trigger_on_receding(self):
        chart = StaticMap((-1000, 2000, -1000, 1000), (CircleObstacle((300, 0), 55, 70),), 25)
        for closing, start, step, expected in [(True, 130, -2, False), (True, 100, 3, True), (False, 130, -2, True)]:
            obj = RiskManagedPlanner(chart, RiskConfig(threshold=80, closing_gate=closing))

            class Probe:
                config = R1Config()

                def plan(self, v):
                    return PlannerDecision(v.current_goal_xy, (), 'probe', False)
            obj.base = Probe()
            for t in range(11):
                v = PlannerInput((start + step * t, 0), 0, (500, 200), ((0, 0), (1000, 0)), t, None)
                obj.plan(v)
                obj.plan(v)
            self.assertEqual(len(obj.motion), 11)
            self.assertEqual(obj.log[-1]['risk_detected'], expected)
            if closing and expected:
                self.assertTrue(any((x['attempt'] for x in obj.log if x['time'] == 10)))
                self.assertFalse(obj.log[-1]['attempt'])

    def test_risk_bypasses_holding_temporarily_and_cooldown_is_physical_time(self):
        chart = StaticMap((-1000, 2000, -1000, 1000), (CircleObstacle((300, 0), 55, 70),), 25)
        obj = RiskManagedPlanner(chart, RiskConfig(threshold=80, cooldown=20))

        class Probe:
            config = R1Config()
            calls = []

            def plan(self, v):
                self.calls.append(self.config)
                return PlannerDecision(v.current_goal_xy, (), 'probe', False)
        obj.base = Probe()
        original = obj.base.config
        for t in [0, 1, 19, 20]:
            obj.plan(PlannerInput((130, 0), 0, (500, 200), ((0, 0), (1000, 0)), t, None))
        self.assertEqual([x.improvement for x in obj.base.calls], [0, 15, 15, 0])
        self.assertEqual([x.hold for x in obj.base.calls], [0, 20, 20, 0])
        self.assertEqual(obj.base.config, original)

    def test_open_water_has_no_finite_risk_and_final_goal_is_retained(self):
        obj = RiskManagedPlanner(StaticMap((-1000, 2000, -1000, 1000)), RiskConfig(threshold=80))
        v = PlannerInput((986, 0), 0, (1000, 0), ((0, 0), (1000, 0)), 100, None)
        self.assertEqual(obj.plan(v).target_xy, (1000, 0))
        self.assertFalse(obj.log[-1]['attempt'])

    def test_history_window_lags_instantaneous_reversal(self):
        chart = StaticMap((-1000, 2000, -1000, 1000), (CircleObstacle((300, 0), 55, 70),), 25)
        for positions, expected in [([100 + 2 * t for t in range(10)] + [116], True), ([140 - 2 * t for t in range(10)] + [124], False)]:
            obj = RiskManagedPlanner(chart, RiskConfig(threshold=80, closing_gate=True))

            class Probe:
                config = R1Config()

                def plan(self, v):
                    return PlannerDecision(v.current_goal_xy, (), 'probe', False)
            obj.base = Probe()
            for t, x in enumerate(positions):
                obj.plan(PlannerInput((x, 0), 0, (500, 200), ((0, 0), (1000, 0)), t, None))
                if t < 10:
                    self.assertFalse(obj.log[-1]['risk_detected'])
            self.assertEqual(obj.log[-1]['risk_detected'], expected)

    def test_non_nearest_approaching_obstacle_can_trigger(self):
        chart = StaticMap((-1000, 2000, -1000, 1000), (CircleObstacle((0, 0), 55, 70), CircleObstacle((350, 0), 55, 70)), 25)
        obj = RiskManagedPlanner(chart, RiskConfig(threshold=80, closing_gate=True))

        class Probe:
            config = R1Config()

            def plan(self, v):
                return PlannerDecision(v.current_goal_xy, (), 'probe', False)
        obj.base = Probe()
        for t in range(11):
            obj.plan(PlannerInput((150 + 2 * t, 0), 0, (500, 200), ((0, 0), (1000, 0)), t, None))
        self.assertEqual(obj.log[-1]['nearest_obstacle'], 0)
        self.assertLess(obj.log[-1]['closing_speed'], 0)
        self.assertEqual([o['index'] for o in obj.log[-1]['risk_obstacles']], [1])
        self.assertTrue(obj.log[-1]['attempt'])

    def test_short_risk_relay_changes_only_attempt_lookahead(self):
        chart = StaticMap((-1000, 2000, -1000, 1000), (CircleObstacle((-200, 0), 55, 70),), 25)
        v = PlannerInput((-30, 0), 0, (400, 0), ((-30, 0), (1000, 0)), 0, None)
        obj = RiskManagedPlanner(chart, RiskConfig(base='relay', threshold=60, risk_lookahead=200))
        result = obj.plan(v)
        self.assertEqual(result.target_xy, (170, 0))
        self.assertEqual(v.current_goal_xy, (400, 0))
        self.assertEqual(obj.base.config.lookahead, 500)
        self.assertTrue(obj.log[-1]['proposed_change'])
        self.assertEqual(obj.plan(PlannerInput((-27, 0), 0, result.target_xy, v.route, 1, None)).target_xy, result.target_xy)

    def test_failed_plan_logs_attempt_and_restores_config(self):
        chart = StaticMap((-1000, 2000, -1000, 1000), (CircleObstacle((300, 0), 55, 70),), 25)
        obj = RiskManagedPlanner(chart, RiskConfig(threshold=80))

        class Probe:
            config = R1Config()

            def plan(self, v):
                raise NoRouteError('test failure')
        obj.base = Probe()
        before = obj.base.config
        with self.assertRaises(NoRouteError):
            obj.plan(PlannerInput((130, 0), 0, (500, 200), ((0, 0), (1000, 0)), 0, None))
        self.assertEqual(obj.base.config, before)
        self.assertEqual(obj.log[-1]['error'], 'NoRouteError')
        self.assertTrue(obj.log[-1]['attempt'])
        self.assertFalse(obj.log[-1]['proposed_change'])
