"""Backward-compatible entry point; the application lives in ACEest_Fitness.py."""
from ACEest_Fitness import (  # noqa: F401
    CLIENTS,
    PROGRAMS,
    VERSION,
    bmi_category,
    calculate_bmi,
    create_app,
    estimate_calories,
    reset_store,
)

if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
