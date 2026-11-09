"""Aggregate evaluated outcomes without treating unknowns as failures or successes."""

from collections import Counter


class GraspEvaluator:
    def evaluate(self, candidates):
        counts = Counter()
        for candidate in candidates:
            counts["total"] += 1
            if candidate.success is None:
                counts["unevaluated"] += 1
            else:
                counts["evaluated"] += 1
                counts["successful"] += int(candidate.success)
        evaluated = counts["evaluated"]
        return {"total": counts["total"], "evaluated": evaluated, "unevaluated": counts["unevaluated"],
                "successful": counts["successful"],
                "success_rate": counts["successful"] / evaluated if evaluated else None}
