from state_providers.base_provider import BaseStateProvider


class YoloStateProvider(BaseStateProvider):
    """Placeholder for real camera/YOLO-based vehicle detection.

    Not implemented yet -- deliberately returns no signal rather than a
    simulated stand-in, so it can't be mistaken for a working perception
    source. `docs/ground_truth_final_state_and_gaps.md` documents the ground-truth
    ceiling metrics (from `optimal_ground_truth_strategy.py`) that real
    detection should be measured against once it exists. The strategy that
    will consume this provider's output is not written yet either -- it
    starts from a clean slate once real detection exists, rather than
    reusing any of this project's earlier adaptive-controller code. The
    eventual implementation only needs to fill in get_state()/get_rich_state()
    with real inference output; the contract (a dict of direction -> signal)
    is all a future strategy needs from any provider.
    """

    def __init__(self, engine):
        self.engine = engine

    def get_state(self):
        return {"right": 0, "down": 0, "left": 0, "up": 0}

    def get_rich_state(self):
        return {
            direction: {
                "queue_count": 0,
                "visible_count": 0,
                "score": 0,
                "queue_level": "unknown",
                "is_saturated": False,
                "occupancy_ratio": None,
                "color": (230, 230, 230),
            }
            for direction in ["right", "down", "left", "up"]
        }
