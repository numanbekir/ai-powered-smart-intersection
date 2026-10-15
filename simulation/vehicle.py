import math
import pygame


class Vehicle(pygame.sprite.Sprite):
    ACTIVE_LANES = [1, 2]

    EMERGENCY_TYPES = ["ambulance", "police", "firetruck"]

    ROTATION_MAP = {
        "right": 0,
        "down": -90,
        "left": 180,
        "up": 90,
    }

    def __init__(
        self,
        engine,
        lane,
        vehicleClass,
        direction_number,
        direction,
        turn_intent,
        controller,
        is_emergency=False,
        emergency_type=None,
    ):
        pygame.sprite.Sprite.__init__(self)

        if lane not in self.ACTIVE_LANES:
            raise ValueError(f"Invalid lane: {lane}. Active lanes are {self.ACTIVE_LANES}")

        self.engine = engine
        self.controller = controller
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.base_speed = engine.speeds[vehicleClass]
        self.direction_number = direction_number
        self.direction = direction
        self.turnIntent = turn_intent
        self.willTurn = 1 if turn_intent != "straight" else 0

        self.isEmergency = bool(is_emergency or vehicleClass in self.EMERGENCY_TYPES)
        self.emergencyType = emergency_type if self.isEmergency else None
        if self.isEmergency and self.emergencyType is None:
            self.emergencyType = vehicleClass

        self.x = engine.x[direction][lane]
        self.y = engine.y[direction][lane]
        self._placed = False
        self.spawnTime = engine.simulation_elapsed
        self.spawnDistance = None

        self.crossed = 0
        self.turned = 0
        self.rotateAngle = 0

        self.waitTime = 0.0

        self.waitingDueToSignalQueue = False
        # px per simulated second
        self.max_speed = self.base_speed * engine.fps
        self.velocity = self.max_speed
        self._committed_to_cross = False
        self._had_green = False
        self._in_junction = False
        self._exit_heading = None
        self._exit_index = None

        self.crossedLogged = False
        self.emergencyWaitLogged = False
        self._wait_text_font = None

        self.receivedEmergencyHold = False
        self.totalEmergencyHoldTime = 0.0
        self.emergencyHoldSuccessLogged = False

        # Fully build the vehicle (image included) before adding it to the
        # shared engine.vehicles list. The spawner and controller threads run
        # concurrently, and code reading vehicle.image could otherwise see a
        # vehicle without an image and raise AttributeError.
        self.originalImage = self.load_vehicle_image(vehicleClass, direction)
        self.image = self.originalImage.copy()

        engine.vehicles[direction][lane].append(self)
        self.index = len(engine.vehicles[direction][lane]) - 1
        self.crossedIndex = 0

        if len(engine.vehicles[direction][lane]) > 1 and engine.vehicles[direction][lane][self.index - 1].crossed == 0:
            prev_vehicle = engine.vehicles[direction][lane][self.index - 1]

            if direction == "right":
                self.stop = prev_vehicle.stop - prev_vehicle.image.get_rect().width - engine.stoppingGap
            elif direction == "left":
                self.stop = prev_vehicle.stop + prev_vehicle.image.get_rect().width + engine.stoppingGap
            elif direction == "down":
                self.stop = prev_vehicle.stop - prev_vehicle.image.get_rect().height - engine.stoppingGap
            elif direction == "up":
                self.stop = prev_vehicle.stop + prev_vehicle.image.get_rect().height + engine.stoppingGap
            else:
                self.stop = engine.defaultStop[direction]
        else:
            self.stop = engine.defaultStop[direction]

        engine.simulation.add(self)

    def place_at_spawn(self):
        """Put the vehicle at its lane's spawn origin, or right behind the
        lane's last vehicle if that one has not cleared the origin yet.

        The origin itself never moves. Previously every spawn pushed the
        origin back by one vehicle length and it was never restored, so the
        Nth vehicle of a lane entered N lengths away from the intersection no
        matter how empty the road was (measured: 322px for the first vehicle,
        4500px after 20 simulated minutes).

        Runs on the main loop's first move() of this vehicle, not in
        __init__: the spawner thread must not read another vehicle's position
        while the main loop is moving it. Inside a tick vehicles move in spawn
        order, so the vehicle ahead has already been moved when this runs.
        """
        self._placed = True
        engine = self.engine
        prev = self.previous_vehicle()

        if prev is not None:
            gap = engine.stoppingGap
            rect = self.image.get_rect()
            prev_rect = prev.image.get_rect()

            if self.direction == "right":
                self.x = min(self.x, prev.x - rect.width - gap)
            elif self.direction == "left":
                self.x = max(self.x, prev.x + prev_rect.width + gap)
            elif self.direction == "down":
                self.y = min(self.y, prev.y - rect.height - gap)
            elif self.direction == "up":
                self.y = max(self.y, prev.y + prev_rect.height + gap)

        leader = self.leader_before_turn()
        if leader is not None:
            # Enter at the speed the gap to the vehicle ahead allows.
            free_gap = max(0.0, self.gap_to(leader, self.HEADING[self.direction]) - engine.stoppingGap)
            self.velocity = min(self.max_speed, free_gap / engine.timeHeadway)

        self.spawnDistance = self.distance_to_stop_line()

    def distance_to_stop_line(self):
        line = self.engine.stopLines[self.direction]
        rect = self.image.get_rect()

        if self.direction == "right":
            return max(0.0, line - (self.x + rect.width))
        if self.direction == "down":
            return max(0.0, line - (self.y + rect.height))
        if self.direction == "left":
            return max(0.0, self.x - line)
        return max(0.0, self.y - line)

    def load_vehicle_image(self, vehicleClass, direction):
        path = str(self.engine.images_dir / "vehicles" / f"{vehicleClass}.png")
        base_image = pygame.image.load(path)

        if pygame.display.get_surface() is not None:
            base_image = base_image.convert_alpha()

        angle = self.ROTATION_MAP.get(direction, 0)
        return pygame.transform.rotate(base_image, angle)


    def update_signal_wait_time(self, old_x, old_y):
        self.waitingDueToSignalQueue = False

        if self.crossed == 1:
            return

        moved_distance = abs(self.x - old_x) + abs(self.y - old_y)

        if moved_distance >= 0.01:
            return

        direction_no = self.engine.directionToNumber[self.direction]

        if self.controller.is_green(direction_no):
            return

        tolerance = 3.0

        if self.direction == "right":
            waiting_at_own_stop = (
                self.x + self.image.get_rect().width >= self.engine.defaultStop[self.direction] - tolerance
            )

        elif self.direction == "down":
            waiting_at_own_stop = (
                self.y + self.image.get_rect().height >= self.engine.defaultStop[self.direction] - tolerance
            )

        elif self.direction == "left":
            waiting_at_own_stop = self.x <= self.engine.defaultStop[self.direction] + tolerance

        elif self.direction == "up":
            waiting_at_own_stop = self.y <= self.engine.defaultStop[self.direction] + tolerance

        else:
            waiting_at_own_stop = False

        prev = self.previous_vehicle()

        waiting_behind_signal_queue = (
            prev is not None
            and prev.crossed == 0
            and getattr(prev, "waitingDueToSignalQueue", False)
        )

        if not waiting_at_own_stop and not waiting_behind_signal_queue:
            return

        self.waitingDueToSignalQueue = True
        self.waitTime += self.engine.current_simulation_delta
        
    def draw_wait_time(self, screen):
        if self.crossed == 1:
            return

        if self.waitTime <= 0:
            return

        if self._wait_text_font is None:
            self._wait_text_font = pygame.font.SysFont("Arial", 12, bold=True)

        text = self._wait_text_font.render(
            f"{self.waitTime:.1f}s",
            True,
            (255, 255, 255),
        )

        image_rect = self.image.get_rect()

        text_rect = text.get_rect(
            topright=(
                int(self.x + image_rect.width),
                int(self.y - 6),
            )
        )

        pygame.draw.rect(
            screen,
            (0, 0, 0),
            text_rect.inflate(4, 2),
        )

        screen.blit(text, text_rect)


    def move_by(self, dx, dy):
        self.x += dx
        self.y += dy
        return True

    def previous_vehicle(self):
        if self.index <= 0:
            return None

        vehicles = self.engine.vehicles[self.direction][self.lane]

        if self.index - 1 >= len(vehicles):
            return None

        return vehicles[self.index - 1]


    def log_crossing_if_needed(self):
        engine = self.engine

        if self.direction == "right":
            crossed_now = self.x + self.image.get_rect().width > engine.stopLines[self.direction]
        elif self.direction == "down":
            crossed_now = self.y + self.image.get_rect().height > engine.stopLines[self.direction]
        elif self.direction == "left":
            crossed_now = self.x < engine.stopLines[self.direction]
        elif self.direction == "up":
            crossed_now = self.y < engine.stopLines[self.direction]
        else:
            crossed_now = False

        if self.crossed == 0 and crossed_now:
            self.crossed = 1
            engine.vehicles[self.direction]["crossed"] += 1

            if self.turnIntent == "straight":
                engine.vehiclesNotTurned[self.direction][self.lane].append(self)
                self.crossedIndex = len(engine.vehiclesNotTurned[self.direction][self.lane]) - 1


    def log_vehicle_metrics_if_crossed(self):
        if self.crossed == 0:
            return

        if self.crossedLogged:
            return

        engine = self.engine

        self.crossedLogged = True
        engine.mark_direction_served(self.direction)

        # Vehicles spawned during warm-up start from an empty intersection
        # and are left out of every wait/delay statistic.
        if self.spawnTime < engine.warmup_time:
            return

        engine.vehicleMetrics[self.direction].append(self.waitTime)
        engine.vehicleDelays.append(self.control_delay())

        if self.isEmergency:
            engine.emergencyVehicleMetrics["wait_times"].append(self.waitTime)
            engine.emergencyVehicleMetrics["crossed"] += 1

            if (
                self.receivedEmergencyHold
                and not self.emergencyHoldSuccessLogged
            ):
                engine.emergencyVehicleMetrics["hold_success_count"] += 1
                self.emergencyHoldSuccessLogged = True

        else:
            engine.normalVehicleMetrics["wait_times"].append(self.waitTime)
            engine.normalVehicleMetrics["crossed"] += 1

    def control_delay(self):
        """Seconds lost to the signal: time from spawn to the stop line minus
        the time the same trip takes at free flow. Unlike waitTime it also
        counts queue discharge and start-up delay during green."""
        free_flow = (self.spawnDistance or 0.0) / (self.base_speed * self.engine.fps)
        return max(0.0, self.engine.simulation_elapsed - self.spawnTime - free_flow)

    # Heading of each approach: (axis, sign).
    HEADING = {"right": ("x", 1), "down": ("y", 1), "left": ("x", -1), "up": ("y", -1)}

    # Turn geometry per (approach, turn): the position offset of one 3-degree
    # rotation step, the rotation sense and the heading after the turn.
    TURNS = {
        ("right", "left"): (2.4, -2.8, True, ("y", -1)),
        ("right", "right"): (2.0, 1.8, False, ("y", 1)),
        ("down", "left"): (1.2, 1.8, True, ("x", 1)),
        ("down", "right"): (-2.5, 2.0, False, ("x", -1)),
        ("left", "left"): (-1.0, 1.2, True, ("y", 1)),
        ("left", "right"): (-1.8, -2.5, False, ("y", -1)),
        ("up", "left"): (-2.0, -1.2, True, ("x", -1)),
        ("up", "right"): (1.0, -1.0, False, ("x", 1)),
    }

    def front(self, heading):
        """Coordinate of the leading edge along `heading`."""
        axis, sign = heading
        rect = self.image.get_rect()
        if axis == "x":
            return self.x + rect.width if sign > 0 else self.x
        return self.y + rect.height if sign > 0 else self.y

    def rear(self, heading):
        axis, sign = heading
        rect = self.image.get_rect()
        if axis == "x":
            return self.x if sign > 0 else self.x + rect.width
        return self.y if sign > 0 else self.y + rect.height

    def distance_ahead(self, heading, coordinate):
        """Distance from the leading edge to `coordinate`, positive ahead."""
        return heading[1] * (coordinate - self.front(heading))

    def gap_to(self, leader, heading):
        return heading[1] * (leader.rear(heading) - self.front(heading))

    def leader_before_turn(self):
        prev = self.previous_vehicle()
        if prev is None or prev.turned == 1:
            return None
        return prev

    # How many of the vehicles that entered an exit road before this one
    # are checked when looking for the one to follow.
    EXIT_LOOKBACK = 8

    def join_exit_road(self, heading):
        """Register on the road this vehicle leaves the intersection by.
        Vehicles from different approaches meet there."""
        road = self.engine.exitRoads[heading]
        road.append(self)
        self._exit_heading = heading
        self._exit_index = len(road) - 1

    def leader_on_exit_road(self):
        """Nearest vehicle ahead in the same lane of the exit road."""
        heading = self._exit_heading
        road = self.engine.exitRoads[heading]
        start = max(0, self._exit_index - self.EXIT_LOOKBACK)
        lateral = "y" if heading[0] == "x" else "x"
        own_low = getattr(self, lateral)
        rect = self.image.get_rect()
        own_high = own_low + (rect.height if lateral == "y" else rect.width)

        leader, leader_gap = None, None
        for vehicle in road[start:self._exit_index]:
            other_rect = vehicle.image.get_rect()
            low = getattr(vehicle, lateral)
            high = low + (other_rect.height if lateral == "y" else other_rect.width)
            if high <= own_low or low >= own_high:
                continue
            gap = self.gap_to(vehicle, heading)
            if gap < -other_rect.width - other_rect.height:
                continue
            if leader_gap is None or gap < leader_gap:
                leader, leader_gap = vehicle, gap
        return leader

    def update_junction_presence(self):
        """Keep the engine's list of vehicles inside the junction box."""
        inside = self.engine.junctionVehicles
        if self.crossed == 0:
            return
        rect = self.image.get_rect()
        in_box = self.engine.junctionBox.colliderect(
            pygame.Rect(int(self.x), int(self.y), rect.width, rect.height)
        )
        if in_box and not self._in_junction:
            self._in_junction = True
            inside.append(self)
        elif not in_box and self._in_junction:
            self._in_junction = False
            inside.remove(self)

    def junction_blocked(self):
        """True while a vehicle from another approach is still inside the
        junction."""
        return any(vehicle.direction != self.direction for vehicle in self.engine.junctionVehicles)

    def must_stop_at_line(self, heading):
        """True while the vehicle has to hold at the stop line: the signal
        is not green, or it is green but cross traffic is still inside the
        junction. A vehicle too close to stop at the moment the light turns
        drives through."""
        if self.crossed == 1:
            return False

        green = self.controller.is_green(self.direction_number)
        light_just_changed = self._had_green and not green
        self._had_green = green

        if green:
            self._committed_to_cross = False
            return self.junction_blocked()

        if light_just_changed:
            distance = self.distance_ahead(heading, self.engine.defaultStop[self.direction])
            braking_distance = self.velocity ** 2 / (2 * self.engine.hardBraking)
            self._committed_to_cross = self.velocity > 0 and distance < braking_distance

        if self._committed_to_cross and self.velocity == 0:
            # Held up after all (queue ahead): the commitment is void.
            self._committed_to_cross = False

        return not self._committed_to_cross

    def advance(self, heading, leader, stop_distance=None, slow_to=None):
        """Move one tick along `heading`.

        Speed follows three limits: acceleration towards the vehicle's own
        top speed, a time gap behind the leader, and a braking curve towards
        a stop point. The step never closes the standing gap to the leader
        and never passes the stop point. `slow_to` is a (speed, distance)
        pair: the speed to be down to at a point ahead, used before a turn.
        """
        engine = self.engine
        dt = engine.current_simulation_delta
        target = min(self.max_speed, self.velocity + engine.acceleration * dt)
        room = None

        if leader is not None:
            free_gap = max(0.0, self.gap_to(leader, heading) - engine.stoppingGap)
            # The time gap alone closes the last metres ever more slowly, so
            # behind a standing leader the braking curve takes over. The
            # curve fades out as the leader picks up speed, which keeps a
            # queue from starting as one block.
            follow_speed = max(
                free_gap / engine.timeHeadway,
                math.sqrt(2 * engine.comfortBraking * free_gap) - 2 * leader.velocity,
            )
            if self.velocity == 0 and free_gap < engine.startGap:
                # A standing vehicle waits until the leader has pulled away
                # a little, so a queue starts one vehicle after another.
                follow_speed = 0.0
            target = min(target, follow_speed)
            room = free_gap

        if stop_distance is not None:
            stop_distance = max(0.0, stop_distance)
            target = min(target, math.sqrt(2 * engine.comfortBraking * stop_distance))
            room = stop_distance if room is None else min(room, stop_distance)

        if slow_to is not None:
            # Reach `slow_to[0]` px/s by the point `slow_to[1]` px ahead.
            limit_speed, limit_distance = slow_to
            target = min(
                target,
                math.sqrt(limit_speed ** 2 + 2 * engine.comfortBraking * max(0.0, limit_distance)),
            )

        # Never brake harder than the hard limit, unless the room ahead
        # leaves no choice.
        target = max(target, self.velocity - engine.hardBraking * dt)

        step = target * dt
        if room is not None:
            step = min(step, room)
            if room < 0.05:
                # Close enough: come to rest instead of creeping forever.
                step = 0.0
                target = 0.0

        self.velocity = min(target, step / dt) if room is not None and dt > 0 else target
        if slow_to is not None:
            step = min(step, max(0.0, slow_to[1]))

        axis, sign = heading
        if axis == "x":
            self.x += sign * step
        else:
            self.y += sign * step

    def advance_turn(self, dx_base, dy_base, clockwise):
        """Rotate through the turn at the vehicle's own speed. The path is
        the same at every playback speed: the position offset is tied to the
        rotation angle."""
        engine = self.engine
        dt = engine.current_simulation_delta
        self.velocity = min(
            self.max_speed * engine.turnSpeedFactor,
            self.velocity + engine.acceleration * dt,
        )

        steps = self.velocity * dt / math.hypot(dx_base, dy_base)
        angle_step = min(engine.rotationAngle * steps, 90 - self.rotateAngle)
        move_ratio = angle_step / engine.rotationAngle

        self.rotateAngle += angle_step
        angle = self.rotateAngle if clockwise else -self.rotateAngle
        self.image = pygame.transform.rotate(self.originalImage, angle)
        self.x += dx_base * move_ratio
        self.y += dy_base * move_ratio

        if self.rotateAngle >= 90:
            self.rotateAngle = 90
            self.turned = 1
            turned = self.engine.vehiclesTurned[self.direction][self.lane]
            turned.append(self)
            self.crossedIndex = len(turned) - 1
            self.join_exit_road(self.TURNS[(self.direction, self.turnIntent)][3])

    def move(self):
        if not self._placed:
            self.place_at_spawn()

        old_x, old_y = self.x, self.y
        engine = self.engine
        heading = self.HEADING[self.direction]

        was_crossed = self.crossed
        self.log_crossing_if_needed()
        if self.crossed == 1 and was_crossed == 0 and self.turnIntent == "straight":
            self.join_exit_road(heading)

        if self.turnIntent == "straight":
            if self.crossed == 0:
                stop_distance = None
                if self.must_stop_at_line(heading):
                    stop_distance = self.distance_ahead(heading, engine.defaultStop[self.direction])
                self.advance(heading, self.leader_before_turn(), stop_distance)
            else:
                self.advance(heading, self.leader_on_exit_road())

        elif self.turned == 1:
            self.advance(self._exit_heading, self.leader_on_exit_road())

        else:
            trigger = engine.turnTriggerPoints[self.direction][self.turnIntent]
            to_trigger = self.distance_ahead(heading, trigger)

            if self.rotateAngle == 0 and to_trigger > 0:
                stop_distance = None
                if self.must_stop_at_line(heading):
                    stop_distance = self.distance_ahead(heading, engine.defaultStop[self.direction])
                turn_speed = self.max_speed * engine.turnSpeedFactor
                self.advance(heading, self.leader_before_turn(), stop_distance, slow_to=(turn_speed, to_trigger))
            else:
                dx_base, dy_base, clockwise, _exit_heading = self.TURNS[(self.direction, self.turnIntent)]
                self.advance_turn(dx_base, dy_base, clockwise)

        self.update_junction_presence()
        self.update_signal_wait_time(old_x, old_y)
        self.log_vehicle_metrics_if_crossed()
