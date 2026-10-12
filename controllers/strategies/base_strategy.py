class BaseAdaptiveStrategy:
    strategy_key = "base"

    def choose_next_phase(self, state, params, engine):
        """Returns (direction, green_time, reason, decision_meta).

        decision_meta is a dict of optional flags the generic controller
        uses for cross-strategy bookkeeping (metrics, logging) without
        needing to know strategy-specific decision logic. Currently
        recognized key: "emergency_priority" (bool) -- whether this phase
        was selected because of emergency-vehicle priority rather than
        normal demand-based selection.
        """
        raise NotImplementedError
