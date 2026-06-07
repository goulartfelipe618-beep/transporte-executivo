"""Cliente HTTP para Supabase REST."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .supabase_config import get_api_key, get_url, is_configured as _configured


def is_configured():
    return _configured()


def _headers(*, prefer=None):
    headers = {
        "apikey": get_api_key(),
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
    }
    headers["Prefer"] = prefer or "return=representation"
    return headers


def _base():
    return get_url().rstrip("/") + "/rest/v1"


def _request(method, url, body=None, *, prefer=None, timeout=20):
    if not is_configured():
        return None
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(prefer=prefer), method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return []
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else [parsed]
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except OSError:
            detail = ""
        raise RuntimeError(f"Supabase {method} {url} -> {exc.code}: {detail}") from exc
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Supabase {method} {url} failed: {exc}") from exc


def select_one(table, filters=None):
    rows = select_all(table, filters=filters, limit=1)
    return rows[0] if rows else None


def select_all(table, filters=None, *, limit=None, order=None):
    if not is_configured():
        return []
    params = [f"{key}=eq.{urllib.parse.quote(str(value))}" for key, value in (filters or {}).items()]
    if order:
        params.append(f"order={urllib.parse.quote(order)}")
    if limit is not None:
        params.append(f"limit={int(limit)}")
    query = "&".join(params)
    url = f"{_base()}/{table}?{query}" if query else f"{_base()}/{table}"
    result = _request("GET", url)
    return result or []


def insert_row(table, payload):
    rows = _request("POST", f"{_base()}/{table}", payload)
    return rows[0] if rows else None


def upsert_row(table, payload, on_conflict="legacy_admin_id"):
    prefer = "resolution=merge-duplicates,return=representation"
    conflict = "id" if payload.get("id") else on_conflict
    url = f"{_base()}/{table}?on_conflict={urllib.parse.quote(conflict)}"
    rows = _request("POST", url, payload, prefer=prefer)
    return rows[0] if rows else None


def patch_rows(table, filters, payload):
    if not filters:
        return []
    params = "&".join(f"{key}=eq.{urllib.parse.quote(str(value))}" for key, value in filters.items())
    url = f"{_base()}/{table}?{params}"
    rows = _request("PATCH", url, payload, prefer="return=representation")
    return rows or []


def delete_rows(table, filters):
    if not filters:
        return
    params = "&".join(f"{key}=eq.{urllib.parse.quote(str(value))}" for key, value in filters.items())
    url = f"{_base()}/{table}?{params}"
    _request("DELETE", url, prefer="return=minimal")


def count_rows(table, filters=None):
    return len(select_all(table, filters=filters))
