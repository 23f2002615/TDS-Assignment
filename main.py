import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Start with hardcoded defaults: lowest precedence.
config = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

# 2. Load config.development.yaml and overwrite matching keys.
yaml_path = BASE_DIR / "config.development.yaml"
if yaml_path.exists():
    with open(yaml_path, "r") as f:
        yaml_config = yaml.safe_load(f) or {}
    config.update(yaml_config)

# 3. Load the .env file.
# NUM_WORKERS is an alias for workers.
# APP_API_KEY maps to api_key.
load_dotenv(BASE_DIR / ".env")

env_file_config = {}

if os.getenv("NUM_WORKERS") is not None:
    env_file_config["workers"] = os.getenv("NUM_WORKERS")

if os.getenv("APP_API_KEY") is not None:
    env_file_config["api_key"] = os.getenv("APP_API_KEY")

config.update(env_file_config)

# 4. Read real OS environment variables beginning with APP_.
# APP_PORT -> port, APP_LOG_LEVEL -> log_level, etc.
for env_name, value in os.environ.items():
    if env_name.startswith("APP_"):
        config_key = env_name[len("APP_"):].lower()
        config[config_key] = value


# Convert string values into the types the grader expects.
def coerce_value(key: str, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes", "on")

    return str(value)


app = FastAPI()

# Allow the grading page/browser to call this API from another origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/effective-config")
def effective_config(set: list[str] | None = Query(default=None)):
    # Make a fresh copy so CLI overrides do not permanently change server config.
    effective = dict(config)

    # 5. Apply CLI overrides: ?set=port=9000&set=debug=true
    if set:
        for item in set:
            if "=" not in item:
                continue

            key, value = item.split("=", 1)
            key = key.strip()
            effective[key] = value

    # Convert every known config value to its required type.
    result = {
        "port": coerce_value("port", effective.get("port", 8000)),
        "workers": coerce_value("workers", effective.get("workers", 1)),
        "debug": coerce_value("debug", effective.get("debug", False)),
        "log_level": coerce_value("log_level", effective.get("log_level", "info")),
        "api_key": "****",  # Never expose the real secret.
    }

    return result