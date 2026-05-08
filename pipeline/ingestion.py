import sqlparse
import sqlparse.tokens as T


def parse_sql(raw_sql: str) -> list:
    statements = sqlparse.split(raw_sql)
    return [s.strip() for s in statements if s.strip() and s.strip() != ";" and not _is_comment_only(s.strip())]


def load_sql_file(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return parse_sql(f.read())


def _is_comment_only(stmt: str) -> bool:
    parsed = sqlparse.parse(stmt)
    if not parsed:
        return False
    tokens = [t for t in parsed[0].tokens if not t.is_whitespace]
    return bool(tokens) and all(t.ttype in (T.Comment.Single, T.Comment.Multiline) for t in tokens)
