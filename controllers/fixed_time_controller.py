import random

from simulation.signal import TrafficSignal


class FixedTimeSignalController:
    ACTIVE_LANES = [1, 2]

    def __init__(self, engine):
        self.engine = engine
        self.signals = []

        initial_green = engine.fixed_config.get("initial_green", "right")

        if initial_green == "random":
            initial_green = random.choice(["right", "down", "left", "up"])

        self.currentGreen = engine.directionToNumber[initial_green]
        self.nextGreen = (self.currentGreen + 1) % engine.noOfSignals
        self.currentYellow = 0

        self.initialize()

    def initialize(self):
        self.signals.clear()

        green_time = self.engine.fixed_config["green_time"]
        yellow_time = self.engine.fixed_config["yellow_time"]
        red_time = self.engine.fixed_config["red_time"]

        for i in range(self.engine.noOfSignals):
            if i == self.currentGreen:
                self.signals.append(TrafficSignal(0, yellow_time, green_time))
            else:
                self.signals.append(TrafficSignal(red_time, yellow_time, green_time))

        self.engine.begin_phase_tracking(
            self.engine.directionNumbers[self.currentGreen], green_time
        )

    def update_values(self):
        for i in range(self.engine.noOfSignals):
            if i == self.currentGreen:
                if self.currentYellow == 0:
                    self.signals[i].green -= 1
                else:
                    self.signals[i].yellow -= 1
            else:
                self.signals[i].red -= 1

    def hold_current_direction_on_yellow(self):
        current_direction = self.engine.directionNumbers[self.currentGreen]

        for lane in self.ACTIVE_LANES:
            for vehicle in self.engine.vehicles[current_direction][lane]:
                vehicle.stop = self.engine.defaultStop[current_direction]

    def run(self):
        while self.engine.simulationRunning:
            while self.signals[self.currentGreen].green > 0 and self.engine.simulationRunning:
                self.engine.wait_if_paused()
                self.update_values()
                self.engine.scaled_sleep(1)

            if not self.engine.simulationRunning:
                break

            self.engine.record_completed_phase(reason="Fixed-time cycle.")

            self.currentYellow = 1
            self.hold_current_direction_on_yellow()

            while self.signals[self.currentGreen].yellow > 0 and self.engine.simulationRunning:
                self.engine.wait_if_paused()
                self.update_values()
                self.engine.scaled_sleep(1)

            self.currentYellow = 0

            green_time = self.engine.fixed_config["green_time"]
            yellow_time = self.engine.fixed_config["yellow_time"]
            red_time = self.engine.fixed_config["red_time"]

            self.signals[self.currentGreen].green = green_time
            self.signals[self.currentGreen].yellow = yellow_time
            self.signals[self.currentGreen].red = red_time

            self.currentGreen = self.nextGreen
            self.nextGreen = (self.currentGreen + 1) % self.engine.noOfSignals

            self.signals[self.nextGreen].red = (
                self.signals[self.currentGreen].yellow
                + self.signals[self.currentGreen].green
            )

            self.engine.begin_phase_tracking(
                self.engine.directionNumbers[self.currentGreen], green_time
            )

    def is_green(self, direction_number):
        return self.currentGreen == direction_number and self.currentYellow == 0