class BaseStateProvider:
    def __init__(self, engine):
        self.engine = engine

    def get_state(self):
        raise NotImplementedError
