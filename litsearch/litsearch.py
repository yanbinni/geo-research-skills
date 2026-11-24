#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
litsearch - multi-source literature search CLI (zero dependency, stdlib only).

Part of the `litsearch` skill. See SKILL.md / INSTALL.md.

Commands:
  search   multi-source keyword search -> merged, deduped list
  expand   citation snowballing from one seed DOI
  oa       batch open-access lookup by DOI
  doctor   environment / key / connectivity self-check
  sources  list configured sources
"""

import argparse
import csv
import difflib
import json
import os
import re
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from xml.etree import ElementTree as ET

VERSION = "1.0.0"

HOME = os.path.expanduser("~")
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
CFG_DIR = os.environ.get("LITSEARCH_HOME") or os.path.join(HOME, ".litsearch")
CFG_PATH = os.path.join(CFG_DIR, "config.json")
DB_PATH = os.path.join(CFG_DIR, "cache.sqlite")

DEFAULT_CFG = {
    "openalex_api_key": "",
    "serpapi_api_key": "",
    "searchapi_api_key": "",
    "core_api_key": "",
    "unpaywall_email": "",
    "mailto": "",
    "limits": {
        "max_per_source": 50,
        "timeout_sec": 15,
        "serpapi_monthly": 100,
        "searchapi_monthly": 100,
    },
}

# ---------------------------------------------------------------- utilities


def out(s=""):
    sys.stdout.write(str(s) + "\n")


def eprint(*a):
    sys.stderr.write(" ".join(str(x) for x in a) + "\n")


def load_cfg():
    cfg = json.loads(json.dumps(DEFAULT_CFG))
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, encoding="utf-8-sig") as fh:
                user = json.load(fh)
            for k, v in user.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except Exception as e:
            eprint("[warn] cannot read config.json:", e)
    # env fallbacks
    env_map = {
        "openalex_api_key": "OPENALEX_API_KEY",
        "serpapi_api_key": "SERPAPI_API_KEY",
        "searchapi_api_key": "SEARCHAPI_API_KEY",
        "core_api_key": "CORE_API_KEY",
        "unpaywall_email": "UNPAYWALL_EMAIL",
        "mailto": "LITSEARCH_MAILTO",
    }
    for k, ek in env_map.items():
        if not cfg.get(k) and os.environ.get(ek):
            cfg[k] = os.environ[ek]
    if not cfg.get("mailto"):
        cfg["mailto"] = cfg.get("unpaywall_email") or ""
    return cfg


def user_agent(cfg):
    return "litsearch/%s (+personal research tool; mailto:%s)" % (
        VERSION,
        cfg.get("mailto") or "unknown",
    )


def http(url, params=None, data=None, timeout=15, cfg=None, accept=None, extra_headers=None):
    """GET/POST -> parsed JSON (or raw text when accept='text')."""
    if params:
        sep = "&" if "?" in url else "?"
        url = url + sep + urllib.parse.urlencode(params, doseq=True)
    headers = {"User-Agent": user_agent(cfg or {})}
    headers["Accept"] = accept or "application/json"
    if extra_headers:
        headers.update(extra_headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url, data=body, headers=headers, method="POST" if body else "GET"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    if accept == "text":
        return raw.decode("utf-8", "replace")
    return json.loads(raw.decode("utf-8", "replace"))


def block_until(con, name):
    v = cache_get(con, "block:" + name, ttl_days=1)
    if isinstance(v, (int, float)) and time.time() < v:
        return int(v - time.time())
    return 0


def set_block(con, name, minutes):
    cache_put(con, "block:" + name, time.time() + minutes * 60)


def norm_doi(v):
    if not v:
        return ""
    v = str(v).strip().lower()
    v = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", "", v)
    return v.strip().rstrip(".")


def norm_title(v):
    if not v:
        return ""
    v = str(v).lower()
    v = re.sub(r"<[^>]+>", " ", v)
    v = re.sub(r"[^a-z0-9\u4e00-\u9fff ]+", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def clean(s):
    if s is None:
        return ""
    s = re.sub(r"<[^>]+>", " ", str(s))
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", s).strip()


def mkrec(**kw):
    r = {
        "title": "",
        "year": None,
        "venue": "",
        "doi": "",
        "authors": [],
        "abstract": "",
        "url": "",
        "cited": None,
        "oa": None,
        "type": "",
        "source": [],
        "id": "",
        "sid": "",
        "jif": None,
        "h": None,
        "py": None,
    }
    for k, v in kw.items():
        if k in r:
            r[k] = v
    r["doi"] = norm_doi(r["doi"])
    r["title"] = clean(r["title"])
    if r.get("abstract"):
        r["abstract"] = clean(r["abstract"])
    if r.get("venue"):
        r["venue"] = clean(r["venue"])
    return r


# ---------------------------------------------------------------- cache / usage


_DB_LOCK = threading.Lock()
_DB_MODE = "file"
_DB_PATH_USED = DB_PATH


def db():
    """Open the cache DB; fall back to temp dir, then memory, when unwritable."""
    global _DB_MODE, _DB_PATH_USED
    con = None
    candidates = [DB_PATH]
    try:
        import tempfile
        candidates.append(os.path.join(tempfile.gettempdir(), "litsearch_cache.sqlite"))
    except Exception:
        pass
    for path in candidates:
        try:
            d = os.path.dirname(path)
            if d:
                os.makedirs(d, exist_ok=True)
            con = sqlite3.connect(path, timeout=15, check_same_thread=False)
            con.execute("SELECT 1").fetchone()
            _DB_MODE = "file"
            _DB_PATH_USED = path
            break
        except Exception:
            try:
                if con:
                    con.close()
            except Exception:
                pass
            con = None
    if con is None:
        con = sqlite3.connect(":memory:", check_same_thread=False)
        _DB_MODE = "memory"
        _DB_PATH_USED = ":memory:"
    with _DB_LOCK:
        con.execute(
            "CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, ts REAL, v TEXT)"
        )
        con.execute(
            "CREATE TABLE IF NOT EXISTS usage (period TEXT, source TEXT, n INTEGER, PRIMARY KEY (period, source))"
        )
        con.commit()
    return con


def cache_get(con, key, ttl_days=7):
    with _DB_LOCK:
        row = con.execute("SELECT ts, v FROM cache WHERE k=?", (key,)).fetchone()
    if not row:
        return None
    if time.time() - row[0] > ttl_days * 86400:
        return None
    try:
        return json.loads(row[1])
    except Exception:
        return None


def cache_put(con, key, val):
    try:
        with _DB_LOCK:
            con.execute(
                "INSERT OR REPLACE INTO cache (k, ts, v) VALUES (?,?,?)",
                (key, time.time(), json.dumps(val, ensure_ascii=False)),
            )
            con.commit()
    except Exception:
        pass


def bump_usage(con, source, period):
    try:
        with _DB_LOCK:
            con.execute(
                "INSERT INTO usage (period, source, n) VALUES (?,?,1) "
                "ON CONFLICT(period, source) DO UPDATE SET n = n + 1",
                (period, source),
            )
            con.commit()
    except Exception:
        pass


def usage_count(con, source, period):
    with _DB_LOCK:
        row = con.execute(
            "SELECT n FROM usage WHERE period=? AND source=?", (period, source)
        ).fetchone()
    return row[0] if row else 0


# ---------------------------------------------------------------- sources


def src_openalex(q, since, until, limit, cfg, con):
    key = cfg.get("openalex_api_key") or ""
    params = {
        "search": q,
        "per_page": min(limit, 100),
        "select": "id,doi,display_name,publication_year,publication_date,"
        "authorships,primary_location,abstract_inverted_index,cited_by_count,"
        "type,open_access,best_oa_location",
    }
    filt = []
    if since:
        filt.append("from_publication_date:%s-01-01" % since)
    if until:
        filt.append("to_publication_date:%s-12-31" % until)
    if filt:
        params["filter"] = ",".join(filt)
    if key:
        params["api_key"] = key
    bump_usage(con, "openalex", date.today().isoformat())
    d = http("https://api.openalex.org/works", params, cfg=cfg,
             timeout=int(cfg["limits"]["timeout_sec"]))
    recs = []
    for w in d.get("results", []):
        inv = w.get("abstract_inverted_index") or {}
        abstract = ""
        if inv:
            pos = []
            for word, idxs in inv.items():
                for i in idxs:
                    pos.append((i, word))
            pos.sort()
            abstract = " ".join(x[1] for x in pos)
        loc = w.get("primary_location") or {}
        src = (loc.get("source") or {}) if isinstance(loc, dict) else {}
        oa = w.get("open_access") or {}
        best = w.get("best_oa_location") or {}
        recs.append(
            mkrec(
                title=w.get("display_name") or w.get("title") or "",
                year=w.get("publication_year"),
                venue=src.get("display_name") or "",
                doi=w.get("doi"),
                authors=[
                    (a.get("author") or {}).get("display_name", "")
                    for a in (w.get("authorships") or [])[:12]
                ],
                abstract=abstract,
                url=loc.get("landing_page_url") or "",
                cited=w.get("cited_by_count"),
                oa={
                    "is_oa": bool(oa.get("is_oa")),
                    "status": oa.get("oa_status") or "",
                    "url": best.get("url_for_pdf") or best.get("url") or "",
                },
                type=w.get("type") or "",
                source=["openalex"],
                id=w.get("id") or "",
                sid=src.get("id") or "",
            )
        )
    return recs


def src_crossref(q, since, until, limit, cfg, con):
    params = {
        "query.bibliographic": q,
        "rows": min(limit, 100),
        "select": "DOI,title,author,container-title,issued,abstract,"
        "is-referenced-by-count,URL,type",
    }
    if cfg.get("mailto"):
        params["mailto"] = cfg["mailto"]
    filt = []
    if since:
        filt.append("from-pub-date:%s-01-01" % since)
    if until:
        filt.append("until-pub-date:%s-12-31" % until)
    if filt:
        params["filter"] = ",".join(filt)
    d = http("https://api.crossref.org/works", params, cfg=cfg,
             timeout=int(cfg["limits"]["timeout_sec"]))
    recs = []
    for it in (d.get("message") or {}).get("items", []):
        year = None
        parts = ((it.get("issued") or {}).get("date-parts") or [[None]])[0]
        if parts:
            year = parts[0]
        ct = it.get("container-title") or []
        recs.append(
            mkrec(
                title=(it.get("title") or [""])[0],
                year=year,
                venue=ct[0] if ct else "",
                doi=it.get("DOI"),
                authors=[
                    "%s %s" % (a.get("given", ""), a.get("family", ""))
                    for a in (it.get("author") or [])[:12]
                ],
                abstract=it.get("abstract") or "",
                url=it.get("URL") or "",
                cited=it.get("is-referenced-by-count"),
                type=it.get("type") or "",
                source=["crossref"],
            )
        )
    return recs


def src_arxiv(q, since, until, limit, cfg, con):
    terms = [t for t in re.split(r"\s+", q.strip()) if t]
    query = " AND ".join('all:"%s"' % t for t in terms[:8])
    params = {
        "search_query": query,
        "start": 0,
        "max_results": min(limit, 100),
        "sortBy": "relevance",
    }
    txt = http(
        "http://export.arxiv.org/api/query",
        params,
        cfg=cfg,
        accept="text",
        timeout=int(cfg["limits"]["timeout_sec"]) + 10,
    )
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(txt)
    recs = []
    for e in root.findall("a:entry", ns):
        t = clean("".join(e.find("a:title", ns).itertext()))
        pub = (e.find("a:published", ns).text or "")[:4]
        aid = (e.find("a:id", ns).text or "").strip()
        summ = clean("".join(e.find("a:summary", ns).itertext()))
        auths = [
            clean("".join(a.find("a:name", ns).itertext()))
            for a in e.findall("a:author", ns)
        ]
        doi = ""
        for link in e.findall("a:link", ns):
            pass
        recs.append(
            mkrec(
                title=t,
                year=int(pub) if pub.isdigit() else None,
                venue="arXiv",
                doi=doi,
                authors=auths[:12],
                abstract=summ,
                url=aid.replace("http://", "https://"),
                type="preprint",
                source=["arxiv"],
                id=aid,
            )
        )
    return recs


def src_doaj(q, since, until, limit, cfg, con):
    enc = urllib.parse.quote(q, safe="")
    d = http(
        "https://doaj.org/api/search/articles/" + enc,
        {"pageSize": min(limit, 100)},
        cfg=cfg,
        timeout=int(cfg["limits"]["timeout_sec"]),
    )
    recs = []
    for it in d.get("results", []):
        b = it.get("bibjson") or {}
        y = b.get("year")
        doi = ""
        for ident in (b.get("identifier") or []):
            if str(ident.get("type", "")).lower() == "doi":
                doi = ident.get("id", "")
                break
        recs.append(
            mkrec(
                title=b.get("title") or "",
                year=int(y) if y and str(y).isdigit() else None,
                venue=(b.get("journal") or {}).get("title", ""),
                doi=doi,
                authors=[a.get("name", "") for a in (b.get("author") or [])[:12]],
                abstract=b.get("abstract") or "",
                url=(b.get("link") or [{}])[0].get("url", ""),
                type="article",
                source=["doaj"],
            )
        )
    return recs


def _names(v, keys=("text", "name", "author")):
    """Coerce various 'people' payloads into a list of names."""
    if not v:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, dict):
        v = [v]
    outp = []
    for a in list(v)[:12]:
        if isinstance(a, str):
            outp.append(a)
        elif isinstance(a, dict):
            for k in keys:
                if a.get(k):
                    val = a[k]
                    if isinstance(val, dict):
                        val = val.get("name") or val.get("text") or ""
                    outp.append(str(val))
                    break
    return [clean(x) for x in outp if x]


def src_core(q, since, until, limit, cfg, con):
    wait = block_until(con, "core")
    if wait:
        raise RuntimeError("CORE 限流冷却中，%d 分钟后自动重试" % (wait // 60 + 1))
    last = None
    headers = {}
    if cfg.get("core_api_key"):
        headers["Authorization"] = "Bearer " + cfg["core_api_key"]
    for attempt in range(2):
        try:
            d = http(
                "https://api.core.ac.uk/v3/search/works",
                {"q": q, "limit": min(limit, 100)},
                cfg=cfg,
                timeout=int(cfg["limits"]["timeout_sec"]) + 10,
                extra_headers=headers or None,
            )
            break
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 401, 403):
                set_block(con, "core", 60)
                raise RuntimeError("CORE 限流(%s)，匿名额度很低，已冷却 60 分钟" % e.code)
            if attempt == 0:
                time.sleep(2)
                continue
            raise
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt == 0:
                time.sleep(2)
                continue
            raise
    else:
        raise RuntimeError(str(last))
    recs = []
    for it in d.get("results", []):
        y = it.get("yearPublished")
        recs.append(
            mkrec(
                title=it.get("title") or "",
                year=int(y) if y and str(y).isdigit() else None,
                venue=it.get("publisher") or "",
                doi=it.get("doi") or "",
                authors=_names(it.get("authors")),
                abstract=it.get("abstract") or "",
                url=it.get("downloadUrl") or "",
                type=it.get("documentType") or "",
                source=["core"],
            )
        )
    return recs


def src_usgs(q, since, until, limit, cfg, con):
    params = {"q": q, "page_size": min(limit, 100)}
    d = http(
        "https://pubs.usgs.gov/pubs-services/publication/",
        params,
        cfg=cfg,
        timeout=int(cfg["limits"]["timeout_sec"]),
    )
    recs = []
    for it in d.get("records") or d.get("items") or []:
        idx = it.get("indexId") or it.get("publicationId") or ""
        y = it.get("publicationYear")
        recs.append(
            mkrec(
                title=it.get("title") or "",
                year=int(y) if y and str(y).isdigit() else None,
                venue="USGS Publications Warehouse",
                doi=it.get("doi") or "",
                authors=_names(it.get("contributors")) or _names(it.get("authors")),
                abstract=it.get("abstract") or "",
                url=("https://pubs.usgs.gov/publication/%s" % idx) if idx else "",
                type="report",
                source=["usgs"],
                id=idx,
            )
        )
    return recs


def src_ntrs(q, since, until, limit, cfg, con):
    payload = {"q": q, "page": {"size": min(limit, 100), "from": 0}}
    d = http(
        "https://ntrs.nasa.gov/api/citations/search",
        data=payload,
        cfg=cfg,
        timeout=int(cfg["limits"]["timeout_sec"]),
    )
    recs = []
    for it in d.get("results", []):
        t = it.get("title")
        if isinstance(t, list):
            t = t[0] if t else ""
        y = (it.get("publicationDate") or "")[:4]
        nid = it.get("id") or ""
        auths = []
        for a in (it.get("authorAffiliations") or [])[:8]:
            try:
                nm = ((a.get("meta") or {}).get("author") or {}).get("name") or ""
            except Exception:  # noqa: BLE001
                nm = ""
            if nm:
                auths.append(nm)
        recs.append(
            mkrec(
                title=t,
                year=int(y) if y.isdigit() else None,
                venue="NASA NTRS",
                doi=it.get("doi") or "",
                authors=auths,
                abstract=clean(it.get("abstract") or ""),
                url=("https://ntrs.nasa.gov/citations/%s" % nid) if nid else "",
                type="report",
                source=["ntrs"],
                id=str(nid),
            )
        )
    return recs


def _gs_serpapi(q, limit, cfg, con):
    if not cfg.get("serpapi_api_key"):
        raise RuntimeError("未配置 serpapi_api_key")
    period = datetime.now().strftime("%Y-%m")
    used = usage_count(con, "serpapi", period)
    if used >= int(cfg["limits"]["serpapi_monthly"]):
        raise RuntimeError("SerpAPI 本月额度已用尽 (%d)" % used)
    bump_usage(con, "serpapi", period)
    d = http(
        "https://serpapi.com/search.json",
        {
            "engine": "google_scholar",
            "q": q,
            "num": min(limit, 20),
            "api_key": cfg["serpapi_api_key"],
        },
        cfg=cfg,
        timeout=int(cfg["limits"]["timeout_sec"]),
    )
    recs = []
    for it in d.get("organic_results", []):
        pub = it.get("publication_info") or {}
        summ = pub.get("summary") or ""
        y = re.search(r"\b(19|20)\d{2}\b", summ)
        recs.append(
            mkrec(
                title=it.get("title") or "",
                year=int(y.group(0)) if y else None,
                venue=summ[:120],
                authors=[a.get("name", "") for a in (pub.get("authors") or [])][:12],
                abstract=it.get("snippet") or "",
                url=it.get("link") or "",
                cited=(it.get("inline_links") or {}).get("cited_by", {}).get("total"),
                type="scholar",
                source=["google_scholar"],
                id=it.get("result_id") or "",
            )
        )
    return recs


def _gs_searchapi(q, limit, cfg, con):
    if not cfg.get("searchapi_api_key"):
        raise RuntimeError("未配置 searchapi_api_key")
    period = datetime.now().strftime("%Y-%m")
    used = usage_count(con, "searchapi", period)
    if used >= int(cfg["limits"]["searchapi_monthly"]):
        raise RuntimeError("SearchApi 本月额度已用尽 (%d)" % used)
    bump_usage(con, "searchapi", period)
    d = http(
        "https://www.searchapi.io/api/v1/search",
        {
            "engine": "google_scholar",
            "q": q,
            "num": min(limit, 20),
            "api_key": cfg["searchapi_api_key"],
        },
        cfg=cfg,
        timeout=int(cfg["limits"]["timeout_sec"]),
    )
    recs = []
    for it in d.get("organic_results", []):
        pub = it.get("publication_info") or {}
        summ = pub.get("summary") or ""
        y = re.search(r"\b(19|20)\d{2}\b", summ)
        recs.append(
            mkrec(
                title=it.get("title") or "",
                year=int(y.group(0)) if y else None,
                venue=summ[:120],
                authors=[a.get("name", "") for a in (pub.get("authors") or [])][:12],
                abstract=it.get("snippet") or "",
                url=it.get("link") or "",
                cited=(it.get("inline_links") or {}).get("cited_by", {}).get("total"),
                type="scholar",
                source=["google_scholar"],
                id=it.get("result_id") or "",
            )
        )
    return recs


def src_google_scholar(q, since, until, limit, cfg, con):
    """Provider chain: SerpAPI -> SearchApi."""
    errs = []
    for fn, label in ((_gs_serpapi, "SerpAPI"), (_gs_searchapi, "SearchApi")):
        try:
            return fn(q, limit, cfg, con)
        except Exception as e:
            errs.append("%s: %s" % (label, str(e)[:90]))
    raise RuntimeError("; ".join(errs) or "no provider configured")


SOURCES = {
    # name -> (tier, label, func, needs_key)
    "openalex": ("A", "OpenAlex", src_openalex, False),
    "crossref": ("A", "Crossref", src_crossref, False),
    "arxiv": ("B", "arXiv", src_arxiv, False),
    "doaj": ("A", "DOAJ", src_doaj, False),
    "core": ("A", "CORE", src_core, False),
    "usgs": ("C", "USGS", src_usgs, False),
    "ntrs": ("C", "NASA NTRS", src_ntrs, False),
    "google_scholar": ("C", "Google Scholar", src_google_scholar, True),
}

TIER_DEFAULT = {
    "A": ["openalex", "crossref", "doaj", "core"],
    "B": ["arxiv"],
    "C": ["usgs", "ntrs", "google_scholar"],
    "D": [],
}

# rough value ordering: journal articles first, then proceedings, preprints, rest
TYPE_RANK = {
    "article": 0,
    "review": 0,
    "book-chapter": 1,
    "proceedings-article": 2,
    "posted-content": 3,
    "preprint": 3,
    "report": 3,
    "scholar": 4,
    "dataset": 5,
    "": 2,
}


def type_rank(t):
    t = (t or "").lower()
    if t in TYPE_RANK:
        return TYPE_RANK[t]
    if "article" in t:
        return 1
    if "preprint" in t or "posted" in t:
        return 3
    return 2

# ---------------------------------------------------------------- merge / dedupe


def merge_into(dst, src):
    if not dst.get("abstract") and src.get("abstract"):
        dst["abstract"] = src["abstract"]
    if not dst.get("doi") and src.get("doi"):
        dst["doi"] = src["doi"]
    if not dst.get("venue") and src.get("venue"):
        dst["venue"] = src["venue"]
    if not dst.get("year") and src.get("year"):
        dst["year"] = src["year"]
    if not dst.get("url") and src.get("url"):
        dst["url"] = src["url"]
    if not dst.get("authors") and src.get("authors"):
        dst["authors"] = src["authors"]
    if (src.get("cited") or 0) > (dst.get("cited") or 0):
        dst["cited"] = src.get("cited")
    if not dst.get("oa") and src.get("oa"):
        dst["oa"] = src["oa"]
    if src.get("oa") and dst.get("oa") and not dst["oa"].get("url"):
        dst["oa"] = src["oa"]
    for s in src.get("source") or []:
        if s not in dst["source"]:
            dst["source"].append(s)


def dedupe(recs):
    out, by_doi = [], {}
    for r in recs:
        if not (r.get("title") or "").strip():
            continue
        d = r.get("doi")
        if d and d in by_doi:
            merge_into(by_doi[d], r)
            continue
        if d:
            by_doi[d] = r
        out.append(r)

    final = []
    for r in out:
        nt = norm_title(r.get("title"))
        hit = None
        for f in final:
            ft = norm_title(f.get("title"))
            if not nt or not ft:
                continue
            if r.get("year") and f.get("year") and abs(int(r["year"]) - int(f["year"])) > 1:
                continue
            if difflib.SequenceMatcher(None, nt[:130], ft[:130]).ratio() >= 0.92:
                hit = f
                break
        if hit is not None:
            merge_into(hit, r)
        else:
            final.append(r)
    return final


# ---------------------------------------------------------------- orchestration


def run_one(name, q, since, until, limit, cfg, con, timeout):
    """Run a single source with wall-clock protection; returns (recs, status)."""
    t0 = time.time()
    box = {}

    def work():
        try:
            box["v"] = SOURCES[name][2](q, since, until, limit, cfg, con)
        except Exception as ex:  # noqa: BLE001
            box["e"] = ex

    th = threading.Thread(target=work, daemon=True)
    th.start()
    th.join(timeout)
    dt = round(time.time() - t0, 1)
    if th.is_alive():
        return [], {"name": name, "label": SOURCES[name][1], "ok": False,
                    "n": 0, "secs": dt, "msg": "超时（>%ss）" % timeout}
    if "e" in box:
        return [], {"name": name, "label": SOURCES[name][1], "ok": False,
                    "n": 0, "secs": dt, "msg": str(box["e"])[:160]}
    recs = box.get("v") or []
    return recs, {"name": name, "label": SOURCES[name][1], "ok": True,
                  "n": len(recs), "secs": dt, "msg": ""}


def resolve_sources(args):
    if args.sources:
        names = [s.strip() for s in args.sources.split(",") if s.strip()]
        bad = [n for n in names if n not in SOURCES]
        if bad:
            raise SystemExit("未知源: %s（可选: %s）" % (", ".join(bad), ", ".join(SOURCES)))
        return names
    tier = (args.tier or "ABC").upper()
    if tier in ("ALL", "*"):
        return list(SOURCES)
    names = []
    for ch in tier:
        names.extend(TIER_DEFAULT.get(ch, []))
    return names or list(SOURCES)


def enrich_journals(recs, cfg, con):
    """Fetch OpenAlex source metrics (2yr mean citedness ~ impact factor, h-index)."""
    sids = sorted({r.get("sid") for r in recs if r.get("sid")})
    if not sids:
        return
    info = {}
    for i in range(0, len(sids), 50):
        chunk = [s.rsplit("/", 1)[-1] for s in sids[i:i + 50]]
        params = {
            "filter": "openalex_id:" + "|".join(chunk),
            "per_page": 50,
            "select": "id,display_name,summary_stats,issn_l",
        }
        if cfg.get("openalex_api_key"):
            params["api_key"] = cfg["openalex_api_key"]
        try:
            d = http("https://api.openalex.org/sources", params, cfg=cfg,
                     timeout=int(cfg["limits"]["timeout_sec"]))
        except Exception:
            continue
        for s in d.get("results", []):
            ss = s.get("summary_stats") or {}
            info[s.get("id")] = (ss.get("2yr_mean_citedness"), ss.get("h_index"))
    for r in recs:
        v = info.get(r.get("sid") or "")
        if v:
            jif, h = v
            r["jif"] = round(jif, 1) if isinstance(jif, (int, float)) else None
            r["h"] = h
    today = date.today().year
    for r in recs:
        if r.get("cited") is not None and r.get("year"):
            span = max(1, today - int(r["year"]) + 1)
            r["py"] = round(r["cited"] / span, 1)


def cmd_search(args, cfg):
    con = db()
    q = args.query
    names = resolve_sources(args)
    limit = args.max or int(cfg["limits"]["max_per_source"])
    timeout = args.timeout or int(cfg["limits"]["timeout_sec"]) + 10
    since, until = args.since, args.until

    all_recs, statuses = [], []
    threads = []
    results = {}

    def runner(nm):
        results[nm] = run_one(nm, q, since, until, limit, cfg, con, timeout)

    for nm in names:
        t = threading.Thread(target=runner, args=(nm,), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout + 5)

    for nm in names:
        if nm not in results:
            statuses.append({"name": nm, "label": SOURCES[nm][1], "ok": False,
                             "n": 0, "secs": timeout, "msg": "未返回"})
            continue
        recs, st = results[nm]
        all_recs.extend(recs)
        statuses.append(st)

    merged = dedupe(all_recs)
    if args.sort == "year":
        merged.sort(key=lambda r: ((r.get("year") or 0), (r.get("cited") or 0)), reverse=True)
    else:
        merged.sort(key=lambda r: (type_rank(r.get("type")),
                                   -(r.get("cited") or 0),
                                   -(r.get("year") or 0)))

    if args.limit_out:
        merged = merged[: args.limit_out]

    enrich_journals(merged, cfg, con)
    render(merged, statuses, q, args, cfg, con)
    return merged, statuses


def build_gaps(merged, statuses, q, args):
    """Dynamic 'what you still need to search yourself' table."""
    rows = []
    st = {s["name"]: s for s in statuses}
    gs = st.get("google_scholar")
    gs_bad = (gs is None) or (not gs["ok"])
    core = st.get("core")
    core_bad = bool(core) and not core["ok"]

    rows.append(
        ("中文文献", "本工具不含 CNKI / 万方 / 维普",
         "知网、万方、维普（校内 IP 或图书馆入口）",
         "把本次英文检索式译成中文后再检索（工具无法自动翻译）")
    )
    if gs_bad:
        reason = "Google Scholar 不可用" + ("：" + gs["msg"] if gs and gs.get("msg") else "")
        rows.append(
            ("灰色文献", reason,
             "手动 Google Scholar / 百度学术",
             '"%s"（可加 filetype:pdf）' % q[:60])
        )
    if core_bad:
        rows.append(
            ("学位论文 / 机构库", "CORE 本次未返回结果",
             "各校图书馆学位论文库、CORE 官网", '"%s"' % q[:60])
        )
    y = date.today().year
    rows.append(
        ("图书 / 标准 / 地图集 / 会议摘要", "非 DOI 文献，不在任何 API 覆盖内",
         "图书馆书目系统、IEEE/ISPRS 会议官网、标准全文库",
         "按机构名或会议名单独检索")
    )
    rows.append(
        ("近 1–3 个月新刊", "OpenAlex/Crossref 收录有滞后",
         "目标期刊官网 / RSS / 出版社 alert",
         "锁定 3–5 本核心期刊逐期浏览 %d 年" % y)
    )
    return rows


def fmt_authors(a):
    a = [x for x in a if x]
    if not a:
        return ""
    if len(a) > 3:
        return a[0] + " et al."
    return ", ".join(a)


def render(merged, statuses, q, args, cfg, con):
    fmt = args.format
    if fmt == "csv":
        write_csv(merged, args.out)
        return
    if fmt == "json":
        payload = {
            "query": q,
            "generated": datetime.now().isoformat(timespec="seconds"),
            "count": len(merged),
            "statuses": statuses,
            "gaps": [dict(zip(["gap", "reason", "where", "query"], g))
                     for g in build_gaps(merged, statuses, q, args)],
            "records": merged,
        }
        text = json.dumps(payload, ensure_ascii=False, indent=1)
        emit(text, args.out)
        return

    L = []
    L.append("# 文献检索结果：%s" % q)
    L.append("")
    L.append("- 生成时间：%s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    L.append("- 时间窗：%s ~ %s" % (args.since or "不限", args.until or "不限"))
    L.append("- 去重后：**%d 篇**" % len(merged))
    L.append("")
    L.append("## 文献清单")
    L.append("")
    if not merged:
        L.append("_没有命中任何文献。_")
    else:
        L.append("| # | 年份 | 标题 | 期刊/来源 | IF≈ | 被引 | 被引/年 | DOI | OA | 数据源 |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(merged, 1):
            title = (r.get("title") or "").replace("|", "/")
            if len(title) > 120:
                title = title[:117] + "..."
            if r.get("url") and not r.get("doi"):
                title = "[%s](%s)" % (title, r["url"])
            doi = r.get("doi") or ""
            if doi:
                doi = "[%s](https://doi.org/%s)" % (doi, doi)
            oa = r.get("oa") or {}
            if oa.get("is_oa"):
                oa_s = oa.get("status") or "OA"
                if oa.get("url"):
                    oa_s = "[%s](%s)" % (oa_s, oa["url"])
            else:
                oa_s = "—"
            L.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                i,
                r.get("year") or "",
                title,
                (r.get("venue") or "").replace("|", "/")[:55],
                r.get("jif") if r.get("jif") is not None else "—",
                r.get("cited") if r.get("cited") is not None else "",
                r.get("py") if r.get("py") is not None else "",
                doi,
                oa_s,
                ",".join(r.get("source") or []),
            ))
        L.append("")
        L.append("> **IF≈** = OpenAlex 的 2yr mean citedness，与影响因子同算法（前两年文章在本年的篇均"
                 "被引），免费可批量取；但不是 Clarivate JCR 官方 IF，数值会有出入，只适合横向量级比较。")
        L.append("> **被引/年** = 总被引 ÷ 发表年数，用来抵消新文章攒被引时间短的偏差。")
    L.append("")
    L.append("## 来源状态")
    L.append("")
    L.append("| 源 | 状态 | 条数 | 耗时 | 说明 |")
    L.append("|---|---|---|---|---|")
    for s in statuses:
        L.append("| %s | %s | %d | %ss | %s |" % (
            s["label"], "✅" if s["ok"] else "❌", s["n"], s["secs"],
            (s.get("msg") or "").replace("|", "/")[:80]))
    L.append("")
    n_abs = getattr(args, "abstracts", 0) or 0
    if n_abs and merged:
        L.append("## 摘要速览（前 %d 篇）" % min(n_abs, len(merged)))
        L.append("")
        for i, r in enumerate(merged[:n_abs], 1):
            L.append("**[%d] %s** (%s)" % (i, r.get("title") or "", r.get("year") or "—"))
            ab = clean(r.get("abstract") or "")
            if not ab:
                L.append("> （该源未提供摘要，需要看原文）")
            else:
                L.append("> " + (ab[:600] + ("..." if len(ab) > 600 else "")))
            L.append("")
    L.append("## 需要你自己补检的部分")
    L.append("")
    L.append("> 以下缺口由本次实际运行状态自动生成，不是固定免责声明。")
    L.append("")
    L.append("| 缺口 | 本次原因 | 建议去哪补 | 建议检索式 |")
    L.append("|---|---|---|---|")
    for g in build_gaps(merged, statuses, q, args):
        L.append("| %s | %s | %s | %s |" % tuple(x.replace("|", "/") for x in g))
    L.append("")
    emit("\n".join(L), args.out)


def emit(text, path):
    if path:
        try:
            # utf-8-sig: keeps Windows editors / Get-Content from decoding as GBK
            with open(path, "w", encoding="utf-8-sig") as fh:
                fh.write(text)
        except OSError as e:
            eprint("[错误] 无法写入 %s (%s)" % (path, e))
            eprint("提示：把 --out 指到当前工作目录，或换一个有写权限的路径。")
            sys.stdout.write(text + "\n")
            return
        out("已写入：%s" % path)
    else:
        out(text)


def write_csv(recs, path):
    cols = ["title", "authors", "year", "venue", "jif", "cited", "cited_per_year",
            "doi", "oa_url", "sources", "url"]
    rows = []
    for r in recs:
        rows.append({
            "title": r.get("title") or "",
            "authors": fmt_authors(r.get("authors") or []),
            "year": r.get("year") or "",
            "venue": r.get("venue") or "",
            "jif": r.get("jif") if r.get("jif") is not None else "",
            "cited": r.get("cited") if r.get("cited") is not None else "",
            "cited_per_year": r.get("py") if r.get("py") is not None else "",
            "doi": r.get("doi") or "",
            "oa_url": (r.get("oa") or {}).get("url") or "",
            "sources": ",".join(r.get("source") or []),
            "url": r.get("url") or "",
        })
    if path:
        try:
            fh = open(path, "w", encoding="utf-8-sig", newline="")
        except OSError as e:
            eprint("[错误] 无法写入 %s (%s)，改为输出到标准输出。" % (path, e))
            fh = None
        if fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
            fh.close()
            out("已写入：%s" % path)
        else:
            w = csv.DictWriter(sys.stdout, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- expand / oa


def cmd_expand(args, cfg):
    con = db()
    doi = norm_doi(args.doi)
    if not doi:
        raise SystemExit("需要 --doi")
    cap = args.max or 50
    forward, backward = [], []

    if "openalex" in (args.sources or "openalex,opencitations").split(","):
        try:
            w = http("https://api.openalex.org/works/https://doi.org/" + doi,
                     {"api_key": cfg["openalex_api_key"]} if cfg.get("openalex_api_key") else None,
                     cfg=cfg, timeout=int(cfg["limits"]["timeout_sec"]))
            oid = (w.get("id") or "").rsplit("/", 1)[-1]
            if args.direction in ("both", "forward") and oid:
                d = http("https://api.openalex.org/works",
                         dict({"filter": "cites:" + oid,
                               "per_page": min(cap, 100),
                               "select": "id,doi,display_name,publication_year,"
                                         "cited_by_count,primary_location,open_access"},
                              **({"api_key": cfg["openalex_api_key"]} if cfg.get("openalex_api_key") else {})),
                         cfg=cfg, timeout=int(cfg["limits"]["timeout_sec"]))
                for it in d.get("results", []):
                    forward.append(mkrec(
                        title=it.get("display_name") or "",
                        year=it.get("publication_year"),
                        doi=it.get("doi"),
                        cited=it.get("cited_by_count"),
                        venue=((it.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
                        oa={"is_oa": bool((it.get("open_access") or {}).get("is_oa")),
                            "status": (it.get("open_access") or {}).get("oa_status", ""),
                            "url": ""},
                        source=["openalex"]))
            if args.direction in ("both", "backward"):
                refs = (w.get("referenced_works") or [])[:cap]
                ids = [x.rsplit("/", 1)[-1] for x in refs]
                for i in range(0, len(ids), 50):
                    chunk = ids[i:i + 50]
                    d = http("https://api.openalex.org/works",
                             dict({"filter": "openalex_id:" + "|".join(chunk),
                                   "per_page": 50,
                                   "select": "id,doi,display_name,publication_year,"
                                             "cited_by_count,primary_location,open_access"},
                                  **({"api_key": cfg["openalex_api_key"]} if cfg.get("openalex_api_key") else {})),
                             cfg=cfg, timeout=int(cfg["limits"]["timeout_sec"]))
                    for it in d.get("results", []):
                        backward.append(mkrec(
                            title=it.get("display_name") or "",
                            year=it.get("publication_year"),
                            doi=it.get("doi"),
                            cited=it.get("cited_by_count"),
                            venue=((it.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
                            source=["openalex"]))
        except Exception as e:
            eprint("[warn] OpenAlex expand 失败:", e)

    if "opencitations" in (args.sources or "openalex,opencitations").split(","):
        for direction, bucket in (("forward", forward), ("backward", backward)):
            if args.direction not in ("both", direction):
                continue
            ep = "citations" if direction == "forward" else "references"
            try:
                d = http("https://opencitations.net/index/api/v1/%s/%s" % (ep, doi),
                         cfg=cfg, timeout=int(cfg["limits"]["timeout_sec"]))
                for item in d[:cap]:
                    other = item.get("citing") if direction == "forward" else item.get("cited")
                    other = norm_doi(other)
                    if not other or other == doi:
                        continue
                    bucket.append(mkrec(doi=other, title="(OpenCitations 仅提供 DOI)",
                                        source=["opencitations"]))
            except Exception as e:
                eprint("[warn] OpenCitations %s 失败: %s" % (direction, e))

    merged = dedupe(forward + backward)
    out("种子 DOI: %s" % doi)
    out("前向（谁引用它，可能重复）: %d；后向（它引用了谁）: %d；去重后 %d"
        % (len(forward), len(backward), len(merged)))
    out("")
    out("| # | 方向 | 年份 | 标题 | DOI | 被引 | 源 |")
    out("|---|---|---|---|---|---|---|")
    for i, r in enumerate(merged, 1):
        direction = "前向" if r in forward else "后向"
        out("| %d | %s | %s | %s | %s | %s | %s |" % (
            i, direction, r.get("year") or "", (r.get("title") or "")[:100],
            r.get("doi") or "", r.get("cited") if r.get("cited") is not None else "",
            ",".join(r.get("source") or [])))
    return merged


def cmd_merge(args, cfg):
    """Merge several --format json results into one deduped list."""
    con = db()
    files = [x.strip() for x in args.input.split(",") if x.strip()]
    recs, statuses, queries = [], [], []
    for f in files:
        try:
            with open(f, encoding="utf-8-sig") as fh:
                d = json.load(fh)
        except Exception as e:  # noqa: BLE001
            eprint("[warn] 读不了 %s: %s" % (f, e))
            continue
        recs.extend(d.get("records") or [])
        if d.get("query"):
            queries.append(str(d["query"]))
        for s in (d.get("statuses") or []):
            s = dict(s)
            s["label"] = "%s@%s" % (s.get("label", "?"), os.path.basename(f))
            statuses.append(s)
    merged = dedupe(recs)
    merged.sort(key=lambda r: (type_rank(r.get("type")),
                               -(r.get("cited") or 0),
                               -(r.get("year") or 0)))
    if args.limit_out:
        merged = merged[: args.limit_out]
    enrich_journals(merged, cfg, con)

    class _A:
        pass

    a = _A()
    a.since = None
    a.until = None
    a.format = args.format
    a.out = args.out
    a.abstracts = args.abstracts
    a.limit_out = args.limit_out
    render(merged, statuses, " | ".join(queries) if queries else "合并结果",
           a, cfg, con)
    return merged


def cmd_digest(args, cfg):
    """Emit a compact abstract digest for relevance triage by the assistant."""
    try:
        with open(args.input, encoding="utf-8-sig") as fh:
            d = json.load(fh)
    except Exception as e:  # noqa: BLE001
        raise SystemExit("读不了 %s: %s" % (args.input, e))
    recs = d.get("records") or []
    if not recs:
        raise SystemExit("该文件没有 records")

    def py(r):
        v = r.get("py")
        if v is None and r.get("cited") is not None and r.get("year"):
            v = round(r["cited"] / max(1, date.today().year - int(r["year"]) + 1), 1)
        return v or 0

    if args.min_cited is not None:
        recs = [r for r in recs if (r.get("cited") or 0) >= args.min_cited]
    if args.since:
        recs = [r for r in recs if r.get("year") and int(r["year"]) >= int(args.since)]
    if args.until:
        recs = [r for r in recs if r.get("year") and int(r["year"]) <= int(args.until)]

    if args.sort == "year":
        recs.sort(key=lambda r: (r.get("year") or 0, r.get("cited") or 0), reverse=True)
    elif args.sort == "cited":
        recs.sort(key=lambda r: (r.get("cited") or 0), reverse=True)
    else:
        recs.sort(key=lambda r: py(r), reverse=True)

    total = len(recs)
    shown = recs[: args.top] if args.top else recs
    out("# 摘要速览（供相关性分级）")
    out("")
    out("共 %d 篇；本次呈现 %d 篇；排序：%s" % (
        total, len(shown),
        {"py": "被引/年 降序", "cited": "总被引 降序", "year": "年份 降序"}[args.sort]))
    out("评估规则见 SKILL.md「相关性分级」；无摘要的条目需标记为「无法判断」。")
    out("")
    for i, r in enumerate(shown, 1):
        ab = clean(r.get("abstract") or "")
        oa = (r.get("oa") or {})
        out("[%d] %s | %s | IF≈%s | 被引 %s (%s/年) | OA:%s" % (
            i, r.get("year") or "—", (r.get("venue") or "—")[:48],
            r.get("jif") if r.get("jif") is not None else "—",
            r.get("cited") if r.get("cited") is not None else "—",
            py(r), oa.get("status") or ("—" if not oa.get("is_oa") else "OA")))
        out("    %s" % (r.get("title") or "")[:200])
        if r.get("doi"):
            out("    DOI %s" % r["doi"])
        if ab:
            out("    " + ab[: args.chars] + ("..." if len(ab) > args.chars else ""))
        else:
            out("    （无摘要，需看原文或换源）")
        out("")
    return None


def cmd_oa(args, cfg):
    con = db()
    dois = []
    if args.doi:
        dois = [norm_doi(x) for x in args.doi.split(",") if x.strip()]
    elif args.file:
        with open(args.file, encoding="utf-8") as fh:
            dois = [norm_doi(x) for x in fh.read().split() if x.strip()]
    if not dois:
        raise SystemExit("需要 --doi 或 --file")
    email = cfg.get("unpaywall_email") or cfg.get("mailto")
    if not email:
        raise SystemExit("Unpaywall 需要邮箱：在 config.json 里填 unpaywall_email")
    out("| DOI | 是否 OA | 状态 | 免费全文 |")
    out("|---|---|---|---|")
    for d in dois:
        try:
            r = http("https://api.unpaywall.org/v2/" + d, {"email": email}, cfg=cfg,
                     timeout=int(cfg["limits"]["timeout_sec"]))
            best = r.get("best_oa_location") or {}
            out("| %s | %s | %s | %s |" % (
                d, "是" if r.get("is_oa") else "否", r.get("oa_status") or "—",
                best.get("url_for_pdf") or best.get("url") or "—"))
        except Exception as e:
            out("| %s | ? | 查询失败 | %s |" % (d, str(e)[:60]))
    return None


# ---------------------------------------------------------------- doctor


def cmd_sources(args, cfg):
    out("%-16s %-4s %-18s %s" % ("name", "tier", "label", "key"))
    out("-" * 60)
    for k, (tier, label, _fn, needs) in SOURCES.items():
        have = ""
        if k == "google_scholar":
            have = "serpapi=%s searchapi=%s" % (
                "有" if cfg.get("serpapi_api_key") else "无",
                "有" if cfg.get("searchapi_api_key") else "无")
        out("%-16s %-4s %-18s %s" % (k, tier, label, have))


def init_config():
    """Create an empty per-user configuration without replacing existing settings."""
    os.makedirs(CFG_DIR, mode=0o700, exist_ok=True)
    try:
        fd = os.open(CFG_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        out("已有配置，保留原文件：%s" % CFG_PATH)
        return
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(DEFAULT_CFG, fh, indent=2)
        fh.write("\n")
    out("已创建空白配置，请用本机文本编辑器填写：%s" % CFG_PATH)


def cmd_doctor(args, cfg):
    out("litsearch doctor  v%s" % VERSION)
    out("-" * 64)
    out("Python      : %s" % sys.version.split()[0])
    out("技能目录    : %s" % SKILL_DIR)
    out("配置目录    : %s" % CFG_DIR)
    out("配置文件    : %s (%s)" % (CFG_PATH, "存在" if os.path.exists(CFG_PATH) else "缺失"))
    for field in ("openalex_api_key", "serpapi_api_key", "searchapi_api_key",
                  "core_api_key", "unpaywall_email", "mailto"):
        out("  %-18s %s" % (field, "已配置" if cfg.get(field) else "未配置"))
    if args.offline:
        out("离线检查完成。凭据有效性需通过对应服务的实际请求验证。")
        return
    try:
        os.makedirs(CFG_DIR, exist_ok=True)
        con = db()
        if _DB_MODE == "file":
            out("缓存数据库  : 可写 %s" % _DB_PATH_USED)
        else:
            out("缓存数据库  : ⚠️ 无可写位置，本会话用内存缓存（配额计数不跨次保存）")
    except Exception as e:
        out("缓存数据库  : ❌ %s" % e)
        con = None
    out("")
    if con is not None:
        m = datetime.now().strftime("%Y-%m")
        d = date.today().isoformat()
        out("")
        out("本月 Google Scholar 用量：SerpAPI %d/%s，SearchApi %d/%s" % (
            usage_count(con, "serpapi", m), cfg["limits"]["serpapi_monthly"],
            usage_count(con, "searchapi", m), cfg["limits"]["searchapi_monthly"]))
        out("今日 OpenAlex 请求数：%d" % usage_count(con, "openalex", d))
    out("")
    out("连通性（每个源跑一次 limit=2 的真实检索）")
    out("-" * 64)
    out("%-16s %-6s %-8s %s" % ("源", "状态", "耗时", "说明"))
    con = con or db()
    probe = args.query or "remote sensing crop mapping"
    for k in SOURCES:
        recs, st = run_one(k, probe, None, None, 2, cfg, con,
                           int(cfg["limits"]["timeout_sec"]) + 10)
        out("%-16s %-6s %-8s %s" % (k, "OK" if st["ok"] else "FAIL",
                                    "%ss" % st["secs"], (st.get("msg") or "")[:70]))
    out("")
    out("提示：Google Scholar 的主服务及回退请求均可能计入各自的额度。")
    return None


# ---------------------------------------------------------------- main


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    p = argparse.ArgumentParser(
        prog="litsearch",
        description="多源文献检索（OpenAlex/Crossref/DOAJ/arXiv/CORE/USGS/NTRS/Google Scholar）")
    p.add_argument("--version", action="version", version="litsearch " + VERSION)
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("search", help="多源关键词检索")
    s.add_argument("query")
    s.add_argument("--since", default=None, help="起始年，如 2015")
    s.add_argument("--until", default=None, help="结束年，如 2026")
    s.add_argument("--max", type=int, default=0, help="每个源最多取多少条")
    s.add_argument("--limit-out", type=int, default=0, help="最终最多输出多少条")
    s.add_argument("--tier", default="ABC", help="A/B/C 组合，或 all")
    s.add_argument("--sources", default=None, help="逗号分隔的源名")
    s.add_argument("--sort", default="cited", choices=["year", "cited"])
    s.add_argument("--abstracts", type=int, default=0, help="额外输出前 N 篇的摘要")
    s.add_argument("--format", default="md", choices=["md", "csv", "json"])
    s.add_argument("--out", default=None, help="输出文件路径")
    s.add_argument("--timeout", type=int, default=0)

    e = sub.add_parser("expand", help="引文雪球（基于一个 DOI）")
    e.add_argument("--doi", required=True)
    e.add_argument("--direction", default="both", choices=["both", "forward", "backward"])
    e.add_argument("--max", type=int, default=50)
    e.add_argument("--sources", default="openalex,opencitations")

    m = sub.add_parser("merge", help="合并多份 --format json 的结果并去重")
    m.add_argument("--input", required=True, help="逗号分隔的 json 文件路径")
    m.add_argument("--limit-out", type=int, default=0)
    m.add_argument("--abstracts", type=int, default=0)
    m.add_argument("--format", default="md", choices=["md", "csv", "json"])
    m.add_argument("--out", default=None)

    dg = sub.add_parser("digest", help="输出摘要速览，供 AI 做相关性分级")
    dg.add_argument("--input", required=True, help="search/merge 产出的 json")
    dg.add_argument("--top", type=int, default=60, help="呈现多少篇（0=全部）")
    dg.add_argument("--chars", type=int, default=350, help="每篇摘要截断长度")
    dg.add_argument("--sort", default="py", choices=["py", "cited", "year"])
    dg.add_argument("--min-cited", type=int, default=None)
    dg.add_argument("--since", default=None)
    dg.add_argument("--until", default=None)

    o = sub.add_parser("oa", help="批量查询开放获取状态")
    o.add_argument("--doi", default=None, help="逗号分隔的 DOI")
    o.add_argument("--file", default=None, help="每行一个 DOI 的文件")

    d = sub.add_parser("doctor", help="自检")
    d.add_argument("--offline", action="store_true", help="只检查本机配置，不联网或消耗配额")
    d.add_argument("--query", default=None, help="连通性测试用查询")

    sub.add_parser("sources", help="列出所有源")
    sub.add_parser("setup", help="在本机创建空配置，保留已有文件")

    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help()
        return 0

    if args.cmd == "setup":
        init_config()
        return 0
    cfg = load_cfg()
    if args.cmd == "search":
        cmd_search(args, cfg)
    elif args.cmd == "expand":
        cmd_expand(args, cfg)
    elif args.cmd == "merge":
        cmd_merge(args, cfg)
    elif args.cmd == "digest":
        cmd_digest(args, cfg)
    elif args.cmd == "oa":
        cmd_oa(args, cfg)
    elif args.cmd == "doctor":
        cmd_doctor(args, cfg)
    elif args.cmd == "sources":
        cmd_sources(args, cfg)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        eprint("中断")
        sys.exit(130)
