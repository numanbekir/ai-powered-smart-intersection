import copy
import tkinter as tk
from tkinter import ttk, messagebox

import core.i18n as i18n
from core.i18n import t
from core.config_defaults import default_app_state
from core.controller_version_registry import ControllerVersionRegistry
from core.persistence import read_json, write_json
from core.paths import APP_STATE_FILE
from core.result_registry import ResultRegistry
from core.scenario_registry import ScenarioRegistry
from core.state_provider_registry import StateProviderRegistry
from core.test_naming import TestNameGenerator
from simulation.engine import SimulationEngine
from ui.home_tab import HomeTab
from ui.providers_tab import ProvidersTab
from ui.scenarios_tab import ScenariosTab


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1220x980")
        self.root.minsize(1220, 980)

        self.scenario_registry = ScenarioRegistry()
        self.controller_registry = ControllerVersionRegistry()
        self.state_provider_registry = StateProviderRegistry()
        self.result_registry = ResultRegistry()
        self.test_name_generator = TestNameGenerator()
        self.app_state = read_json(APP_STATE_FILE, default_app_state())

        i18n.set_language(self.app_state.get("language", i18n.DEFAULT_LANGUAGE))
        self.root.title(t("app.title"))

        # `set_status`/`status_var` kalici tutuluyor (birçok yerden
        # cagriliyor) ama artik hicbir widget'a bagli degil -- ust
        # bardaki mavi durum metni kaldirildi, yerine dil dropdown'u
        # geldi. Bu, cagiri noktalarina dokunmadan gorsel degisikligi
        # izole ediyor.
        self.status_var = tk.StringVar(value="")
        self.controller_mode_var = tk.StringVar(value="adaptive")
        self.provider_type_var = tk.StringVar(value="ground_truth")
        self.emergency_priority_var = tk.BooleanVar(
            value=self.app_state.get("emergency_priority_enabled", True)
        )
        self.cycle_fairness_var = tk.BooleanVar(
            value=self.app_state.get("cycle_fairness_enabled", True)
        )
        # Varsayilan False: data/controller_versions.json'daki BUTUN kayitli
        # versiyonlar bu korumayi zaten kapali tutuyor (cycle-fairness'in
        # strateji katmaninda saglar hale gelmesiyle gereksizlesti) -- burada
        # varsayilani True yapmak, kullanici hic dokunmasa bile TUM
        # versiyonlarin olculmus/tuned davranisini sessizce degistirirdi.
        self.repeat_guard_var = tk.BooleanVar(
            value=self.app_state.get("repeat_guard_enabled", False)
        )

        self.state_providers = self.state_provider_registry.list_all()

        self.current_scenario = self.resolve_current_scenario()
        self.current_controller_version = self.resolve_current_controller_version()
        self.current_state_provider = self.resolve_current_state_provider()

        if self.current_state_provider:
            self.provider_type_var.set(
                self.current_state_provider.get("provider_type", "ground_truth")
            )

        self.build_ui()

        self.select_scenario(self.current_scenario)
        self.select_controller_version(self.current_controller_version)
        self.select_state_provider(self.current_state_provider)

        self.home_tab.refresh()
        self.providers_tab.refresh()
        self.scenarios_tab.refresh()

    def resolve_current_scenario(self):
        scenario = self.scenario_registry.get_by_id(
            self.app_state.get("selected_scenario_id", "default_scenario")
        )

        if scenario is not None:
            return scenario

        scenarios = self.scenario_registry.list_all()

        if not scenarios:
            raise RuntimeError("No scenarios available.")

        fallback = scenarios[0]
        self.app_state["selected_scenario_id"] = fallback["scenario_id"]
        write_json(APP_STATE_FILE, self.app_state)

        return fallback

    def resolve_current_controller_version(self):
        version = self.controller_registry.get(
            self.app_state.get("selected_controller_version_id", "adaptive_v1")
        )

        if version is not None:
            return version

        versions = self.controller_registry.list_all()

        if not versions:
            return None

        fallback = versions[0]
        self.app_state["selected_controller_version_id"] = fallback["version_id"]
        write_json(APP_STATE_FILE, self.app_state)

        return fallback

    def resolve_current_state_provider(self):
        provider = self.state_provider_registry.get(
            self.app_state.get("selected_state_provider_id", "ground_truth_v1")
        )

        if provider is not None:
            return provider

        fallback = self.get_default_provider_for_type("ground_truth")

        if fallback is not None:
            self.app_state["selected_state_provider_id"] = fallback["provider_id"]
            write_json(APP_STATE_FILE, self.app_state)

        return fallback

    def build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 10))

        self.title_label = ttk.Label(
            header,
            text=t("app.title"),
            font=("Arial", 16, "bold")
        )
        self.title_label.pack(side="left")

        language_box = ttk.Frame(header)
        language_box.pack(side="right")

        self.language_label = ttk.Label(language_box, text=t("app.language_label"))
        self.language_label.pack(side="left", padx=(0, 6))

        self.language_display_var = tk.StringVar(
            value=i18n.LANGUAGE_DISPLAY[i18n.get_language()]
        )
        self.language_combo = ttk.Combobox(
            language_box,
            textvariable=self.language_display_var,
            values=[i18n.LANGUAGE_DISPLAY[code] for code in i18n.LANGUAGES],
            state="readonly",
            width=14
        )
        self.language_combo.pack(side="right")
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_change)

        notebook = ttk.Notebook(main)
        notebook.pack(fill="both", expand=True)

        home_frame = ttk.Frame(notebook)
        scenarios_frame = ttk.Frame(notebook)
        providers_frame = ttk.Frame(notebook)

        self.notebook = notebook
        self.home_frame = home_frame
        self.scenarios_frame = scenarios_frame
        self.providers_frame = providers_frame

        notebook.add(home_frame, text=t("nav.home"))
        notebook.add(scenarios_frame, text=t("nav.scenarios"))
        notebook.add(providers_frame, text=t("nav.providers"))

        self.home_tab = HomeTab(home_frame, self)
        self.scenarios_tab = ScenariosTab(scenarios_frame, self)
        self.providers_tab = ProvidersTab(providers_frame, self)

    def on_language_change(self, _event=None):
        display_value = self.language_display_var.get()
        code = next(
            (c for c, label in i18n.LANGUAGE_DISPLAY.items() if label == display_value),
            i18n.DEFAULT_LANGUAGE
        )

        i18n.set_language(code)
        self.save_app_state()

        self.title_label.config(text=t("app.title"))
        self.root.title(t("app.title"))
        self.language_label.config(text=t("app.language_label"))
        self.notebook.tab(self.home_frame, text=t("nav.home"))
        self.notebook.tab(self.scenarios_frame, text=t("nav.scenarios"))
        self.notebook.tab(self.providers_frame, text=t("nav.providers"))

        self.home_tab.retranslate()
        self.scenarios_tab.retranslate()
        self.providers_tab.retranslate()

        self.home_tab.refresh()
        self.providers_tab.refresh()
        self.scenarios_tab.refresh()

    def get_default_provider_for_type(self, provider_type):
        providers = [
            p for p in self.state_provider_registry.list_all()
            if p.get("provider_type") == provider_type
        ]
        return copy.deepcopy(providers[0]) if providers else None

    def save_app_state(self):
        if not self.current_scenario:
            return

        self.app_state = {
            "selected_scenario_id": self.current_scenario["scenario_id"],
            "selected_controller_version_id": (
                self.current_controller_version["version_id"]
                if self.current_controller_version
                else "adaptive_v1"
            ),
            "selected_state_provider_id": (
                self.current_state_provider["provider_id"]
                if self.current_state_provider
                else "ground_truth_v1"
            ),
            "emergency_priority_enabled": self.emergency_priority_var.get(),
            "cycle_fairness_enabled": self.cycle_fairness_var.get(),
            "repeat_guard_enabled": self.repeat_guard_var.get(),
            "language": i18n.get_language(),
        }
        write_json(APP_STATE_FILE, self.app_state)

    def strategy_toggles_available(self):
        return (
            self.controller_mode_var.get() == "adaptive"
            and self.current_controller_version is not None
        )

    def on_strategy_toggle_change(self):
        self.home_tab.refresh()
        self.save_app_state()

    def build_effective_controller_version(self):
        # Ana ekrandaki emergency/tur-adaleti toggle'lari, secili controller
        # version'in data/controller_versions.json'daki KAYITLI params'ini
        # DEGISTIRMEZ -- sadece bu tek calistirma icin bir kopya uzerinde
        # override edilir (controller_mode_var/provider_type_var'in
        # app_state.json'a yazilip registry'ye yazilmamasiyla ayni desen).
        if not self.current_controller_version:
            return None

        version = copy.deepcopy(self.current_controller_version)
        params = version.setdefault("params", {})
        params["emergency_priority_enabled"] = self.emergency_priority_var.get()
        params["cycle_fairness_enabled"] = self.cycle_fairness_var.get()
        params["controller_repeat_guard_enabled"] = self.repeat_guard_var.get()
        return version

    def set_status(self, text):
        self.status_var.set(text)

    def on_controller_mode_change(self, _event=None):
        self.home_tab.refresh()
        self.save_app_state()
        self.set_status(f"Controller mode selected: {self.controller_mode_var.get()}")

    def on_provider_type_change(self, _event=None):
        provider_type = self.provider_type_var.get()

        current_type = (
            self.current_state_provider.get("provider_type")
            if self.current_state_provider
            else None
        )

        if current_type != provider_type:
            default_provider = self.get_default_provider_for_type(provider_type)
            if default_provider:
                self.select_state_provider(default_provider)

        self.providers_tab.refresh()
        self.home_tab.refresh()
        self.save_app_state()
        self.set_status(f"Provider type selected: {provider_type}")

    def select_state_provider(self, provider):
        if provider is None:
            return

        self.current_state_provider = copy.deepcopy(provider)
        self.provider_type_var.set(
            self.current_state_provider.get("provider_type", "ground_truth")
        )

        self.providers_tab.refresh()
        self.home_tab.refresh()
        self.save_app_state()

        self.set_status(
            f"Selected provider version: {self.current_state_provider['display_name']}"
        )

    def select_scenario(self, scenario):
        if scenario is None:
            scenario = self.resolve_current_scenario()

        self.current_scenario = copy.deepcopy(scenario)

        self.home_tab.refresh()
        self.scenarios_tab.refresh()
        self.save_app_state()

        self.set_status(
            f"Selected scenario: {self.current_scenario['scenario_name']}"
        )

    def select_controller_version(self, version):
        if version is None:
            return

        self.current_controller_version = copy.deepcopy(version)

        self.providers_tab.refresh()
        self.home_tab.refresh()
        self.save_app_state()

        self.set_status(
            f"Selected adaptive version: {self.current_controller_version['display_name']}"
        )

    def start_simulation(self):
        if self.controller_mode_var.get() == "adaptive":
            provider_type = (
                self.current_state_provider.get("provider_type")
                if self.current_state_provider
                else None
            )
            compatible_types = (
                self.current_controller_version.get(
                    "compatible_state_provider_types", []
                )
                if self.current_controller_version
                else []
            )

            if not self.current_controller_version or provider_type not in compatible_types:
                messagebox.showerror(
                    t("app.msg_config_error_title"),
                    t("app.msg_no_compatible_strategy", type=provider_type)
                )
                return

        try:
            test_name = self.test_name_generator.next_name(
                self.current_scenario["scenario_name"]
            )

        except Exception as e:
            messagebox.showerror(t("app.msg_config_error_title"), str(e))
            return

        self.set_status("Simulation is running...")
        self.root.update_idletasks()
        self.root.withdraw()

        try:
            while True:
                engine = SimulationEngine(
                    scenario=self.current_scenario,
                    test_name=test_name,
                    controller_mode=self.controller_mode_var.get(),
                    controller_version=(
                        self.build_effective_controller_version()
                        if self.controller_mode_var.get() == "adaptive"
                        else None
                    ),
                    state_provider_id=(
                        self.current_state_provider["provider_id"]
                        if self.current_state_provider
                        else "ground_truth_v1"
                    ),
                )

                outcome = engine.run()

                if outcome["action"] == "restart":
                    continue

                result = outcome["result"]

                if result is not None:
                    self.result_registry.add(result)

                if outcome["action"] == "finished" and result is not None:
                    self.set_status("Simulation completed")

                else:
                    self.set_status("Simulation stopped")

                break

        except Exception as e:
            self.set_status("Simulation error")
            messagebox.showerror(t("app.msg_simulation_error_title"), str(e))

        finally:
            self.root.deiconify()
            self.home_tab.refresh()
            self.providers_tab.refresh()
            self.scenarios_tab.refresh()