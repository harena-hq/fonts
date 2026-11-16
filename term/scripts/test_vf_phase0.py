#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

import unittest

from vf_phase0 import problem_counts


class ProblemCountsTest(unittest.TestCase):
    def test_counts_problem_types_across_glyphs(self) -> None:
        problems = {
            "A": [{"type": "node_count"}, {"type": "kink"}],
            "B": [{"type": "node_count"}],
        }
        self.assertEqual(problem_counts(problems), {
            "kink": 1,
            "node_count": 2,
        })

    def test_empty_problem_set(self) -> None:
        self.assertEqual(problem_counts({}), {})


if __name__ == "__main__":
    unittest.main()
