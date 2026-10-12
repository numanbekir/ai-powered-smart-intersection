class DecisionLogger:
    def __init__(self):
        self.entries = []

    def add(self, entry):
        self.entries.append(entry)

    def list_recent(self, max_lines=12):
        return self.entries[-max_lines:]