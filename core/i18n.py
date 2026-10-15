"""UI translations: the Tkinter control center (Home/Scenarios/Providers
tabs, scenario editor), the pygame simulation window and the decision
explanations written by the adaptive controller. English is the default.

Scenario/controller-version/state-provider `display_name` and
`scenario_name` are NOT translated: they double as lookup keys
(`ScenarioRegistry.get_by_name`, duplicate detection on save) and as
stable identifiers referenced elsewhere, so changing them per-language
would be a functional risk, not just cosmetic. Only prose `description`
fields (via a parallel `description_tr` field) and UI chrome
(labels/buttons/hints/messages) are translated.
"""

DEFAULT_LANGUAGE = "en"
LANGUAGES = ["en", "tr"]
LANGUAGE_DISPLAY = {
    "en": "EN - English",
    "tr": "TR - Türkçe",
}

_current_language = DEFAULT_LANGUAGE

TRANSLATIONS = {
    "en": {
        "app.title": "AI-Powered Smart Intersection",
        "app.language_label": "Language",
        "app.msg_config_error_title": "Config Error",
        "app.msg_no_compatible_strategy": "No strategy is compatible with the current provider "
                                           "type ('{type}'). Pick a provider type that has a "
                                           "compatible strategy on the Providers tab first.",
        "app.msg_simulation_error_title": "Simulation Error",
        "nav.home": "Home",
        "nav.scenarios": "Scenarios",
        "nav.providers": "Providers",

        "home.title": "Simulation Launcher",
        "home.subtitle": "Start a simulation with the currently selected scenario, "
                          "controller mode, and strategy.",
        "home.controller_mode": "Controller Mode",
        "home.mode_fixed": "Fixed",
        "home.mode_adaptive": "Adaptive",
        "home.start_button": "▶  Start Simulation",
        "home.current_selection": "Current Selection",
        "home.card_scenario": "Scenario",
        "home.card_controller": "Controller",
        "home.card_state_provider": "State Provider",
        "home.card_mode_prefix": "Mode: {mode}",
        "home.tip": "Tip: State Provider determines what the adaptive controller can observe. "
                    "Use Ground Truth for ideal tests and YOLO for camera-like, limited-visibility tests.",
        "home.strategy_options": "Strategy Options",
        "home.emergency_check": "Emergency priority enabled",
        "home.emergency_hint": "When off, emergency vehicles get no special treatment.",
        "home.fairness_check": "Turn fairness enabled (tur adaleti)",
        "home.fairness_hint": "When off, direction choice always follows the raw score, "
                               "without guaranteeing every active direction a turn first.",
        "home.options_available_hint": "Applies to this run only -- the saved controller "
                                        "version is unchanged.",
        "home.options_unavailable_hint": "Only available in adaptive mode with a selected strategy.",

        "scenarios.list_frame": "Scenario List",
        "scenarios.detail_frame": "Selected Scenario",
        "scenarios.use_button": "Use Selected Scenario",
        "scenarios.reload_button": "Reload List",
        "scenarios.delete_button": "Delete Selected Scenario",
        "scenarios.new_edit_button": "New / Edit Scenario",
        "scenarios.actions_frame": "Scenario Actions",
        "scenarios.hint": "Saving a new/edited scenario keeps it as-is for consistency across runs.",
        "scenarios.default_suffix": "  [default]",
        "scenarios.no_scenarios": "No scenarios found.",
        "scenarios.no_description": "No description available.",
        "scenarios.msg_selected_title": "Scenario Selected",
        "scenarios.msg_selected_body": "Active scenario: {name}",
        "scenarios.msg_delete_confirm_title": "Confirm",
        "scenarios.msg_delete_confirm_body": "Delete scenario '{name}'?",
        "scenarios.msg_delete_error_title": "Delete Error",
        "scenarios.msg_delete_error_body": "Default scenario cannot be deleted.",

        "providers.intro": "Select a provider type on the left; strategies compatible "
                            "with it appear on the right.",
        "providers.type_frame": "Provider Type",
        "providers.strategies_frame": "Compatible Strategies",
        "providers.actions_frame": "Strategy Actions",
        "providers.use_button": "Use Selected Strategy",
        "providers.status_prefix": "Status: {status}",
        "providers.no_provider_for_type": "No provider registered for this type.",
        "providers.no_description": "No description available.",
        "providers.no_compatible_strategy": "No strategies are compatible with provider type: {type}",
        "providers.msg_strategy_selected_title": "Strategy Selected",
        "providers.msg_strategy_selected_body": "Active adaptive strategy: {name}",
        "providers.msg_not_available_title": "Not yet available",
        "providers.msg_not_available_body": "'{type}' has no compatible strategy yet, so it "
                                             "can't be selected as the active provider type. "
                                             "Staying on '{previous}'.",

        "editor.window_title": "New / Edit Scenario",
        "editor.tab_basic_info": "Basic Info",
        "editor.tab_general": "General",
        "editor.tab_traffic": "Traffic Density",
        "editor.tab_vehicle_mix": "Vehicle Mix",
        "editor.tab_vehicle_speeds": "Vehicle Speeds",
        "editor.tab_turns": "Turns",
        "editor.tab_fixed_time": "Fixed-Time",
        "editor.tab_emergency": "Emergency",
        "editor.tab_preview": "Advanced (JSON preview)",
        "editor.cancel_button": "Cancel",
        "editor.save_button": "Save Scenario",
        "editor.field.scenario_name": "Scenario Name",
        "editor.field.description": "Description",
        "editor.basic_info_hint": "Fine-grained values (traffic density, vehicle mix, speeds, "
                                   "turns, fixed-time, emergency) are on the tabs above.",
        "editor.field.simulation_time": "Simulation Time (s)",
        "editor.field.spawn_interval": "Spawn Interval (s)",
        "editor.field.playback_speed": "Playback Speed",
        "editor.field.random_seed": "Random Seed",
        "editor.field.fps": "FPS",
        "editor.general_hint": "Spawn interval controls demand density (v/c) -- see "
                                "docs/scenario_capacity_calibration.md before changing it.",
        "editor.direction_density_frame": "Direction Density (relative weight)",
        "editor.allowed_types_frame": "Allowed Vehicle Types",
        "editor.direction.right": "Right",
        "editor.direction.down": "Down",
        "editor.direction.left": "Left",
        "editor.direction.up": "Up",
        "editor.vehicle_type.car": "Car",
        "editor.vehicle_type.bus": "Bus",
        "editor.vehicle_type.truck": "Truck",
        "editor.vehicle_type.bike": "Bike",
        "editor.vehicle_type.ambulance": "Ambulance",
        "editor.vehicle_type.police": "Police",
        "editor.vehicle_type.firetruck": "Firetruck",
        "editor.vehicle_mix_hint": "Per-direction vehicle type mix (percentages, need not sum "
                                    "to 100 -- used as relative weights).",
        "editor.field.left_turn_probability": "Left Turn Probability",
        "editor.field.right_turn_probability": "Right Turn Probability",
        "editor.turns_hint": "Lane turn policy (which lane allows which turns) is a fixed "
                              "structural setting, identical across every scenario, and is "
                              "not edited here.",
        "editor.field.initial_green": "Initial Green Direction",
        "editor.field.green_time": "Green Time (s)",
        "editor.field.yellow_time": "Yellow Time (s)",
        "editor.field.red_time": "Red Time (s)",
        "editor.emergency_enabled_check": "Emergency vehicles enabled for this scenario",
        "editor.emergency_types_frame": "Emergency Vehicle Types",
        "editor.field.spawn_probability": "Spawn Probability",
        "editor.field.min_spawn_gap": "Min Spawn Gap (s)",
        "editor.field.max_active_emergency": "Max Active Emergency",
        "editor.emergency_priority_check": "Priority handling enabled",
        "editor.field.priority_green_time": "Priority Green Time (s)",
        "editor.preview_hint": "Read-only preview of the resulting config, generated from "
                                "the tabs above. Refreshes when you open this tab.",
        "editor.msg_error_title": "Scenario Error",
        "editor.msg_name_empty": "Scenario name cannot be empty.",
        "editor.msg_invalid_value": "Invalid value: {error}",
        "editor.msg_saved_title": "Saved",
        "editor.msg_saved_body": "Scenario saved: {name}",
        # Simulation window (pygame) and decision explanations
        "sim.approach.right": "West",
        "sim.approach.down": "North",
        "sim.approach.left": "East",
        "sim.approach.up": "South",
        "sim.signal.right": "WEST",
        "sim.signal.down": "NORTH",
        "sim.signal.left": "EAST",
        "sim.signal.up": "SOUTH",
        "sim.reason.emergency": "{approach} gets a {green} s green: an emergency vehicle is "
                                "{distance} px from the stop line with {ahead} vehicles ahead of it.",
        "sim.reason.no_demand": "No vehicles on any approach, the green stays on {approach}.",
        "sim.reason.normal": "{approach} gets a {green} s green. It had {count} vehicles and had "
                             "been red for {red} s.{note}",
        "sim.reason.fairness_note": " It was its turn in the cycle.",
        "sim.reason.hold": "Green on {approach} extended by {extension} s so the emergency "
                           "vehicle can cross.",
        "sim.reason.preempt": "Green on {approach} cut after {elapsed} s: an emergency vehicle "
                              "is coming from another approach.",
        "sim.reason.keep_green": "No vehicles on the other approaches, the green stays on {approach}.",
        "sim.reason.fixed": "Fixed time: each approach gets a {green} s green in turn.",
        "sim.seconds": "{value} s",
        "sim.percent": "{value}%",
        "sim.header.time": "{elapsed} / {total} s",
        "sim.header.fixed": "Fixed time",
        "sim.header.detection": "{model}, detection {ms} ms",
        "sim.header.speed": "speed {speed}x",
        "sim.card.approaches": "Approaches",
        "sim.card.decision": "Last decision",
        "sim.card.totals": "This run",
        "sim.card.phases": "Recent greens",
        "sim.col.approach": "Approach",
        "sim.col.signal": "Signal",
        "sim.col.vehicles": "Vehicles",
        "sim.col.vehicles_camera": "Vehicles (camera)",
        "sim.col.wait": "Wait",
        "sim.col.crossed": "Crossed",
        "sim.row.emergency": "emergency vehicle",
        "sim.row.next": "next",
        "sim.light.green": "green  {remaining} s",
        "sim.light.yellow": "yellow  {remaining} s",
        "sim.light.red": "red",
        "sim.row.actual": "actual {count}",
        "sim.stat.crossed": "vehicles crossed",
        "sim.stat.delay": "avg delay",
        "sim.stat.longest_wait": "longest wait",
        "sim.stat.camera_correct": "camera count correct",
        "sim.stat.emergency_wait": "emergency wait",
        "sim.phase.time": "{time} s",
        "sim.phase.green": "{green} s green",
        "sim.phase.crossed": "{count} crossed",
        "sim.phase.emergency": "emergency priority",
        "sim.phase.none": "No completed greens yet.",
        "sim.button.pause": "Pause",
        "sim.button.resume": "Resume",
        "sim.button.stop": "Stop",
        "sim.button.restart": "Restart",
        "sim.paused": "PAUSED",
    },
    "tr": {
        "app.title": "AI-Powered Smart Intersection",
        "app.language_label": "Dil",
        "app.msg_config_error_title": "Yapılandırma Hatası",
        "app.msg_no_compatible_strategy": "Şu anki provider type ('{type}') ile uyumlu strateji "
                                           "yok. Önce Providers sekmesinden uyumlu bir provider "
                                           "type seç.",
        "app.msg_simulation_error_title": "Simülasyon Hatası",
        "nav.home": "Ana Sayfa",
        "nav.scenarios": "Senaryolar",
        "nav.providers": "Providers",

        "home.title": "Simülasyon Başlatıcı",
        "home.subtitle": "Şu an seçili senaryo, kontrolcü modu ve strateji ile bir "
                          "simülasyon başlat.",
        "home.controller_mode": "Kontrolcü Modu",
        "home.mode_fixed": "Sabit",
        "home.mode_adaptive": "Adaptif",
        "home.start_button": "▶  Simülasyonu Başlat",
        "home.current_selection": "Mevcut Seçim",
        "home.card_scenario": "Senaryo",
        "home.card_controller": "Kontrolcü",
        "home.card_state_provider": "State Provider",
        "home.card_mode_prefix": "Mod: {mode}",
        "home.tip": "İpucu: State Provider, adaptif kontrolcünün neyi gözlemleyebildiğini "
                    "belirler. İdeal testler için Ground Truth, kamera benzeri kısıtlı "
                    "görünürlük testleri için YOLO kullan.",
        "home.strategy_options": "Strateji Seçenekleri",
        "home.emergency_check": "Acil durum önceliği aktif",
        "home.emergency_hint": "Kapalıyken acil durum araçları hiçbir özel muamele görmez.",
        "home.fairness_check": "Tur adaleti aktif",
        "home.fairness_hint": "Kapalıyken yön seçimi her zaman ham skora göre yapılır, "
                               "her aktif yönün önce sırasını alması garanti edilmez.",
        "home.options_available_hint": "Yalnızca bu çalıştırma için geçerli -- kayıtlı "
                                        "kontrolcü versiyonu değişmez.",
        "home.options_unavailable_hint": "Yalnızca adaptif modda ve bir strateji seçiliyken kullanılabilir.",

        "scenarios.list_frame": "Senaryo Listesi",
        "scenarios.detail_frame": "Seçili Senaryo",
        "scenarios.use_button": "Seçili Senaryoyu Kullan",
        "scenarios.reload_button": "Listeyi Yenile",
        "scenarios.delete_button": "Seçili Senaryoyu Sil",
        "scenarios.new_edit_button": "Yeni / Düzenle",
        "scenarios.actions_frame": "Senaryo İşlemleri",
        "scenarios.hint": "Yeni/düzenlenmiş bir senaryoyu kaydetmek, koşular arasında "
                           "tutarlılık için onu olduğu gibi korur.",
        "scenarios.default_suffix": "  [varsayılan]",
        "scenarios.no_scenarios": "Senaryo bulunamadı.",
        "scenarios.no_description": "Açıklama yok.",
        "scenarios.msg_selected_title": "Senaryo Seçildi",
        "scenarios.msg_selected_body": "Aktif senaryo: {name}",
        "scenarios.msg_delete_confirm_title": "Onay",
        "scenarios.msg_delete_confirm_body": "'{name}' senaryosu silinsin mi?",
        "scenarios.msg_delete_error_title": "Silme Hatası",
        "scenarios.msg_delete_error_body": "Varsayılan senaryo silinemez.",

        "providers.intro": "Soldan bir provider type seç; ona uyumlu stratejiler sağda görünür.",
        "providers.type_frame": "Provider Type",
        "providers.strategies_frame": "Uyumlu Stratejiler",
        "providers.actions_frame": "Strateji İşlemleri",
        "providers.use_button": "Seçili Stratejiyi Kullan",
        "providers.status_prefix": "Durum: {status}",
        "providers.no_provider_for_type": "Bu tip için kayıtlı bir provider yok.",
        "providers.no_description": "Açıklama yok.",
        "providers.no_compatible_strategy": "Şu provider type ile uyumlu strateji yok: {type}",
        "providers.msg_strategy_selected_title": "Strateji Seçildi",
        "providers.msg_strategy_selected_body": "Aktif adaptif strateji: {name}",
        "providers.msg_not_available_title": "Henüz kullanılamaz",
        "providers.msg_not_available_body": "'{type}' için henüz uyumlu bir strateji yok, bu "
                                             "yüzden aktif provider type olarak seçilemez. "
                                             "'{previous}' üzerinde kalınıyor.",

        "editor.window_title": "Yeni / Senaryo Düzenle",
        "editor.tab_basic_info": "Temel Bilgi",
        "editor.tab_general": "Genel",
        "editor.tab_traffic": "Trafik Yoğunluğu",
        "editor.tab_vehicle_mix": "Araç Karışımı",
        "editor.tab_vehicle_speeds": "Araç Hızları",
        "editor.tab_turns": "Dönüşler",
        "editor.tab_fixed_time": "Sabit Süreli",
        "editor.tab_emergency": "Acil Durum",
        "editor.tab_preview": "Gelişmiş (JSON önizleme)",
        "editor.cancel_button": "İptal",
        "editor.save_button": "Senaryoyu Kaydet",
        "editor.field.scenario_name": "Senaryo Adı",
        "editor.field.description": "Açıklama",
        "editor.basic_info_hint": "İnce ayar değerleri (trafik yoğunluğu, araç karışımı, "
                                   "hızlar, dönüşler, sabit süreli, acil durum) yukarıdaki "
                                   "sekmelerde.",
        "editor.field.simulation_time": "Simülasyon Süresi (sn)",
        "editor.field.spawn_interval": "Doğuş Aralığı (sn)",
        "editor.field.playback_speed": "Oynatma Hızı",
        "editor.field.random_seed": "Random Seed",
        "editor.field.fps": "FPS",
        "editor.general_hint": "Doğuş aralığı talep yoğunluğunu (v/c) belirler -- "
                                "değiştirmeden önce docs/scenario_capacity_calibration.md'ye bak.",
        "editor.direction_density_frame": "Yön Yoğunluğu (göreli ağırlık)",
        "editor.allowed_types_frame": "İzin Verilen Araç Tipleri",
        "editor.direction.right": "Sağ",
        "editor.direction.down": "Aşağı",
        "editor.direction.left": "Sol",
        "editor.direction.up": "Yukarı",
        "editor.vehicle_type.car": "Otomobil",
        "editor.vehicle_type.bus": "Otobüs",
        "editor.vehicle_type.truck": "Kamyon",
        "editor.vehicle_type.bike": "Motosiklet",
        "editor.vehicle_type.ambulance": "Ambulans",
        "editor.vehicle_type.police": "Polis",
        "editor.vehicle_type.firetruck": "İtfaiye",
        "editor.vehicle_mix_hint": "Yöne göre araç tipi karışımı (yüzdeler 100'e tamamlanmak "
                                    "zorunda değil -- göreli ağırlık olarak kullanılır).",
        "editor.field.left_turn_probability": "Sola Dönüş Olasılığı",
        "editor.field.right_turn_probability": "Sağa Dönüş Olasılığı",
        "editor.turns_hint": "Şerit dönüş politikası (hangi şeridin hangi dönüşe izin verdiği) "
                              "her senaryoda aynı, sabit bir yapısal ayardır ve burada "
                              "düzenlenmez.",
        "editor.field.initial_green": "Başlangıç Yeşil Yönü",
        "editor.field.green_time": "Yeşil Süre (sn)",
        "editor.field.yellow_time": "Sarı Süre (sn)",
        "editor.field.red_time": "Kırmızı Süre (sn)",
        "editor.emergency_enabled_check": "Bu senaryoda acil durum araçları aktif",
        "editor.emergency_types_frame": "Acil Durum Araç Tipleri",
        "editor.field.spawn_probability": "Doğuş Olasılığı",
        "editor.field.min_spawn_gap": "Min Doğuş Aralığı (sn)",
        "editor.field.max_active_emergency": "Maks. Aktif Acil Durum",
        "editor.emergency_priority_check": "Öncelik mekanizması aktif",
        "editor.field.priority_green_time": "Öncelik Yeşil Süresi (sn)",
        "editor.preview_hint": "Yukarıdaki sekmelerden üretilen, salt-okunur sonuç config "
                                "önizlemesi. Bu sekmeyi her açtığında yenilenir.",
        "editor.msg_error_title": "Senaryo Hatası",
        "editor.msg_name_empty": "Senaryo adı boş olamaz.",
        "editor.msg_invalid_value": "Geçersiz değer: {error}",
        "editor.msg_saved_title": "Kaydedildi",
        "editor.msg_saved_body": "Senaryo kaydedildi: {name}",
        # Simulation window (pygame) and decision explanations
        "sim.approach.right": "Sol",
        "sim.approach.down": "Yukarı",
        "sim.approach.left": "Sağ",
        "sim.approach.up": "Aşağı",
        "sim.signal.right": "SOL",
        "sim.signal.down": "YUKARI",
        "sim.signal.left": "SAĞ",
        "sim.signal.up": "AŞAĞI",
        "sim.reason.emergency": "{approach} yöne {green} saniye yeşil verildi: acil durum aracı "
                                "dur çizgisine {distance} piksel uzakta, önünde {ahead} araç var.",
        "sim.reason.no_demand": "Hiçbir yönde araç yok, yeşil {approach} yönde kalıyor.",
        "sim.reason.normal": "{approach} yöne {green} saniye yeşil verildi. O anda {count} araç "
                             "vardı, yön {red} saniyedir kırmızıydı.{note}",
        "sim.reason.fairness_note": " Tur adaleti gereği sıra bu yöndeydi.",
        "sim.reason.hold": "{approach} yönde yeşil {extension} saniye uzatıldı: bu yöndeki acil "
                           "durum aracının geçmesi bekleniyor.",
        "sim.reason.preempt": "{approach} yönde yeşil {elapsed}. saniyede kesildi: başka yönden "
                              "acil durum aracı yaklaşıyor.",
        "sim.reason.keep_green": "Başka hiçbir yönde araç yok, yeşil {approach} yönde sürüyor.",
        "sim.reason.fixed": "Sabit süre: her yöne sırayla {green} saniye yeşil verilir.",
        "sim.seconds": "{value} sn",
        "sim.percent": "%{value}",
        "sim.header.time": "{elapsed} / {total} sn",
        "sim.header.fixed": "Sabit süre",
        "sim.header.detection": "{model}, tespit {ms} ms",
        "sim.header.speed": "hız {speed}x",
        "sim.card.approaches": "Yönler",
        "sim.card.decision": "Son karar",
        "sim.card.totals": "Bu koşu",
        "sim.card.phases": "Son yeşiller",
        "sim.col.approach": "Yön",
        "sim.col.signal": "Işık",
        "sim.col.vehicles": "Araç",
        "sim.col.vehicles_camera": "Araç (kamera)",
        "sim.col.wait": "Bekleme",
        "sim.col.crossed": "Geçen",
        "sim.row.emergency": "acil durum aracı",
        "sim.row.next": "sıradaki",
        "sim.light.green": "yeşil  {remaining} sn",
        "sim.light.yellow": "sarı  {remaining} sn",
        "sim.light.red": "kırmızı",
        "sim.row.actual": "gerçek {count}",
        "sim.stat.crossed": "geçen araç",
        "sim.stat.delay": "geçenlerde gecikme",
        "sim.stat.longest_wait": "en uzun bekleme",
        "sim.stat.camera_correct": "kamera sayımı doğru",
        "sim.stat.emergency_wait": "acil durum beklemesi",
        "sim.phase.time": "{time}. sn",
        "sim.phase.green": "{green} sn yeşil",
        "sim.phase.crossed": "{count} araç geçti",
        "sim.phase.emergency": "acil durum önceliği",
        "sim.phase.none": "Henüz tamamlanan yeşil yok.",
        "sim.button.pause": "Duraklat",
        "sim.button.resume": "Devam et",
        "sim.button.stop": "Durdur",
        "sim.button.restart": "Yeniden başlat",
        "sim.paused": "DURAKLATILDI",
    },
}


def set_language(language):
    global _current_language
    if language in TRANSLATIONS:
        _current_language = language


def get_language():
    return _current_language


def t(key, **kwargs):
    text = TRANSLATIONS.get(_current_language, {}).get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    return text.format(**kwargs) if kwargs else text


def localized_description(entity, fallback_key="scenarios.no_description"):
    if _current_language == "tr" and entity.get("description_tr"):
        return entity["description_tr"]
    return entity.get("description") or t(fallback_key)


def approach_name(direction):
    """Display name of an approach, e.g. "right" -> "West"."""
    return t(f"sim.approach.{direction}")
