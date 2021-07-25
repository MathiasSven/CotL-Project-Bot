import random
from typing import Tuple, Dict
from .formulas import VictoryType, Military, MilitaryType, MAProbabilities
from unittest import TestCase
from hypothesis import Verbosity, given, settings, strategies
import numba as nb
import numpy as np
from datetime import datetime


class TestMAProbabilities(TestCase):
    @staticmethod
    @nb.njit((nb.f8, nb.f8, nb.u8))
    def _attack_aggregator(mili_value__a: float, mili_value__d: float, perseverance: int) -> Tuple:
        victory_types: np.ndarray = np.zeros(4, dtype=np.uint64)
        casualties: np.ndarray = np.zeros((2, 4, 3), dtype=np.float64)
        casualties[:, :, 0] = np.inf

        for _ in nb.prange(perseverance):
            roll_wins: int = 0
            attackers_casualties = 0.0
            defenders_casualties = 0.0
            for roll in range(3):
                attackers_roll = mili_value__a * random.uniform(0.4, 1)
                defenders_roll = mili_value__d * random.uniform(0.4, 1)
                if attackers_roll > defenders_roll:
                    roll_wins += 1
                attackers_casualties += defenders_roll * 0.01
                defenders_casualties += attackers_roll * 0.018337

            victory_types[roll_wins] += 1
            casualties[0, roll_wins, 2] += attackers_casualties
            casualties[1, roll_wins, 2] += defenders_casualties

            if attackers_casualties < casualties[0, roll_wins, 0]:
                casualties[0, roll_wins, 0] = attackers_casualties
            if attackers_casualties > casualties[0, roll_wins, 1]:
                casualties[0, roll_wins, 1] = attackers_casualties
            if defenders_casualties < casualties[1, roll_wins, 0]:
                casualties[1, roll_wins, 0] = defenders_casualties
            if defenders_casualties > casualties[1, roll_wins, 1]:
                casualties[1, roll_wins, 1] = defenders_casualties

        return victory_types, casualties

    @classmethod
    def attack_aggregator(cls, mili_value__a: float, mili_value__d: float, perseverance: int) -> Dict:
        victory_types, casualties = cls._attack_aggregator(mili_value__a, mili_value__d, perseverance)
        return {
            'victory_types': {VictoryType(x): {'total': y, 'expected': f"{(y / perseverance):.2%}"} for x, y in enumerate(victory_types)},
            'casualties': {x: {'expected': sum(casualties[y, :, 2]) / perseverance,
                               'given': {VictoryType(i): {'min': casualties[y, i, 0], 'max': casualties[y, i, 1],
                                                          'total': casualties[y, i, 2], 'expected': casualties[y, i, 2] / (victory_types[i] if victory_types[i] else 1)}
                                         for i in VictoryType}} for y, x in enumerate(('attacker', 'defender'))}
        }

    def test_airstrike(self):
        aircraft__a = 1000
        aircraft__d = 1500
        perseverance = 10000000
        mili__a = Military(aircraft=aircraft__a)
        mili__d = Military(aircraft=aircraft__d)

        tmp = self.attack_aggregator(mili__a.values[MilitaryType.AIRFORCE],
                                     mili__d.values[MilitaryType.AIRFORCE],
                                     perseverance)
        from pprint import pprint
        pprint(tmp)

        # expected_results = MAProbabilities(mili__a=mili__a, mili__d=mili__d).victory_types(mili__a.values[MilitaryType.AIRFORCE],
        #                                                                                    mili__d.values[MilitaryType.AIRFORCE])

        # for i in VictoryType:
        #     print(i, f"Expected: {(expected_results[i]):.2%}", f"Aggregated: {(aggregated_results[i]):.2%}", f"Diff: {(expected_results[i] - aggregated_results[i]):.2%}")
        # self.assertAlmostEqual(expected_results[i], aggregated_results[i], places=2)

# start = datetime.now()
# t = TestMAProbabilities()._attack_aggregator(3000, 4500, 10 ** 8)
# end = datetime.now()
# print(end - start)
