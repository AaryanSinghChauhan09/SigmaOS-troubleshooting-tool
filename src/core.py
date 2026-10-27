"""Troubleshooting/report generator for SigmaOS-troubleshooting-tool
(inspired by mintreport).

Principles: facts are injected (never probed from the real system here),
reports are pure renderings of those facts, comparisons are deterministic
diffs, and export is the only write (to an explicit path). Collecting is
planned, not executed.
"""
import argparse, json, os, sys

ENGINE = {
    "name": "sigma-report",
    "summary": "Collect-plan, render, compare and export system reports",
    "language": "python",
    "verbs": ["collect-plan", "report", "compare", "export"],
    "principles": ["Plan Before Apply", "Pure Rendering", "Determinism",
                   "KISS", "Least Astonishment"],
}

cli_doc = """\
$ sigma-report collect-plan --profile desktop
$ sigma-report report --facts facts.json --format text
$ sigma-report compare --before before.json --after after.json
$ sigma-report export --facts facts.json --out report.html
"""

COLLECTION_PROFILES = {
    "minimal": ["os-release", "kernel", "uptime"],
    "desktop": ["os-release", "kernel", "uptime", "display-server",
                "desktop-session", "graphics-driver", "disk-usage",
                "failed-services", "recent-errors"],
    "full": ["os-release", "kernel", "uptime", "display-server",
             "desktop-session", "graphics-driver", "disk-usage",
             "failed-services", "recent-errors", "packages-changed",
             "hardware-list", "network-state"],
}

SEVERITY_ORDER = {"ok": 0, "info": 1, "warn": 2, "error": 3}

CHECKS = (
    ("disk-usage", "root filesystem usage", "percent_used", 90, 97),
    ("memory-usage", "memory usage", "percent_used", 85, 95),
    ("failed-services", "failed services", "count", 1, 4),
    ("recent-errors", "recent log errors", "count", 5, 20),
)


class ReportError(Exception):
    pass


def plan_collect(profile):
    """Pure: what would be collected for a profile (commands, not run)."""
    if profile not in COLLECTION_PROFILES:
        raise ReportError(f"unknown profile {profile!r}; "
                          f"choose from {sorted(COLLECTION_PROFILES)}")
    plan = []
    for item in COLLECTION_PROFILES[profile]:
        plan.append({"fact": item, "source": _SOURCE_FOR[item],
                     "command": _SOURCE_FOR[item]})
    return {"profile": profile, "count": len(plan), "steps": plan,
            "note": "plan only; nothing is executed by this verb"}


_SOURCE_FOR = {
    "os-release": "cat /etc/os-release",
    "kernel": "uname -r",
    "uptime": "uptime -p",
    "display-server": "echo $XDG_SESSION_TYPE",
    "desktop-session": "echo $XDG_CURRENT_DESKTOP",
    "graphics-driver": "glxinfo -B",
    "disk-usage": "df -hP /",
    "failed-services": "systemctl --failed --no-legend",
    "recent-errors": "journalctl -p err -b --no-pager",
    "packages-changed": "grep -h install /var/log/dpkg.log | tail -50",
    "hardware-list": "lspci -nn",
    "network-state": "ip -br addr",
}


def evaluate_checks(facts):
    """Pure: run threshold checks against injected facts -> findings."""
    findings = []
    for key, label, field, warn_at, err_at in CHECKS:
        section = facts.get(key)
        if section is None:
            continue
        value = section.get(field) if isinstance(section, dict) else section
        if not isinstance(value, (int, float)):
            continue
        if value >= err_at:
            severity = "error"
        elif value >= warn_at:
            severity = "warn"
        else:
            severity = "ok"
        findings.append({"check": key, "label": label, "value": value,
                         "severity": severity,
                         "detail": f"{label}: {value} (warn >= {warn_at}, "
                                   f"error >= {err_at})"})
    return findings


def render_report(facts, fmt="text"):
    """Pure rendering of facts + derived findings."""
    findings = evaluate_checks(facts)
    worst = max((SEVERITY_ORDER[f["severity"]] for f in findings), default=0)
    overall = [k for k, v in SEVERITY_ORDER.items() if v == worst][0]
    if fmt == "json":
        return json.dumps({"facts": facts, "findings": findings,
                           "overall": overall}, indent=2, sort_keys=True)
    if fmt == "html":
        rows = "\n".join(
            f"<tr class='{f['severity']}'><td>{f['label']}</td>"
            f"<td>{f['value']}</td><td>{f['severity']}</td></tr>"
            for f in findings)
        return ("<!doctype html><title>SigmaOS report</title>"
                f"<h1>SigmaOS report: {overall}</h1>"
                "<table>" + rows + "</table>")
    lines = [f"SigmaOS system report -- overall: {overall}", ""]
    for section in sorted(facts):
        value = facts[section]
        if isinstance(value, dict):
            lines.append(f"[{section}]")
            for k in sorted(value):
                lines.append(f"  {k}: {value[k]}")
        else:
            lines.append(f"[{section}] {value}")
    lines.append("")
    lines.append("findings:")
    for f in findings:
        lines.append(f"  {f['severity'].upper():5} {f['detail']}")
    return "\n".join(lines) + "\n"


def compare(before, after):
    """Pure: deterministic diff of two fact snapshots."""
    changes = []
    flat_b, flat_a = _flatten(before), _flatten(after)
    for key in sorted(set(flat_b) | set(flat_a)):
        old, new = flat_b.get(key), flat_a.get(key)
        if old == new:
            continue
        if key not in flat_b:
            kind = "added"
        elif key not in flat_a:
            kind = "removed"
        else:
            kind = "changed"
        changes.append({"key": key, "kind": kind, "before": old, "after": new})
    return changes


def _flatten(node, prefix=""):
    out = {}
    for k in sorted(node):
        key = f"{prefix}.{k}" if prefix else k
        v = node[k]
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


def export_report(facts, out_path, fmt=None):
    """Side-effecting but explicit: render + write to out_path.

    fmt defaults to sniffing the extension (.txt/.json/.html), else text.
    """
    if fmt is None:
        ext = os.path.splitext(out_path)[1].lstrip(".").lower()
        fmt = {"txt": "text", "json": "json", "html": "html"}.get(ext, "text")
    body = render_report(facts, fmt)
    directory = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(directory, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return {"path": out_path, "bytes": len(body.encode()),
            "format": fmt, "overall": _overall(facts)}


def _overall(facts):
    findings = evaluate_checks(facts)
    worst = max((SEVERITY_ORDER[f["severity"]] for f in findings), default=0)
    return [k for k, v in SEVERITY_ORDER.items() if v == worst][0]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=ENGINE["name"], description=ENGINE["summary"])
    sub = p.add_subparsers(dest="cmd", required=True)
    cp = sub.add_parser("collect-plan", help="show what would be collected")
    cp.add_argument("--profile", default="desktop",
                    choices=sorted(COLLECTION_PROFILES))
    rp = sub.add_parser("report", help="render a report from a facts file")
    rp.add_argument("--facts", required=True)
    rp.add_argument("--format", default="text", choices=["text", "json", "html"])
    cm = sub.add_parser("compare", help="diff two fact snapshots")
    cm.add_argument("--before", required=True)
    cm.add_argument("--after", required=True)
    ex = sub.add_parser("export", help="render + write a report file")
    ex.add_argument("--facts", required=True)
    ex.add_argument("--out", required=True)
    ex.add_argument("--format", default=None,
                    help="text|json|html (default: from output extension)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "collect-plan":
            print(json.dumps(plan_collect(args.profile), indent=2))
        elif args.cmd == "report":
            with open(args.facts) as fh:
                print(render_report(json.load(fh), args.format))
        elif args.cmd == "compare":
            with open(args.before) as fh:
                before = json.load(fh)
            with open(args.after) as fh:
                after = json.load(fh)
            changes = compare(before, after)
            if not changes:
                print("no changes")
            for c in changes:
                print(f"{c['kind']:8} {c['key']}: "
                      f"{c['before']!r} -> {c['after']!r}")
        elif args.cmd == "export":
            with open(args.facts) as fh:
                facts = json.load(fh)
            info = export_report(facts, args.out, args.format)
            print(f"wrote {info['path']} ({info['bytes']} bytes, "
                  f"overall: {info['overall']})")
        return 0
    except (ReportError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def self_test() -> None:
    # collect planning is pure and profile-driven
    plan = plan_collect("minimal")
    assert plan["count"] == 3
    assert [s["fact"] for s in plan["steps"]] == ["os-release", "kernel", "uptime"]
    assert plan["steps"][1]["command"] == "uname -r"
    assert "nothing is executed" in plan["note"]
    full = plan_collect("full")
    assert full["count"] == 12
    try:
        plan_collect("kitchen-sink")
    except ReportError as e:
        assert "unknown profile" in str(e)
    else:
        raise AssertionError("bad profile not caught")

    # facts -> findings with realistic thresholds
    facts = {
        "os-release": {"name": "SigmaOS", "version": "22.3"},
        "kernel": "6.8.0-31-generic",
        "disk-usage": {"percent_used": 93},
        "failed-services": {"count": 2},
        "recent-errors": {"count": 4},
        "memory-usage": {"percent_used": 61},
    }
    findings = evaluate_checks(facts)
    by_check = {f["check"]: f for f in findings}
    assert by_check["disk-usage"]["severity"] == "warn"       # 90 <= 93 < 97
    assert by_check["memory-usage"]["severity"] == "ok"
    assert by_check["failed-services"]["severity"] == "warn"
    assert by_check["recent-errors"]["severity"] == "ok"

    text = render_report(facts, "text")
    assert text.startswith("SigmaOS system report")
    assert "[kernel] 6.8.0-31-generic" in text
    assert "WARN" in text and "OK" in text and "ERROR" not in text
    as_json = json.loads(render_report(facts, "json"))
    assert as_json["overall"] == "warn"
    assert len(as_json["findings"]) == 4  # one per registered check present
    html = render_report(facts, "html")
    assert html.startswith("<!doctype html>") and "class='warn'" in html
    sev_err = render_report({"disk-usage": {"percent_used": 99}}, "html")
    assert "class='error'" in sev_err

    healthy = {"disk-usage": {"percent_used": 42}, "kernel": "6.8.0-31"}
    assert json.loads(render_report(healthy, "json"))["overall"] == "ok"
    assert render_report({}, "text").endswith("findings:\n")

    # comparisons
    before = {"kernel": "6.8.0-31", "driver": {"name": "nouveau"},
              "desktop": "Cinnamon"}
    after = {"kernel": "6.8.0-40", "driver": {"name": "nvidia"},
             "session": "wayland"}
    changes = compare(before, after)
    kinds = {c["key"]: c for c in changes}
    assert kinds["kernel"]["kind"] == "changed"
    assert kinds["kernel"]["before"] == "6.8.0-31" and kinds["kernel"]["after"] == "6.8.0-40"
    assert kinds["driver.name"]["after"] == "nvidia"
    assert kinds["session"]["kind"] == "added"
    assert kinds["desktop"]["kind"] == "removed"
    assert compare(before, before) == []

    # export (explicit path only, under tempdir)
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "sub", "report.json")
        info = export_report(facts, out, "json")
        assert info["bytes"] > 0 and info["overall"] == "warn"
        written = json.load(open(out))
        assert written["facts"]["kernel"] == "6.8.0-31-generic"
        # extension sniffing
        out2 = os.path.join(d, "report.html")
        export_report(facts, out2)
        assert open(out2).read().startswith("<!doctype html>")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
