"""Side panel of the simulation window.

Shows, top to bottom: the run, one row per approach, the last decision, the
totals of the run, the last green phases and the control buttons. Every
number is read from the engine, nothing is computed for display only.
"""
import pygame

from controllers.strategies.demand_strategy import APPROACH_NAMES
from core.paths import FONTS_DIR
from state_providers.ground_truth_provider import GroundTruthStateProvider

DIRECTIONS = ["right", "down", "left", "up"]

BG = (17, 19, 24)
CARD = (24, 27, 34)
LINE = (40, 45, 55)
TEXT = (233, 236, 241)
MUTED = (134, 143, 158)
GREEN = (62, 207, 122)
YELLOW = (240, 185, 58)
RED = (239, 90, 90)
ACCENT = (96, 165, 250)
ROW_ON = (25, 44, 35)
BAR = (58, 66, 82)
BUTTON = (30, 34, 43)

PAD = 20
INNER = 16
ROW_H = 46
GAP = 14
# A count bar is full at this many vehicles on one approach.
BAR_FULL = 12


class SidePanel:
    def __init__(self, engine, rect):
        self.engine = engine
        self.rect = pygame.Rect(rect)

        regular = str(FONTS_DIR / "NotoSans-Regular.ttf")
        medium = str(FONTS_DIR / "NotoSans-Medium.ttf")
        self.title_font = pygame.font.Font(medium, 21)
        self.value_font = pygame.font.Font(medium, 22)
        self.font = pygame.font.Font(regular, 15)
        self.strong_font = pygame.font.Font(medium, 15)
        self.small_font = pygame.font.Font(regular, 13)
        self.label_font = pygame.font.Font(medium, 11)

        self.uses_camera = hasattr(engine.state_provider, "detect_for_display")
        # The exact counts, compared with what the camera reports.
        self.truth = GroundTruthStateProvider(engine)
        self._camera_observation = None
        self._truth_at_observation = {d: 0 for d in DIRECTIONS}
        self.camera_checks = 0
        self.camera_matches = 0

        button_w = (self.rect.width - 2 * PAD - 2 * 10) // 3
        button_y = self.rect.bottom - PAD - 40
        self.buttons = {
            name: pygame.Rect(self.rect.x + PAD + i * (button_w + 10), button_y, button_w, 40)
            for i, name in enumerate(["pause", "stop", "restart"])
        }

    # --- drawing helpers -------------------------------------------------

    def text(self, screen, value, x, y, font=None, color=TEXT, align="left"):
        surface = (font or self.font).render(str(value), True, color)
        if align == "right":
            x -= surface.get_width()
        screen.blit(surface, (x, y))
        return surface.get_width()

    def card(self, screen, y, height, title):
        """A titled block. Returns the y of its first content line."""
        rect = pygame.Rect(self.rect.x + PAD, y, self.rect.width - 2 * PAD, height)
        pygame.draw.rect(screen, CARD, rect, border_radius=8)
        pygame.draw.rect(screen, LINE, rect, width=1, border_radius=8)
        self.text(screen, title.upper(), rect.x + INNER, y + 12, self.label_font, MUTED)
        return y + 36

    def wrap(self, value, max_width, max_lines):
        lines, line = [], ""
        for word in str(value).split():
            candidate = f"{line} {word}".strip()
            if self.font.size(candidate)[0] <= max_width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
        return lines[:max_lines]

    @staticmethod
    def seconds(value, digits=0):
        return f"{value:.{digits}f} sn".replace(".", ",")

    # --- data --------------------------------------------------------------

    def counts(self):
        """Per approach: (count the controller works with, exact count).
        With the camera the exact count is taken at the moment of the
        observation, so the two numbers describe the same instant."""
        truth_now = self.truth.get_state()
        if not self.uses_camera:
            return {d: (truth_now[d], truth_now[d]) for d in DIRECTIONS}

        observation = self.engine.state_provider.get_observation()
        if observation is not self._camera_observation:
            self._camera_observation = observation
            self._truth_at_observation = truth_now
            for d in DIRECTIONS:
                self.camera_checks += 1
                self.camera_matches += observation[d]["visible_count"] == truth_now[d]
        return {
            d: (observation[d]["visible_count"], self._truth_at_observation[d])
            for d in DIRECTIONS
        }

    def waiting(self, direction):
        """Longest wait and emergency presence among vehicles that have not
        crossed yet."""
        longest = 0.0
        emergency = False
        for lane in (1, 2):
            for vehicle in self.engine.vehicles[direction][lane]:
                if vehicle.crossed == 0:
                    longest = max(longest, vehicle.waitTime)
                    emergency = emergency or vehicle.isEmergency
        return longest, emergency

    def last_decision(self):
        engine = self.engine
        if engine.controller_mode != "adaptive":
            green = engine.fixed_config["green_time"]
            return f"Sabit süre: her yöne sırayla {green} saniye yeşil verilir."
        return engine.latest_decision_context.get("reason_full") or "-"

    # --- sections ------------------------------------------------------------

    def draw_header(self, screen, y):
        engine = self.engine
        x, right = self.rect.x + PAD, self.rect.right - PAD

        self.text(screen, engine.scenario.get("scenario_name", "-"), x, y, self.title_font)
        self.text(
            screen,
            f"{engine.simulation_elapsed:.0f} / {engine.simulation_time:.0f} sn",
            right, y, self.title_font, align="right",
        )
        y += 32

        controller = "Sabit süre"
        if engine.controller_mode == "adaptive" and engine.controller_version:
            controller = engine.controller_version.get("display_name", "-")
        if self.uses_camera:
            provider = engine.state_provider
            controller += f"   ·   {provider.MODEL_NAME}, tespit {provider.inference_ms:.0f} ms"
        self.text(screen, controller, x, y, self.small_font, MUTED)
        self.text(
            screen, f"hız {engine.playback_speed:g}x", right, y, self.small_font, MUTED,
            align="right",
        )
        return y + 32

    def draw_directions(self, screen, y):
        engine = self.engine
        height = 36 + 24 + 4 * ROW_H + 8
        top = self.card(screen, y, height, "Yönler")
        x = self.rect.x + PAD + INNER
        right = self.rect.right - PAD - INNER

        light_x = x + 150
        count_x = x + 300
        wait_right = right - 80
        crossed_right = right

        count_title = "Araç (kamera)" if self.uses_camera else "Araç"
        self.text(screen, "Yön", x, top, self.small_font, MUTED)
        self.text(screen, "Işık", light_x, top, self.small_font, MUTED)
        self.text(screen, count_title, count_x, top, self.small_font, MUTED)
        self.text(screen, "Bekleme", wait_right, top, self.small_font, MUTED, "right")
        self.text(screen, "Geçen", crossed_right, top, self.small_font, MUTED, "right")
        row_y = top + 24

        current = engine.get_current_green_direction()
        yellow = engine.get_signal_phase_name() == "YELLOW"
        remaining = engine.get_current_signal_remaining()
        upcoming = engine.get_next_green_direction()
        counts = self.counts()

        for direction in DIRECTIONS:
            is_current = direction == current
            pygame.draw.line(screen, LINE, (x, row_y), (right, row_y))
            if is_current and not yellow:
                pygame.draw.rect(
                    screen, ROW_ON,
                    (x - INNER + 1, row_y + 1, right - x + 2 * INNER - 2, ROW_H - 1),
                )
            text_y = row_y + 6

            self.text(screen, APPROACH_NAMES[direction], x, text_y, self.strong_font)
            longest, emergency = self.waiting(direction)
            if emergency:
                self.text(screen, "acil durum aracı", x, text_y + 19, self.small_font, RED)
            elif direction == upcoming and not is_current:
                self.text(screen, "sıradaki", x, text_y + 19, self.small_font, ACCENT)

            if is_current:
                color = YELLOW if yellow else GREEN
                label = f"{'sarı' if yellow else 'yeşil'}  {max(0, int(remaining))} sn"
            else:
                color, label = RED, "kırmızı"
            pygame.draw.circle(screen, color, (light_x + 6, row_y + ROW_H // 2), 6)
            self.text(
                screen, label, light_x + 20, row_y + 13,
                self.strong_font if is_current else self.font,
                color if is_current else MUTED,
            )

            seen, real = counts[direction]
            mismatch = seen != real
            self.text(
                screen, seen, count_x + 22, row_y + 13, self.strong_font,
                YELLOW if mismatch else TEXT, align="right",
            )
            bar = pygame.Rect(count_x + 34, row_y + ROW_H // 2 - 3, 96, 6)
            pygame.draw.rect(screen, BAR, bar, border_radius=3)
            filled = int(bar.width * min(seen, BAR_FULL) / BAR_FULL)
            if filled:
                pygame.draw.rect(
                    screen, GREEN if is_current and not yellow else ACCENT,
                    (bar.x, bar.y, filled, bar.height), border_radius=3,
                )
            if mismatch:
                self.text(screen, f"gerçek {real}", bar.x, row_y + 27, self.small_font, YELLOW)

            self.text(screen, self.seconds(longest), wait_right, row_y + 13, align="right")
            self.text(
                screen, engine.vehicles[direction]["crossed"], crossed_right, row_y + 13,
                self.strong_font, align="right",
            )
            row_y += ROW_H
        return y + height + GAP

    def draw_decision(self, screen, y):
        width = self.rect.width - 2 * PAD - 2 * INNER
        lines = self.wrap(self.last_decision(), width, 3)
        height = 36 + 3 * 22 + 10
        top = self.card(screen, y, height, "Son karar")
        for line in lines:
            self.text(screen, line, self.rect.x + PAD + INNER, top, self.font)
            top += 22
        return y + height + GAP

    def draw_totals(self, screen, y):
        engine = self.engine
        height = 36 + 58
        top = self.card(screen, y, height, "Bu koşu")
        x = self.rect.x + PAD + INNER

        delays = engine.vehicleDelays
        waits = [wait for values in engine.vehicleMetrics.values() for wait in values]
        waits += [self.waiting(direction)[0] for direction in DIRECTIONS]
        emergency_waits = engine.emergencyVehicleMetrics["wait_times"]

        stats = [
            (str(len(delays)), "geçen araç"),
            (self.seconds(sum(delays) / len(delays), 1) if delays else "-", "geçenlerde gecikme"),
            (self.seconds(max(waits)), "en uzun bekleme"),
        ]
        if self.uses_camera:
            share = 100.0 * self.camera_matches / self.camera_checks if self.camera_checks else 0.0
            stats.append((f"%{share:.0f}", "kamera sayımı doğru"))
        else:
            stats.append(
                (
                    self.seconds(sum(emergency_waits) / len(emergency_waits), 1)
                    if emergency_waits
                    else "-",
                    "acil durum beklemesi",
                )
            )

        column_w = (self.rect.width - 2 * PAD - 2 * INNER) // len(stats)
        for i, (value, label) in enumerate(stats):
            self.text(screen, value, x + i * column_w, top, self.value_font)
            self.text(screen, label, x + i * column_w, top + 30, self.small_font, MUTED)
        return y + height + GAP

    def draw_phases(self, screen, y):
        bottom = self.buttons["pause"].top - GAP
        height = bottom - y
        top = self.card(screen, y, height, "Son yeşiller")
        x = self.rect.x + PAD + INNER
        right = self.rect.right - PAD - INNER

        rows = max(1, (bottom - top - 8) // 24)
        history = self.engine.recent_phase_history[-rows:]
        if not history:
            self.text(screen, "Henüz tamamlanan yeşil yok.", x, top, self.small_font, MUTED)
            return

        for phase in reversed(history):
            self.text(screen, f"{phase['time']:.0f}. sn", x, top, self.small_font, MUTED)
            self.text(screen, APPROACH_NAMES[phase["direction"]], x + 70, top, self.small_font)
            self.text(
                screen, f"{phase['actual_green']:.0f} sn yeşil", x + 150, top, self.small_font, MUTED
            )
            self.text(
                screen, f"{phase['vehicles_crossed']} araç geçti", x + 250, top,
                self.small_font, MUTED,
            )
            if phase.get("emergency"):
                self.text(
                    screen, "acil durum önceliği", right, top, self.small_font, RED, "right"
                )
            top += 24

    def draw_buttons(self, screen):
        titles = {
            "pause": "Devam et" if self.engine.paused else "Duraklat",
            "stop": "Durdur",
            "restart": "Yeniden başlat",
        }
        for name, rect in self.buttons.items():
            pygame.draw.rect(screen, BUTTON, rect, border_radius=8)
            pygame.draw.rect(screen, LINE, rect, width=1, border_radius=8)
            surface = self.strong_font.render(titles[name], True, TEXT)
            screen.blit(surface, surface.get_rect(center=rect.center))

    def button_at(self, position):
        for name, rect in self.buttons.items():
            if rect.collidepoint(position):
                return name
        return None

    def draw(self, screen):
        pygame.draw.rect(screen, BG, self.rect)
        pygame.draw.line(screen, LINE, self.rect.topleft, self.rect.bottomleft)

        y = self.rect.y + PAD
        y = self.draw_header(screen, y)
        y = self.draw_directions(screen, y)
        y = self.draw_decision(screen, y)
        y = self.draw_totals(screen, y)
        self.draw_phases(screen, y)
        self.draw_buttons(screen)
