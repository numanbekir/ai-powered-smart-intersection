import tkinter as tk
from tkinter import ttk, messagebox

from core.i18n import t, localized_description


class ProvidersTab:
    def __init__(self, parent, app):
        self.app = app
        self.provider_types = []
        self.strategies = []
        self._static = []

        self.frame = ttk.Frame(parent, padding=10)
        self.frame.pack(fill="both", expand=True)

        self.intro_label = ttk.Label(self.frame, text=t("providers.intro"), foreground="#666666")
        self.intro_label.pack(anchor="w", pady=(0, 10))
        self._static.append((self.intro_label, "providers.intro"))

        top = ttk.Frame(self.frame)
        top.pack(fill="both", expand=True)

        self.left_frame = ttk.LabelFrame(top, text=t("providers.type_frame"), padding=8)
        self.right_frame = ttk.LabelFrame(top, text=t("providers.strategies_frame"), padding=8)
        self._static.append((self.left_frame, "providers.type_frame"))
        self._static.append((self.right_frame, "providers.strategies_frame"))

        self.left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.right_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        self.type_list = tk.Listbox(self.left_frame, height=8, exportselection=False)
        self.type_list.pack(fill="x")
        self.type_list.bind("<<ListboxSelect>>", self.on_type_select)

        type_detail = ttk.Frame(self.left_frame, padding=(4, 12, 4, 4))
        type_detail.pack(fill="both", expand=True)

        self.type_name_label = ttk.Label(
            type_detail, text="-", font=("Arial", 12, "bold"), wraplength=340, justify="left"
        )
        self.type_name_label.pack(anchor="w", pady=(0, 6))

        self.type_status_label = ttk.Label(type_detail, text="-", foreground="#666666")
        self.type_status_label.pack(anchor="w", pady=(0, 8))

        self.type_desc_label = ttk.Label(
            type_detail, text="-", wraplength=340, justify="left", foreground="#333333"
        )
        self.type_desc_label.pack(anchor="w")

        self.strategy_list = tk.Listbox(self.right_frame, height=8, exportselection=False)
        self.strategy_list.pack(fill="x")
        self.strategy_list.bind("<<ListboxSelect>>", self.on_strategy_select)

        strategy_detail = ttk.Frame(self.right_frame, padding=(4, 12, 4, 4))
        strategy_detail.pack(fill="both", expand=True)

        self.strategy_name_label = ttk.Label(
            strategy_detail, text="-", font=("Arial", 12, "bold"), wraplength=340, justify="left"
        )
        self.strategy_name_label.pack(anchor="w", pady=(0, 6))

        self.strategy_status_label = ttk.Label(strategy_detail, text="-", foreground="#666666")
        self.strategy_status_label.pack(anchor="w", pady=(0, 8))

        self.strategy_desc_label = ttk.Label(
            strategy_detail, text="-", wraplength=340, justify="left", foreground="#333333"
        )
        self.strategy_desc_label.pack(anchor="w")

        self.controls_frame = ttk.LabelFrame(self.frame, text=t("providers.actions_frame"), padding=8)
        self.controls_frame.pack(fill="x", pady=(10, 0))
        self._static.append((self.controls_frame, "providers.actions_frame"))

        self.use_button = ttk.Button(
            self.controls_frame, text=t("providers.use_button"), command=self.use_selected_strategy
        )
        self.use_button.pack(side="left", padx=5, pady=5)
        self._static.append((self.use_button, "providers.use_button"))

    def retranslate(self):
        for widget, key in self._static:
            widget.config(text=t(key))
        self.refresh()

    def get_provider_types(self):
        seen = []
        for provider in self.app.state_provider_registry.list_all():
            provider_type = provider.get("provider_type")
            if provider_type not in seen:
                seen.append(provider_type)
        return seen

    def refresh(self):
        self.type_list.delete(0, tk.END)

        self.provider_types = self.get_provider_types()
        current_type = self.app.provider_type_var.get()

        for idx, provider_type in enumerate(self.provider_types):
            is_active = provider_type == current_type
            label = ("✓  " if is_active else "     ") + provider_type
            self.type_list.insert(tk.END, label)
            if is_active:
                self.type_list.itemconfig(
                    idx, {"fg": "#0a6e2f", "selectforeground": "#0a6e2f"}
                )

        if current_type in self.provider_types:
            idx = self.provider_types.index(current_type)
            self.type_list.selection_set(idx)
            self.show_type_detail(current_type)
        elif self.provider_types:
            self.type_list.selection_set(0)
            self.show_type_detail(self.provider_types[0])

        self.refresh_strategies()

    def refresh_strategies(self):
        self.strategy_list.delete(0, tk.END)

        provider_type = self.app.provider_type_var.get()
        self.strategies = self.app.controller_registry.list_by_provider_type(provider_type)

        active_version_id = (
            self.app.current_controller_version.get("version_id")
            if self.app.current_controller_version
            else None
        )

        for idx, version in enumerate(self.strategies):
            is_active = version["version_id"] == active_version_id
            label = ("✓  " if is_active else "     ") + version["display_name"]
            self.strategy_list.insert(tk.END, label)
            if is_active:
                self.strategy_list.itemconfig(
                    idx, {"fg": "#0a6e2f", "selectforeground": "#0a6e2f"}
                )

        if self.app.current_controller_version:
            for idx, version in enumerate(self.strategies):
                if version["version_id"] == self.app.current_controller_version["version_id"]:
                    self.strategy_list.selection_set(idx)
                    self.show_strategy_detail(version)
                    return

        if self.strategies:
            self.strategy_list.selection_set(0)
            self.show_strategy_detail(self.strategies[0])
        else:
            self.show_strategy_detail({
                "message": t("providers.no_compatible_strategy", type=provider_type)
            })

    def get_selected_type(self):
        sel = self.type_list.curselection()
        if not sel:
            return None
        return self.provider_types[sel[0]]

    def get_selected_strategy(self):
        sel = self.strategy_list.curselection()
        if not sel:
            return None
        return self.strategies[sel[0]]

    def on_type_select(self, _event=None):
        provider_type = self.get_selected_type()
        if not provider_type:
            return

        self.show_type_detail(provider_type)

        if provider_type == self.app.provider_type_var.get():
            self.refresh_strategies()
            return

        if not self.app.controller_registry.list_by_provider_type(provider_type):
            # A provider type with no compatible controller cannot be selected:
            # the controller would stay on the old provider type and the run would
            # fail. Restore the previous selection and tell the user why.
            previous_type = self.app.provider_type_var.get()
            self.type_list.selection_clear(0, tk.END)
            if previous_type in self.provider_types:
                self.type_list.selection_set(self.provider_types.index(previous_type))
                self.show_type_detail(previous_type)

            messagebox.showinfo(
                t("providers.msg_not_available_title"),
                t("providers.msg_not_available_body", type=provider_type, previous=previous_type)
            )
            return

        self.app.provider_type_var.set(provider_type)
        self.app.on_provider_type_change()

    def on_strategy_select(self, _event=None):
        version = self.get_selected_strategy()
        if version:
            self.show_strategy_detail(version)

    def show_type_detail(self, provider_type):
        provider = next(
            (
                p for p in self.app.state_provider_registry.list_all()
                if p.get("provider_type") == provider_type
            ),
            None,
        )

        if provider is None:
            self.type_name_label.config(text=provider_type)
            self.type_status_label.config(text="")
            self.type_desc_label.config(text=t("providers.no_provider_for_type"))
            return

        self.type_name_label.config(text=provider.get("display_name", provider_type))
        self.type_status_label.config(text=t("providers.status_prefix", status=provider.get("status", "-")))
        self.type_desc_label.config(text=localized_description(provider, "providers.no_description"))

    def show_strategy_detail(self, version):
        # Tuning parameters are not shown here: this tab explains which rule
        # runs and what it does, it is not a dump of internal settings.
        if "message" in version:
            self.strategy_name_label.config(text="-")
            self.strategy_status_label.config(text="")
            self.strategy_desc_label.config(text=version["message"])
            return

        self.strategy_name_label.config(text=version.get("display_name", "-"))
        self.strategy_status_label.config(text=t("providers.status_prefix", status=version.get("status", "-")))
        self.strategy_desc_label.config(text=localized_description(version, "providers.no_description"))

    def use_selected_strategy(self):
        version = self.get_selected_strategy()
        if not version:
            return

        self.app.select_controller_version(version)

        messagebox.showinfo(
            t("providers.msg_strategy_selected_title"),
            t("providers.msg_strategy_selected_body", name=version["display_name"])
        )
