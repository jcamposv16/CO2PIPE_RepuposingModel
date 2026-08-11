# Save as scripts/diagnose_map_click.py and run with: python scripts/diagnose_map_click.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path("src")))

from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=30)
at.run()
print("=== Initial run exceptions ===")
print(at.exception)
print("=== Map widget present? ===")
print([type(e).__name__ for e in at.main])

# Simulate what happens when st_folium returns a click payload
# by directly setting session_state as if a map click occurred
# and then re-running
at.session_state["selected_feature_id"] = at.sidebar.selectbox[0].options[1]
at.run()
print("=== After selectbox change exceptions ===")
print(at.exception)
print("=== Metrics still present? ===")
for m in at.metric:
    print(f"  {m.label}: {m.value}")
