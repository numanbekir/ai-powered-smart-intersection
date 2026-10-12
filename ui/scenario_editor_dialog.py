import json
import tkinter as tk
from tkinter import ttk, messagebox

from core.config_defaults import default_scenario_config
from core.i18n import t

DIRECTIONS = ["right", "down", "left", "up"]
DIRECTION_KEYS = {
    "right": "editor.direction.right",
    "down": "editor.direction.down",
    "left": "editor.direction.left",
    "up": "editor.direction.up",
}
VEHICLE_TYPES = ["car", "bus", "truck", "bike"]
SPEED_VEHICLE_TYPES = ["car", "bus", "truck", "bike", "ambulance", "police", "firetruck"]
EMERGENCY_VEHICLE_TYPES = ["ambulance", "police", "firetruck"]
VEHICLE_TYPE_KEY = "editor.vehicle_type.{}"


class ScenarioEditorDialog:
    """New/Edit Scenario window: config grouped into meaningful tabs
    (General, Traffic, Vehicle Mix, Vehicle Speeds, Turns, Fixed-Time,
    Emergency) instead of one raw JSON blob. `lane_turn_policy` is not
    exposed -- it is identical across all 22 shipped scenarios (a
    structural invariant, not a per-scenario tuning knob) and is carried
    forward unchanged from the seed config.

    This dialog is modal (grab_set) and one-shot -- it does not need to
    react to a language change while open, since the language dropdown
    lives on the (blocked) main window. Labels are simply built with the
    language active at open time.
    """

    def __init__(self, parent_widget, app, selected_scenario, on_saved):
        self.app = app
        self.selected_scenario = selected_scenario
        self.on_saved = on_saved
        self.seed_config = (
            selected_scenario["config"] if selected_scenario else default_scenario_config()
        )
        self.vars = {}

        self.dialog = tk.Toplevel(parent_widget)
        self.dialog.title(t("editor.window_title"))
        self.dialog.geometry("760x640")
        self.dialog.minsize(680, 520)

        self._build(parent_widget)

    def _build(self, parent_widget):
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_basic_info_tab(notebook)
        self._build_general_tab(notebook)
        self._build_traffic_tab(notebook)
        self._build_vehicle_mix_tab(notebook)
        self._build_vehicle_speeds_tab(notebook)
        self._build_turns_tab(notebook)
        self._build_fixed_time_tab(notebook)
        self._build_emergency_tab(notebook)
        preview_frame, preview_text = self._build_preview_tab(notebook)

        notebook.bind(
            "<<NotebookTabChanged>>",
            lambda _e: self._refresh_preview_if_active(notebook, preview_frame, preview_text)
        )

        buttons = ttk.Frame(self.dialog)
        buttons.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(buttons, text=t("editor.cancel_button"), command=self._close).pack(
            side="right", padx=5
        )
        ttk.Button(buttons, text=t("editor.save_button"), command=self._save).pack(
            side="right", padx=5
        )

        self.dialog.protocol("WM_DELETE_WINDOW", self._close)

        # SIRALAMA onemli: `grab_set()` pencere henuz viewable olmadan
        # cagrilirsa Tk "grab failed: window not viewable" hatasi verir.
        # Once tum widget'lar kuruluyor, `update_idletasks()` ile pencere
        # gercekten cizildikten SONRA transient/topmost/grab_set uygulanir.
        self.dialog.update_idletasks()
        self.dialog.transient(parent_widget.winfo_toplevel())
        self.dialog.attributes("-topmost", True)
        try:
            self.dialog.grab_set()
        except tk.TclError:
            pass
        self.dialog.focus_force()

    # ---- helpers ---------------------------------------------------------

    def _entry_row(self, parent, row, label, value, key, width=14):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
        var = tk.StringVar(value=str(value))
        ttk.Entry(parent, textvariable=var, width=width).grid(
            row=row, column=1, sticky="w", padx=6, pady=4
        )
        self.vars[key] = var
        return var

    def _check_row(self, parent, row, col, label, value, key):
        var = tk.BooleanVar(value=bool(value))
        ttk.Checkbutton(parent, text=label, variable=var).grid(
            row=row, column=col, sticky="w", padx=6, pady=4
        )
        self.vars[key] = var
        return var

    @staticmethod
    def _get_float(vars_dict, key, default=0.0):
        try:
            return float(vars_dict[key].get())
        except (KeyError, ValueError):
            return default

    @staticmethod
    def _get_int(vars_dict, key, default=0):
        try:
            return int(float(vars_dict[key].get()))
        except (KeyError, ValueError):
            return default

    # ---- tabs --------------------------------------------------------

    def _build_basic_info_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text=t("editor.tab_basic_info"))

        ttk.Label(tab, text=t("editor.field.scenario_name")).grid(
            row=0, column=0, sticky="w", padx=6, pady=6
        )
        self.name_var = tk.StringVar(
            value=self.selected_scenario.get("scenario_name", "") if self.selected_scenario else ""
        )
        ttk.Entry(tab, textvariable=self.name_var, width=50).grid(
            row=0, column=1, sticky="w", padx=6, pady=6
        )

        ttk.Label(tab, text=t("editor.field.description")).grid(
            row=1, column=0, sticky="nw", padx=6, pady=6
        )
        self.desc_text = tk.Text(tab, width=44, height=6, wrap="word")
        self.desc_text.grid(row=1, column=1, sticky="w", padx=6, pady=6)
        self.desc_text.insert(
            "1.0",
            self.selected_scenario.get("description", "") if self.selected_scenario else ""
        )

        ttk.Label(
            tab,
            text=t("editor.basic_info_hint"),
            foreground="#666666",
            wraplength=480,
            justify="left"
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=(14, 0))

    def _build_general_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text=t("editor.tab_general"))
        cfg = self.seed_config

        self._entry_row(tab, 0, t("editor.field.simulation_time"), cfg.get("simulation_time", 120), "simulation_time")
        self._entry_row(tab, 1, t("editor.field.spawn_interval"), cfg.get("spawn_interval", 1.63), "spawn_interval")
        self._entry_row(tab, 2, t("editor.field.playback_speed"), cfg.get("playback_speed", 1.0), "playback_speed")
        self._entry_row(tab, 3, t("editor.field.random_seed"), cfg.get("random_seed", 42), "random_seed")
        self._entry_row(tab, 4, t("editor.field.fps"), cfg.get("fps", 60), "fps")

        ttk.Label(
            tab,
            text=t("editor.general_hint"),
            foreground="#666666",
            wraplength=480,
            justify="left"
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=6, pady=(14, 0))

    def _build_traffic_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text=t("editor.tab_traffic"))
        cfg = self.seed_config

        density_box = ttk.LabelFrame(tab, text=t("editor.direction_density_frame"), padding=10)
        density_box.pack(fill="x", pady=(0, 14))

        density = cfg.get("direction_density", {})
        for idx, direction in enumerate(DIRECTIONS):
            self._entry_row(
                density_box, idx, t(DIRECTION_KEYS[direction]),
                density.get(direction, 25), f"direction_density.{direction}", width=10
            )

        types_box = ttk.LabelFrame(tab, text=t("editor.allowed_types_frame"), padding=10)
        types_box.pack(fill="x")

        allowed = cfg.get("allowed_vehicle_types", {})
        for idx, vtype in enumerate(VEHICLE_TYPES):
            self._check_row(
                types_box, 0, idx, t(VEHICLE_TYPE_KEY.format(vtype)),
                allowed.get(vtype, vtype != "bike"), f"allowed_vehicle_types.{vtype}"
            )

    def _build_vehicle_mix_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text=t("editor.tab_vehicle_mix"))

        ttk.Label(
            tab,
            text=t("editor.vehicle_mix_hint"),
            foreground="#666666",
            wraplength=560,
            justify="left"
        ).pack(anchor="w", pady=(0, 10))

        grid = ttk.Frame(tab)
        grid.pack(fill="both", expand=True)

        distribution = self.seed_config.get("road_vehicle_distribution", {})

        for idx, direction in enumerate(DIRECTIONS):
            row, col = idx // 2, idx % 2
            box = ttk.LabelFrame(grid, text=t(DIRECTION_KEYS[direction]), padding=10)
            box.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
            grid.columnconfigure(col, weight=1)

            dir_dist = distribution.get(direction, {})
            for vidx, vtype in enumerate(VEHICLE_TYPES):
                self._entry_row(
                    box, vidx, t(VEHICLE_TYPE_KEY.format(vtype)), dir_dist.get(vtype, 0),
                    f"road_vehicle_distribution.{direction}.{vtype}", width=8
                )

    def _build_vehicle_speeds_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text=t("editor.tab_vehicle_speeds"))
        speeds = self.seed_config.get("vehicle_speeds", {})

        for idx, vtype in enumerate(SPEED_VEHICLE_TYPES):
            self._entry_row(
                tab, idx, t(VEHICLE_TYPE_KEY.format(vtype)), speeds.get(vtype, 1.0),
                f"vehicle_speeds.{vtype}", width=10
            )

    def _build_turns_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text=t("editor.tab_turns"))
        cfg = self.seed_config

        self._entry_row(
            tab, 0, t("editor.field.left_turn_probability"), cfg.get("left_turn_probability", 0.25),
            "left_turn_probability", width=10
        )
        self._entry_row(
            tab, 1, t("editor.field.right_turn_probability"), cfg.get("right_turn_probability", 0.25),
            "right_turn_probability", width=10
        )

        ttk.Label(
            tab,
            text=t("editor.turns_hint"),
            foreground="#666666",
            wraplength=480,
            justify="left"
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=(14, 0))

    def _build_fixed_time_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text=t("editor.tab_fixed_time"))
        fixed = self.seed_config.get("fixed", {})

        ttk.Label(tab, text=t("editor.field.initial_green")).grid(
            row=0, column=0, sticky="w", padx=6, pady=4
        )
        self.initial_green_var = tk.StringVar(value=fixed.get("initial_green", "right"))
        ttk.Combobox(
            tab, textvariable=self.initial_green_var, values=DIRECTIONS,
            state="readonly", width=12
        ).grid(row=0, column=1, sticky="w", padx=6, pady=4)

        self._entry_row(tab, 1, t("editor.field.green_time"), fixed.get("green_time", 10), "fixed.green_time")
        self._entry_row(tab, 2, t("editor.field.yellow_time"), fixed.get("yellow_time", 3), "fixed.yellow_time")
        self._entry_row(tab, 3, t("editor.field.red_time"), fixed.get("red_time", 50), "fixed.red_time")

    def _build_emergency_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text=t("editor.tab_emergency"))
        emergency = self.seed_config.get("emergency", {})

        self.emergency_enabled_var = tk.BooleanVar(value=bool(emergency.get("enabled", False)))
        ttk.Checkbutton(
            tab, text=t("editor.emergency_enabled_check"),
            variable=self.emergency_enabled_var
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 10))

        types_box = ttk.LabelFrame(tab, text=t("editor.emergency_types_frame"), padding=10)
        types_box.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 10))

        vehicle_types = emergency.get("vehicle_types", {})
        for idx, vtype in enumerate(EMERGENCY_VEHICLE_TYPES):
            self._check_row(
                types_box, 0, idx, t(VEHICLE_TYPE_KEY.format(vtype)),
                vehicle_types.get(vtype, True), f"emergency.vehicle_types.{vtype}"
            )

        self._entry_row(
            tab, 2, t("editor.field.spawn_probability"), emergency.get("spawn_probability", 0.03),
            "emergency.spawn_probability", width=10
        )
        self._entry_row(
            tab, 3, t("editor.field.min_spawn_gap"), emergency.get("min_spawn_gap", 20),
            "emergency.min_spawn_gap", width=10
        )
        self._entry_row(
            tab, 4, t("editor.field.max_active_emergency"), emergency.get("max_active_emergency", 1),
            "emergency.max_active_emergency", width=10
        )

        self.emergency_priority_enabled_var = tk.BooleanVar(
            value=bool(emergency.get("priority_enabled", True))
        )
        ttk.Checkbutton(
            tab, text=t("editor.emergency_priority_check"),
            variable=self.emergency_priority_enabled_var
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=6, pady=(6, 4))

        self._entry_row(
            tab, 6, t("editor.field.priority_green_time"), emergency.get("priority_green_time", 12),
            "emergency.priority_green_time", width=10
        )

    def _build_preview_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text=t("editor.tab_preview"))

        ttk.Label(
            tab,
            text=t("editor.preview_hint"),
            foreground="#666666",
            wraplength=560,
            justify="left"
        ).pack(anchor="w", pady=(0, 8))

        text_frame = ttk.Frame(tab)
        text_frame.pack(fill="both", expand=True)

        preview_text = tk.Text(text_frame, wrap="none", state="disabled")
        preview_text.pack(fill="both", expand=True)

        return tab, preview_text

    def _refresh_preview_if_active(self, notebook, preview_frame, preview_text):
        try:
            current = notebook.select()
        except tk.TclError:
            return

        if current != str(preview_frame):
            return

        try:
            cfg = self._build_config()
        except Exception as e:
            cfg = {"error": str(e)}

        preview_text.config(state="normal")
        preview_text.delete("1.0", tk.END)
        preview_text.insert("1.0", json.dumps(cfg, indent=2, ensure_ascii=False))
        preview_text.config(state="disabled")

    # ---- save/close --------------------------------------------------

    def _build_config(self):
        v = self.vars

        config = {
            "fps": self._get_int(v, "fps", self.seed_config.get("fps", 60)),
            "simulation_time": self._get_int(
                v, "simulation_time", self.seed_config.get("simulation_time", 120)
            ),
            "playback_speed": self._get_float(
                v, "playback_speed", self.seed_config.get("playback_speed", 1.0)
            ),
            "spawn_interval": self._get_float(
                v, "spawn_interval", self.seed_config.get("spawn_interval", 1.63)
            ),
            "random_seed": self._get_int(
                v, "random_seed", self.seed_config.get("random_seed", 42)
            ),
            "allowed_vehicle_types": {
                vtype: bool(v[f"allowed_vehicle_types.{vtype}"].get())
                for vtype in VEHICLE_TYPES
            },
            "vehicle_speeds": {
                vtype: self._get_float(v, f"vehicle_speeds.{vtype}", 1.0)
                for vtype in SPEED_VEHICLE_TYPES
            },
            "direction_density": {
                direction: self._get_int(v, f"direction_density.{direction}", 25)
                for direction in DIRECTIONS
            },
            "road_vehicle_distribution": {
                direction: {
                    vtype: self._get_float(
                        v, f"road_vehicle_distribution.{direction}.{vtype}", 0
                    )
                    for vtype in VEHICLE_TYPES
                }
                for direction in DIRECTIONS
            },
            # Butun senaryolarda ayni (bkz. Turns sekmesindeki not) --
            # form'da duzenlenmiyor, seed config'ten (ya da varsayilandan)
            # oldugu gibi tasiniyor.
            "lane_turn_policy": self.seed_config.get(
                "lane_turn_policy", default_scenario_config()["lane_turn_policy"]
            ),
            "left_turn_probability": self._get_float(v, "left_turn_probability", 0.25),
            "right_turn_probability": self._get_float(v, "right_turn_probability", 0.25),
            "fixed": {
                "initial_green": self.initial_green_var.get(),
                "green_time": self._get_int(v, "fixed.green_time", 10),
                "yellow_time": self._get_int(v, "fixed.yellow_time", 3),
                "red_time": self._get_int(v, "fixed.red_time", 50),
            },
            "emergency": {
                "enabled": bool(self.emergency_enabled_var.get()),
                "vehicle_types": {
                    vtype: bool(v[f"emergency.vehicle_types.{vtype}"].get())
                    for vtype in EMERGENCY_VEHICLE_TYPES
                },
                "spawn_probability": self._get_float(v, "emergency.spawn_probability", 0.03),
                "min_spawn_gap": self._get_int(v, "emergency.min_spawn_gap", 20),
                "max_active_emergency": self._get_int(v, "emergency.max_active_emergency", 1),
                "priority_enabled": bool(self.emergency_priority_enabled_var.get()),
                "priority_green_time": self._get_int(v, "emergency.priority_green_time", 12),
            },
        }

        return config

    def _close(self):
        self.dialog.grab_release()
        self.dialog.destroy()

    def _save(self):
        name = self.name_var.get().strip()

        if not name:
            messagebox.showerror(t("editor.msg_error_title"), t("editor.msg_name_empty"))
            return

        try:
            config = self._build_config()
        except Exception as e:
            messagebox.showerror(t("editor.msg_error_title"), t("editor.msg_invalid_value", error=e))
            return

        try:
            scenario = self.app.scenario_registry.create_or_update(
                scenario_name=name,
                description=self.desc_text.get("1.0", tk.END).strip(),
                config=config,
                is_locked=True,
            )

            self.on_saved(scenario)
            self._close()

            messagebox.showinfo(
                t("editor.msg_saved_title"), t("editor.msg_saved_body", name=scenario["scenario_name"])
            )

        except Exception as e:
            messagebox.showerror(t("editor.msg_error_title"), str(e))
