"""Client for EPA's Computational Toxicology and Exposure (CTX) APIs.

Endpoint paths verified against EPA's published source code
(github.com/USEPA/ccte-api-chemical and github.com/USEPA/ccte-api-hazard).
"""
import os
import re
import concurrent.futures as cf
import requests

DEFAULT_BASE = "https://comptox.epa.gov/ctx-api/"

CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


class CTXError(Exception):
    pass


def valid_cas(cas: str) -> bool:
    """Check CAS format and check digit."""
    cas = cas.strip()
    if not CAS_RE.match(cas):
        return False
    digits = cas.replace("-", "")
    body, check = digits[:-1], int(digits[-1])
    total = sum(int(d) * (i + 1) for i, d in enumerate(reversed(body)))
    return total % 10 == check


class CTXClient:
    def __init__(self, api_key: str, base_url: str | None = None, timeout: int = 60):
        if not api_key:
            raise CTXError("CTX_API_KEY is not set.")
        self.base = (base_url or os.getenv("CTX_API_BASE") or DEFAULT_BASE).rstrip("/") + "/"
        self.timeout = timeout
        self.headers = {"accept": "application/json", "x-api-key": api_key}

    def _get(self, path: str):
        url = self.base + path.lstrip("/")
        r = requests.get(url, headers=self.headers, timeout=self.timeout)
        if r.status_code in (401, 403):
            raise CTXError("EPA CTX API rejected the API key (HTTP %s)." % r.status_code)
        if r.status_code in (400, 404):
            return []  # EPA returns 400/404 when no data exists for a chemical
        r.raise_for_status()
        try:
            return r.json()
        except ValueError:
            return []

    def resolve_cas(self, cas: str) -> dict:
        """Return the DSSTox record for an exact CAS match."""
        hits = self._get(f"chemical/search/equal/{cas}")
        if isinstance(hits, dict):
            hits = [hits]
        exact = [h for h in hits if (h.get("casrn") or "").strip() == cas]
        pick = (exact or hits or [None])[0]
        if not pick or not pick.get("dtxsid"):
            raise CTXError(f"No chemical found in the CompTox Dashboard for CAS {cas}.")
        return {
            "dtxsid": pick.get("dtxsid"),
            "casrn": pick.get("casrn") or cas,
            "preferredName": pick.get("preferredName"),
            "dashboardUrl": f"https://comptox.epa.gov/dashboard/chemical/details/{pick.get('dtxsid')}",
        }

    def fetch_hazard(self, dtxsid: str) -> dict:
        """Pull every hazard domain used by the summary, in parallel."""
        paths = {
            "toxval": f"hazard/toxval/search/by-dtxsid/{dtxsid}",
            "cancer_summary": f"hazard/cancer-summary/search/by-dtxsid/{dtxsid}",
            "genetox_summary": f"hazard/genetox/summary/search/by-dtxsid/{dtxsid}",
            "genetox_details": f"hazard/genetox/details/search/by-dtxsid/{dtxsid}",
            "iris": f"hazard/iris/search/by-dtxsid/{dtxsid}",
            "pprtv": f"hazard/pprtv/search/by-dtxsid/{dtxsid}",
        }
        out, errors = {}, {}
        with cf.ThreadPoolExecutor(max_workers=6) as ex:
            futs = {ex.submit(self._get, p): k for k, p in paths.items()}
            for f in cf.as_completed(futs):
                k = futs[f]
                try:
                    v = f.result()
                    out[k] = v if isinstance(v, list) else ([v] if v else [])
                except CTXError:
                    raise
                except Exception as e:  # one domain failing should not kill the run
                    out[k] = []
                    errors[k] = str(e)
        out["_errors"] = errors
        return out
