from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"

SCENARIOS_FILE = DATA_DIR / "scenarios.json"
CONTROLLER_VERSIONS_FILE = DATA_DIR / "controller_versions.json"
STATE_PROVIDERS_FILE = DATA_DIR / "state_providers.json"
TEST_COUNTERS_FILE = DATA_DIR / "test_counters.json"
APP_STATE_FILE = DATA_DIR / "app_state.json"
TREE_FILE = ROOT_DIR / "TREE.txt"
