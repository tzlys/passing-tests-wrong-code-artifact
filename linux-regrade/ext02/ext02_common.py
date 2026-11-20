"""EXT-02 shared helpers: anonymous S3 listing/download over HTTPS (stdlib only), deterministic sampling."""
import hashlib
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BUCKET = "https://swe-bench-submissions.s3.amazonaws.com"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
HERE = os.path.dirname(os.path.abspath(__file__))
MAX_BYTES = 20 * 1024 * 1024
PER_ENTRY = 40


def entries():
    with open(os.path.join(HERE, "..", "ext01", "entries.txt")) as f:
        return [l.split()[0] for l in f if l.strip() and not l.startswith("#")]


def _get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 * (k + 1))


def list_objects(prefix):
    out, token = [], None
    while True:
        q = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            q["continuation-token"] = token
        root = ET.fromstring(_get(BUCKET + "/?" + urllib.parse.urlencode(q)))
        for c in root.findall(NS + "Contents"):
            out.append((c.find(NS + "Key").text, int(c.find(NS + "Size").text)))
        if root.findtext(NS + "IsTruncated") == "true":
            token = root.findtext(NS + "NextContinuationToken")
        else:
            return out


def download(key):
    return _get(BUCKET + "/" + urllib.parse.quote(key))


def instance_of(entry, key):
    rest = key[len(f"lite/{entry}/trajs/"):]
    if "/" in rest:
        return rest.split("/", 1)[0]
    stem = rest
    for ext in (".traj.json", ".traj", ".json", ".jsonl", ".md", ".log", ".txt", ".yaml", ".yml"):
        if stem.endswith(ext):
            return stem[: -len(ext)]
    return stem.rsplit(".", 1)[0]


def sample(entry, objs):
    """Return (chosen instances -> [(key,size)], skipped_too_large)."""
    by_inst = {}
    for key, size in objs:
        by_inst.setdefault(instance_of(entry, key), []).append((key, size))
    order = sorted(by_inst, key=lambda i: hashlib.sha256(f"{entry}/{i}".encode()).hexdigest())
    chosen, too_large = {}, 0
    for inst in order[:PER_ENTRY]:
        keep = []
        for key, size in sorted(by_inst[inst]):
            if size > MAX_BYTES:
                too_large += 1
            else:
                keep.append((key, size))
        chosen[inst] = keep
    return chosen, too_large, len(by_inst)
