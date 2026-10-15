from tkinter import ttk

from core.i18n import t


class HomeTab:
    def __init__(self, parent, app):
        self.app = app
        self._static = []  # (widget, key) pairs re-applied on language change

        self.frame = ttk.Frame(parent, padding=24)
        self.frame.pack(fill="both", expand=True)

        top = ttk.Frame(self.frame)
        top.pack(fill="x", pady=(0, 18))

        self.title_label = ttk.Label(top, text=t("home.title"), font=("Arial", 20, "bold"))
        self.title_label.pack(anchor="w")
        self._static.append((self.title_label, "home.title"))

        self.subtitle_label = ttk.Label(top, text=t("home.subtitle"), foreground="#555555")
        self.subtitle_label.pack(anchor="w", pady=(6, 0))
        self._static.append((self.subtitle_label, "home.subtitle"))

        # ---- Controller mode: segmented radio pair, not a dropdown -------
        mode_row = ttk.Frame(self.frame)
        mode_row.pack(fill="x", pady=(4, 4))

        self.mode_label = ttk.Label(
            mode_row, text=t("home.controller_mode"), font=("Arial", 10, "bold")
        )
        self.mode_label.pack(side="left", padx=(0, 12))
        self._static.append((self.mode_label, "home.controller_mode"))

        mode_switch = ttk.Frame(mode_row)
        mode_switch.pack(side="left")

        self.fixed_radio = ttk.Radiobutton(
            mode_switch,
            text=t("home.mode_fixed"),
            value="fixed",
            variable=self.app.controller_mode_var,
            command=self.app.on_controller_mode_change
        )
        self.fixed_radio.pack(side="left", ipadx=6)
        self._static.append((self.fixed_radio, "home.mode_fixed"))

        self.adaptive_radio = ttk.Radiobutton(
            mode_switch,
            text=t("home.mode_adaptive"),
            value="adaptive",
            variable=self.app.controller_mode_var,
            command=self.app.on_controller_mode_change
        )
        self.adaptive_radio.pack(side="left", ipadx=6, padx=(10, 0))
        self._static.append((self.adaptive_radio, "home.mode_adaptive"))

        action_box = ttk.Frame(self.frame)
        action_box.pack(fill="x", pady=(12, 18))

        self.start_button = ttk.Button(
            action_box,
            text=t("home.start_button"),
            command=self.app.start_simulation
        )
        self.start_button.pack(ipadx=36, ipady=12)
        self._static.append((self.start_button, "home.start_button"))

        ttk.Separator(self.frame, orient="horizontal").pack(fill="x", pady=(0, 18))

        body = ttk.Frame(self.frame)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)

        # ---- Left column: current selection summary --------------------
        self.summary = ttk.LabelFrame(body, text=t("home.current_selection"), padding=16)
        self.summary.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._static.append((self.summary, "home.current_selection"))

        self.cards_frame = ttk.Frame(self.summary)
        self.cards_frame.pack(fill="x")

        self.cards = {}
        self.card_titles = {}

        card_defs = [
            ("scenario", "home.card_scenario"),
            ("controller", "home.card_controller"),
            ("state_provider", "home.card_state_provider"),
        ]

        for idx, (key, title_key) in enumerate(card_defs):
            card = ttk.Frame(
                self.cards_frame,
                padding=12,
                relief="ridge",
                borderwidth=1
            )
            card.grid(row=0, column=idx, sticky="nsew", padx=6, pady=6)

            title_label = ttk.Label(card, text=t(title_key), font=("Arial", 10, "bold"))
            title_label.pack(anchor="w")
            self.card_titles[key] = title_label
            self._static.append((title_label, title_key))

            value_label = ttk.Label(card, text="-", justify="left", wraplength=180)
            value_label.pack(anchor="w", pady=(6, 0))

            self.cards[key] = value_label
            self.cards_frame.columnconfigure(idx, weight=1)

        self.tip_label = ttk.Label(
            self.summary,
            text=t("home.tip"),
            foreground="#555555",
            justify="left",
            wraplength=460
        )
        self.tip_label.pack(anchor="w", pady=(14, 0))
        self._static.append((self.tip_label, "home.tip"))

        # ---- Right column: strategy options -----------------------------
        self.options = ttk.LabelFrame(body, text=t("home.strategy_options"), padding=16)
        self.options.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._static.append((self.options, "home.strategy_options"))

        self.options_hint = ttk.Label(
            self.options,
            text="",
            foreground="#666666",
            justify="left",
            wraplength=280
        )
        self.options_hint.pack(anchor="w", pady=(0, 10))

        self.emergency_check = ttk.Checkbutton(
            self.options,
            text=t("home.emergency_check"),
            variable=self.app.emergency_priority_var,
            command=lambda: self.app.on_strategy_toggle_change()
        )
        self.emergency_check.pack(anchor="w", pady=(0, 4))
        self._static.append((self.emergency_check, "home.emergency_check"))

        self.emergency_hint_label = ttk.Label(
            self.options, text=t("home.emergency_hint"), foreground="#888888", wraplength=280
        )
        self.emergency_hint_label.pack(anchor="w", pady=(0, 12))
        self._static.append((self.emergency_hint_label, "home.emergency_hint"))

        self.fairness_check = ttk.Checkbutton(
            self.options,
            text=t("home.fairness_check"),
            variable=self.app.cycle_fairness_var,
            command=lambda: self.app.on_strategy_toggle_change()
        )
        self.fairness_check.pack(anchor="w", pady=(0, 4))
        self._static.append((self.fairness_check, "home.fairness_check"))

        self.fairness_hint_label = ttk.Label(
            self.options, text=t("home.fairness_hint"), foreground="#888888", wraplength=280
        )
        self.fairness_hint_label.pack(anchor="w", pady=(0, 12))
        self._static.append((self.fairness_hint_label, "home.fairness_hint"))

    def retranslate(self):
        for widget, key in self._static:
            widget.config(text=t(key))

    def update_strategy_options_state(self):
        available = self.app.strategy_toggles_available()
        state = "normal" if available else "disabled"

        self.emergency_check.configure(state=state)
        self.fairness_check.configure(state=state)

        if available:
            self.options_hint.config(text=t("home.options_available_hint"))
        else:
            self.options_hint.config(text=t("home.options_unavailable_hint"))

    def refresh(self):
        scenario = self.app.current_scenario
        controller = self.app.current_controller_version
        state_provider = self.app.current_state_provider

        scenario_name = scenario.get("scenario_name", "-") if scenario else "-"
        controller_mode = self.app.controller_mode_var.get()
        mode_label = t("home.mode_fixed" if controller_mode == "fixed" else "home.mode_adaptive")
        controller_name = controller.get("display_name", "-") if controller else "-"
        provider_name = state_provider.get("display_name", "-") if state_provider else "-"

        self.cards["scenario"].config(text=scenario_name)

        self.cards["controller"].config(
            text=(
                f"{t('home.card_mode_prefix', mode=mode_label)}\n"
                f"{controller_name}"
            )
        )

        self.cards["state_provider"].config(text=provider_name)

        self.update_strategy_options_state()
