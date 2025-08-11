import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers.naming_enforcer import check_consistency, propose_new_name
import os, json, sys


def main():
    issues = check_consistency("logics")
    suggestions = []
    for i in issues:
        if i["issue"].startswith(("bad_filename", "missing_id", "id_mismatch")):
            sug = propose_new_name(i["file"])
            suggestions.append(
                {"file": i["file"], "issue": i["issue"], "suggested_name": sug}
            )
    print(json.dumps(suggestions, indent=2))


if __name__ == "__main__":
    main()
