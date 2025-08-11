from helpers.naming_enforcer import check_consistency


def test_logic_names_and_ids_are_consistent():
    issues = check_consistency("logics")
    # Allow zero or more issues locally, but hard fail on conflicts that would break MCP mapping.
    blockers = [
        i
        for i in issues
        if i["issue"].startswith(
            ("bad_filename", "id_mismatch", "missing_id", "multi_handle")
        )
    ]
    assert not blockers, f"Naming/ID contract violations: {blockers}"
