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

        self.crossed = 0
        self.turned = 0
        self.rotateAngle = 0

        self.waitTime = 0.0

        self.waitingDueToSignalQueue = False
        self._departure_start = None

        self.crossedLogged = False
        self.emergencyWaitLogged = False
        self._wait_text_font = None

        self.receivedEmergencyHold = False
        self.totalEmergencyHoldTime = 0.0
        self.emergencyHoldSuccessLogged = False

        # Once araci fully hazirla (image dahil), ANCAK BUNDAN SONRA
        # paylasilan engine.vehicles listesine ekle. Spawner thread'i ile
        # controller thread'i esitzamanli calistigi icin, self.image
        # set edilmeden once listeye eklenirse controller (ozellikle
        # optimal_ground_truth_strategy'nin emergency ETA hesabi gibi
        # vehicle.image'a dogrudan erisen kod) tam o pencerede araca
        # bakip AttributeError ile cokebiliyordu.
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

        if direction == "right":
            engine.x[direction][lane] -= self.image.get_rect().width + engine.stoppingGap
        elif direction == "left":
            engine.x[direction][lane] += self.image.get_rect().width + engine.stoppingGap
        elif direction == "down":
            engine.y[direction][lane] -= self.image.get_rect().height + engine.stoppingGap
        elif direction == "up":
            engine.y[direction][lane] += self.image.get_rect().height + engine.stoppingGap

        engine.simulation.add(self)

    def load_vehicle_image(self, vehicleClass, direction):
        path = str(self.engine.images_dir / "vehicles" / f"{vehicleClass}.png")
        base_image = pygame.image.load(path)

        if pygame.display.get_surface() is not None:
            base_image = base_image.convert_alpha()

        angle = self.ROTATION_MAP.get(direction, 0)
        return pygame.transform.rotate(base_image, angle)

    def current_speed(self):
        return self.base_speed * self.engine.playback_speed

    def departure_speed(self, full_speed):
        """Ramped speed for the first startupLostTime seconds after THIS
        vehicle personally starts departing from a stop -- tied to this
        vehicle's own first-movement tick, not to the signal phase's start
        time. A vehicle already moving must never be re-slowed just because
        the same direction's green phase happens to restart/repeat while it
        is still crossed==0 (e.g. re-selected shortly after by the
        controller) -- only a vehicle that was actually stationary gets a
        fresh departure ramp, once, the first tick it's allowed to move."""
        if self._departure_start is None:
            self._departure_start = self.engine.simulation_elapsed

        elapsed = self.engine.simulation_elapsed - self._departure_start

        if elapsed >= self.engine.startupLostTime:
            return full_speed

        return full_speed * max(0.15, elapsed / self.engine.startupLostTime)

    def turn_step_ratio(self):
        ratio = self.engine.playback_speed
        return max(1.0, min(ratio, 3.0))

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

        tolerance = max(2.0, self.current_speed() + 1.0)

        if self.direction == "right":
            waiting_at_own_stop = (
                self.x + self.image.get_rect().width >= self.stop - tolerance
            )

        elif self.direction == "down":
            waiting_at_own_stop = (
                self.y + self.image.get_rect().height >= self.stop - tolerance
            )

        elif self.direction == "left":
            waiting_at_own_stop = self.x <= self.stop + tolerance

        elif self.direction == "up":
            waiting_at_own_stop = self.y <= self.stop + tolerance

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

    def _trigger_reached(self, side):
        trigger = self.engine.turnTriggerPoints[self.direction][side]

        if self.direction == "right":
            return self.x + self.image.get_rect().width >= trigger
        if self.direction == "down":
            return self.y + self.image.get_rect().height >= trigger
        if self.direction == "left":
            return self.x <= trigger
        if self.direction == "up":
            return self.y <= trigger

        return False

    def clamped_step_to_trigger(self, side, speed):
        # Bir tick'te tam `speed` kadar ilerlemek, yüksek playback_speed'de
        # tetik noktasını büyük ölçüde aşmaya (overshoot) yol açar --
        # apply_turn()'ün dx/dy ofsetleri sabit olduğundan, farklı bir
        # başlangıç pozisyonundan başlayan dönüş farklı bir final pozisyonda
        # biter (playback_speed'e bağlı "kayma"). Adımı, tetik noktasını
        # aşmayacak şekilde sınırlayarak dönüşün her zaman aynı pozisyondan
        # başlamasını garanti ediyoruz.
        trigger = self.engine.turnTriggerPoints[self.direction][side]
        width = self.image.get_rect().width
        height = self.image.get_rect().height

        if self.direction == "right":
            remaining = trigger - (self.x + width)
        elif self.direction == "down":
            remaining = trigger - (self.y + height)
        elif self.direction == "left":
            remaining = self.x - trigger
        elif self.direction == "up":
            remaining = self.y - trigger
        else:
            return speed

        if remaining <= 0:
            return speed

        return min(speed, remaining)

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

    def previous_vehicle_allows_forward(self):
        prev = self.previous_vehicle()

        if prev is None:
            return True

        if prev.turned == 1:
            return True

        if self.direction == "right":
            return self.x + self.image.get_rect().width < prev.x - self.engine.movingGap

        if self.direction == "down":
            return self.y + self.image.get_rect().height < prev.y - self.engine.movingGap

        if self.direction == "left":
            return self.x > prev.x + prev.image.get_rect().width + self.engine.movingGap

        if self.direction == "up":
            return self.y > prev.y + prev.image.get_rect().height + self.engine.movingGap

        return True

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

    def can_continue_after_crossing_straight(self):
        engine = self.engine

        if self.crossedIndex == 0:
            return True

        prev = engine.vehiclesNotTurned[self.direction][self.lane][self.crossedIndex - 1]

        if self.direction == "right":
            return self.x + self.image.get_rect().width < prev.x - engine.movingGap

        if self.direction == "down":
            return self.y + self.image.get_rect().height < prev.y - engine.movingGap

        if self.direction == "left":
            return self.x > prev.x + prev.image.get_rect().width + engine.movingGap

        if self.direction == "up":
            return self.y > prev.y + prev.image.get_rect().height + engine.movingGap

        return True

    def can_continue_after_turn(self, axis, sign):
        engine = self.engine

        if self.crossedIndex == 0:
            return True

        prev = engine.vehiclesTurned[self.direction][self.lane][self.crossedIndex - 1]

        if axis == "x" and sign > 0:
            return self.x + self.image.get_rect().width < prev.x - engine.movingGap

        if axis == "x" and sign < 0:
            return self.x > prev.x + prev.image.get_rect().width + engine.movingGap

        if axis == "y" and sign > 0:
            return self.y + self.image.get_rect().height < prev.y - engine.movingGap

        if axis == "y" and sign < 0:
            return self.y > prev.y + prev.image.get_rect().height + engine.movingGap

        return True

    def apply_turn(self, dx_base, dy_base, clockwise=True):
        engine = self.engine
        step_ratio = self.turn_step_ratio()
        angle_step = min(engine.rotationAngle * step_ratio, 90 - self.rotateAngle)

        if angle_step <= 0:
            return False

        move_ratio = angle_step / engine.rotationAngle
        dx = dx_base * move_ratio
        dy = dy_base * move_ratio

        self.rotateAngle += angle_step

        if clockwise:
            self.image = pygame.transform.rotate(self.originalImage, self.rotateAngle)
        else:
            self.image = pygame.transform.rotate(self.originalImage, -self.rotateAngle)

        self.x += dx
        self.y += dy

        if self.rotateAngle >= 90:
            self.rotateAngle = 90
            self.turned = 1

        return True

    def log_vehicle_metrics_if_crossed(self):
        if self.crossed == 0:
            return

        if self.crossedLogged:
            return

        engine = self.engine

        engine.vehicleMetrics[self.direction].append(self.waitTime)

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

        self.crossedLogged = True
        engine.mark_direction_served(self.direction)

    def move(self):
        old_x, old_y = self.x, self.y
        engine = self.engine
        speed = self.current_speed()

        # Isik durumu (render/karar icin) aninda degisir; ama az once
        # kirmizidan kurtulan bir arac gercekte aninda tam hiza gecmez --
        # self.departure_speed() bu reaksiyon/ivmelenme gecikmesini
        # modelliyor (bkz. docs/scenario_capacity_calibration.md, gercek
        # kayitlardan olculen ~3s start-up lost time). Sadece DURAKLAMIS/
        # kuyruktaki bir aracin KENDI ilk kalkis anina gore uygulanir --
        # serbest yaklasan, zaten gecmis, ya da halihazirda hareket halindeki
        # araclar (faz yeniden baslasa/uzasa bile) speed ile hareket etmeye
        # devam eder.
        green_right = self.controller.is_green(0)
        green_down = self.controller.is_green(1)
        green_left = self.controller.is_green(2)
        green_up = self.controller.is_green(3)

        self.log_crossing_if_needed()

        if self.direction == "right":
            if self.turnIntent == "left":
                if self.crossed == 0 or not self._trigger_reached("left"):
                    at_stop = self.crossed == 0 and self.x + self.image.get_rect().width > self.stop
                    if (
                        (self.x + self.image.get_rect().width <= self.stop or green_right or self.crossed == 1)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(self.clamped_step_to_trigger("left", step_speed), 0)
                else:
                    if self.turned == 0:
                        turned_now = self.apply_turn(2.4, -2.8, True)
                        if turned_now and self.turned == 1:
                            engine.vehiclesTurned[self.direction][self.lane].append(self)
                            self.crossedIndex = len(engine.vehiclesTurned[self.direction][self.lane]) - 1
                    elif self.can_continue_after_turn("y", -1):
                        self.move_by(0, -speed)

            elif self.turnIntent == "right":
                if self.crossed == 0 or not self._trigger_reached("right"):
                    at_stop = self.crossed == 0 and self.x + self.image.get_rect().width > self.stop
                    if (
                        (self.x + self.image.get_rect().width <= self.stop or green_right or self.crossed == 1)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(self.clamped_step_to_trigger("right", step_speed), 0)
                else:
                    if self.turned == 0:
                        turned_now = self.apply_turn(2.0, 1.8, False)
                        if turned_now and self.turned == 1:
                            engine.vehiclesTurned[self.direction][self.lane].append(self)
                            self.crossedIndex = len(engine.vehiclesTurned[self.direction][self.lane]) - 1
                    elif self.can_continue_after_turn("y", 1):
                        self.move_by(0, speed)

            else:
                if self.crossed == 0:
                    at_stop = self.x + self.image.get_rect().width > self.stop
                    if (
                        (self.x + self.image.get_rect().width <= self.stop or green_right)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(step_speed, 0)
                elif self.can_continue_after_crossing_straight():
                    self.move_by(speed, 0)

        elif self.direction == "down":
            if self.turnIntent == "left":
                if self.crossed == 0 or not self._trigger_reached("left"):
                    at_stop = self.crossed == 0 and self.y + self.image.get_rect().height > self.stop
                    if (
                        (self.y + self.image.get_rect().height <= self.stop or green_down or self.crossed == 1)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(0, self.clamped_step_to_trigger("left", step_speed))
                else:
                    if self.turned == 0:
                        turned_now = self.apply_turn(1.2, 1.8, True)
                        if turned_now and self.turned == 1:
                            engine.vehiclesTurned[self.direction][self.lane].append(self)
                            self.crossedIndex = len(engine.vehiclesTurned[self.direction][self.lane]) - 1
                    elif self.can_continue_after_turn("x", 1):
                        self.move_by(speed, 0)

            elif self.turnIntent == "right":
                if self.crossed == 0 or not self._trigger_reached("right"):
                    at_stop = self.crossed == 0 and self.y + self.image.get_rect().height > self.stop
                    if (
                        (self.y + self.image.get_rect().height <= self.stop or green_down or self.crossed == 1)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(0, self.clamped_step_to_trigger("right", step_speed))
                else:
                    if self.turned == 0:
                        turned_now = self.apply_turn(-2.5, 2.0, False)
                        if turned_now and self.turned == 1:
                            engine.vehiclesTurned[self.direction][self.lane].append(self)
                            self.crossedIndex = len(engine.vehiclesTurned[self.direction][self.lane]) - 1
                    elif self.can_continue_after_turn("x", -1):
                        self.move_by(-speed, 0)

            else:
                if self.crossed == 0:
                    at_stop = self.y + self.image.get_rect().height > self.stop
                    if (
                        (self.y + self.image.get_rect().height <= self.stop or green_down)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(0, step_speed)
                elif self.can_continue_after_crossing_straight():
                    self.move_by(0, speed)

        elif self.direction == "left":
            if self.turnIntent == "left":
                if self.crossed == 0 or not self._trigger_reached("left"):
                    at_stop = self.crossed == 0 and self.x < self.stop
                    if (
                        (self.x >= self.stop or green_left or self.crossed == 1)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(-self.clamped_step_to_trigger("left", step_speed), 0)
                else:
                    if self.turned == 0:
                        turned_now = self.apply_turn(-1.0, 1.2, True)
                        if turned_now and self.turned == 1:
                            engine.vehiclesTurned[self.direction][self.lane].append(self)
                            self.crossedIndex = len(engine.vehiclesTurned[self.direction][self.lane]) - 1
                    elif self.can_continue_after_turn("y", 1):
                        self.move_by(0, speed)

            elif self.turnIntent == "right":
                if self.crossed == 0 or not self._trigger_reached("right"):
                    at_stop = self.crossed == 0 and self.x < self.stop
                    if (
                        (self.x >= self.stop or green_left or self.crossed == 1)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(-self.clamped_step_to_trigger("right", step_speed), 0)
                else:
                    if self.turned == 0:
                        turned_now = self.apply_turn(-1.8, -2.5, False)
                        if turned_now and self.turned == 1:
                            engine.vehiclesTurned[self.direction][self.lane].append(self)
                            self.crossedIndex = len(engine.vehiclesTurned[self.direction][self.lane]) - 1
                    elif self.can_continue_after_turn("y", -1):
                        self.move_by(0, -speed)

            else:
                if self.crossed == 0:
                    at_stop = self.x < self.stop
                    if (
                        (self.x >= self.stop or green_left)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(-step_speed, 0)
                elif self.can_continue_after_crossing_straight():
                    self.move_by(-speed, 0)

        elif self.direction == "up":
            if self.turnIntent == "left":
                if self.crossed == 0 or not self._trigger_reached("left"):
                    at_stop = self.crossed == 0 and self.y < self.stop
                    if (
                        (self.y >= self.stop or green_up or self.crossed == 1)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(0, -self.clamped_step_to_trigger("left", step_speed))
                else:
                    if self.turned == 0:
                        turned_now = self.apply_turn(-2.0, -1.2, True)
                        if turned_now and self.turned == 1:
                            engine.vehiclesTurned[self.direction][self.lane].append(self)
                            self.crossedIndex = len(engine.vehiclesTurned[self.direction][self.lane]) - 1
                    elif self.can_continue_after_turn("x", -1):
                        self.move_by(-speed, 0)

            elif self.turnIntent == "right":
                if self.crossed == 0 or not self._trigger_reached("right"):
                    at_stop = self.crossed == 0 and self.y < self.stop
                    if (
                        (self.y >= self.stop or green_up or self.crossed == 1)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(0, -self.clamped_step_to_trigger("right", step_speed))
                else:
                    if self.turned == 0:
                        turned_now = self.apply_turn(1.0, -1.0, False)
                        if turned_now and self.turned == 1:
                            engine.vehiclesTurned[self.direction][self.lane].append(self)
                            self.crossedIndex = len(engine.vehiclesTurned[self.direction][self.lane]) - 1
                    elif self.can_continue_after_turn("x", 1):
                        self.move_by(speed, 0)

            else:
                if self.crossed == 0:
                    at_stop = self.y < self.stop
                    if (
                        (self.y >= self.stop or green_up)
                        and self.previous_vehicle_allows_forward()
                    ):
                        step_speed = self.departure_speed(speed) if at_stop else speed
                        self.move_by(0, -step_speed)
                elif self.can_continue_after_crossing_straight():
                    self.move_by(0, -speed)

        self.update_signal_wait_time(old_x, old_y)
        self.log_vehicle_metrics_if_crossed()