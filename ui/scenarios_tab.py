import tkinter as tk
from tkinter import ttk, messagebox

from core.i18n import t, localized_description
from ui.scenario_editor_dialog import ScenarioEditorDialog


class ScenariosTab:
    def __init__(self, parent, app):
        self.app = app
        self.scenarios = []
        self._static = []

        self.frame = ttk.Frame(parent, padding=10)
        self.frame.pack(fill="both", expand=True)

        top = ttk.Frame(self.frame)
        top.pack(fill="both", expand=True)

        self.left_frame = ttk.LabelFrame(top, text=t("scenarios.list_frame"), padding=8)
        self.right_frame = ttk.LabelFrame(top, text=t("scenarios.detail_frame"), padding=12)
        self._static.append((self.left_frame, "scenarios.list_frame"))
        self._static.append((self.right_frame, "scenarios.detail_frame"))

        self.left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.right_frame.pack(side="left", fill="y", padx=(5, 0))

        # Fixed size: otherwise the panel resizes with the length of each
        # scenario description and flickers when the selection changes.
        self.right_frame.pack_propagate(False)
        self.right_frame.configure(width=420, height=560)

        self.scenario_list = tk.Listbox(self.left_frame, height=22)
        self.scenario_list.pack(fill="both", expand=True)
        self.scenario_list.bind("<<ListboxSelect>>", self.on_list_select)

        self.detail_name = ttk.Label(
            self.right_frame,
            text="-",
            font=("Arial", 13, "bold"),
            wraplength=390,
            justify="left"
        )
        self.detail_name.pack(anchor="w", fill="x", pady=(0, 10))

        self.detail_text = ttk.Label(
            self.right_frame,
            text="-",
            wraplength=390,
            justify="left",
            foreground="#333333"
        )
        self.detail_text.pack(anchor="w", fill="x")

        self.actions_frame = ttk.LabelFrame(self.frame, text=t("scenarios.actions_frame"), padding=8)
        self.actions_frame.pack(fill="x", pady=(10, 0))
        self._static.append((self.actions_frame, "scenarios.actions_frame"))

        self.use_button = ttk.Button(
            self.actions_frame, text=t("scenarios.use_button"), command=self.use_selected_scenario
        )
        self.use_button.pack(side="left", padx=5)
        self._static.append((self.use_button, "scenarios.use_button"))

        self.reload_button = ttk.Button(
            self.actions_frame, text=t("scenarios.reload_button"), command=self.refresh
        )
        self.reload_button.pack(side="left", padx=5)
        self._static.append((self.reload_button, "scenarios.reload_button"))

        self.delete_button = ttk.Button(
            self.actions_frame, text=t("scenarios.delete_button"), command=self.delete_selected_scenario
        )
        self.delete_button.pack(side="left", padx=5)
        self._static.append((self.delete_button, "scenarios.delete_button"))

        self.new_edit_button = ttk.Button(
            self.actions_frame, text=t("scenarios.new_edit_button"), command=self.open_scenario_editor
        )
        self.new_edit_button.pack(side="left", padx=5)
        self._static.append((self.new_edit_button, "scenarios.new_edit_button"))

        self.hint_label = ttk.Label(self.actions_frame, text=t("scenarios.hint"), foreground="#666666")
        self.hint_label.pack(side="left", padx=12)
        self._static.append((self.hint_label, "scenarios.hint"))

    def retranslate(self):
        for widget, key in self._static:
            widget.config(text=t(key))
        self.refresh()

    def refresh(self):
        self.scenarios = self.app.scenario_registry.list_all()

        self.scenario_list.delete(0, tk.END)

        active_id = (
            self.app.current_scenario.get("scenario_id")
            if self.app.current_scenario
            else None
        )

        for idx, scenario in enumerate(self.scenarios):
            is_active = scenario["scenario_id"] == active_id
            label = ("✓  " if is_active else "     ") + scenario["scenario_name"]
            if scenario.get("is_default"):
                label += t("scenarios.default_suffix")
            self.scenario_list.insert(tk.END, label)

            if is_active:
                self.scenario_list.itemconfig(
                    idx, {"fg": "#0a6e2f", "selectforeground": "#0a6e2f"}
                )

        if self.app.current_scenario:
            for idx, scenario in enumerate(self.scenarios):
                if scenario["scenario_id"] == self.app.current_scenario["scenario_id"]:
                    self.scenario_list.selection_set(idx)
                    self.scenario_list.see(idx)
                    self.show_detail(scenario)
                    return

        if self.scenarios:
            self.scenario_list.selection_set(0)
            self.show_detail(self.scenarios[0])
        else:
            self.show_detail(None)

    def get_selected_scenario(self):
        sel = self.scenario_list.curselection()
        if not sel:
            return None
        return self.scenarios[sel[0]]

    def on_list_select(self, _event=None):
        scenario = self.get_selected_scenario()
        if scenario:
            self.show_detail(scenario)

    def show_detail(self, scenario):
        if not scenario:
            self.detail_name.config(text="-")
            self.detail_text.config(text=t("scenarios.no_scenarios"))
            return

        self.detail_name.config(text=scenario.get("scenario_name", "-"))
        self.detail_text.config(text=localized_description(scenario, "scenarios.no_description"))

    def use_selected_scenario(self):
        scenario = self.get_selected_scenario()
        if not scenario:
            return

        self.app.select_scenario(scenario)
        messagebox.showinfo(
            t("scenarios.msg_selected_title"),
            t("scenarios.msg_selected_body", name=scenario["scenario_name"])
        )

    def delete_selected_scenario(self):
        scenario = self.get_selected_scenario()

        if not scenario:
            return

        if scenario.get("is_default"):
            messagebox.showerror(
                t("scenarios.msg_delete_error_title"), t("scenarios.msg_delete_error_body")
            )
            return

        if messagebox.askyesno(
            t("scenarios.msg_delete_confirm_title"),
            t("scenarios.msg_delete_confirm_body", name=scenario["scenario_name"])
        ):
            self.app.scenario_registry.delete(scenario["scenario_id"])

            default_scenario = self.app.scenario_registry.get_by_id("default_scenario")
            self.app.select_scenario(default_scenario)

            self.refresh()

    def open_scenario_editor(self):
        selected = self.get_selected_scenario()

        def on_saved(scenario):
            self.app.select_scenario(scenario)
            self.refresh()

        ScenarioEditorDialog(self.frame, self.app, selected, on_saved)
