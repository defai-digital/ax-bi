import ast

from superset.db_engine_specs import lint_metadata


def test_eval_ast_value_handles_removed_legacy_ast_aliases(monkeypatch):
    """
    Python 3.14 removed legacy ast.Str/ast.Num aliases.

    Metadata can contain attribute values such as DatabaseCategory.OPEN_SOURCE;
    those should still be parsed even when the legacy aliases are unavailable.
    """
    monkeypatch.delattr(ast, "Str", raising=False)
    monkeypatch.delattr(ast, "Num", raising=False)

    node = ast.parse("DatabaseCategory.OPEN_SOURCE").body[0].value

    assert lint_metadata._eval_ast_value(node) == "DatabaseCategory.OPEN_SOURCE"
