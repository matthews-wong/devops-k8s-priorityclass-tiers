#!/usr/bin/env python3
"""Cross-check priorityClassName usage against the PriorityClasses in manifests/."""
import argparse
import glob
import sys

import yaml

# Built in to every cluster, so never defined in the repo.
BUILTIN_CLASSES = frozenset({"system-cluster-critical", "system-node-critical"})

POD_TEMPLATE_KINDS = frozenset(
    {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job"}
)


def load_docs(paths):
    docs = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for doc in yaml.safe_load_all(handle):
                if isinstance(doc, dict):
                    docs.append((path, doc))
    return docs


def pod_spec(doc):
    """Return the pod spec a workload would create, or None for other kinds."""
    kind = doc.get("kind")
    spec = doc.get("spec") or {}
    if kind == "Pod":
        return spec
    if kind in POD_TEMPLATE_KINDS:
        return (spec.get("template") or {}).get("spec") or {}
    if kind == "CronJob":
        job = (spec.get("jobTemplate") or {}).get("spec") or {}
        return (job.get("template") or {}).get("spec") or {}
    return None


def label(path, doc):
    name = (doc.get("metadata") or {}).get("name", "<unnamed>")
    return f"{path}: {doc.get('kind')}/{name}"


def check_classes(docs):
    errors = []
    classes = {}
    defaults = []
    values = {}
    for path, doc in docs:
        if doc.get("kind") != "PriorityClass":
            continue
        name = doc["metadata"]["name"]
        value = doc.get("value")
        classes[name] = value
        if doc.get("globalDefault"):
            defaults.append(name)
        if value in values:
            errors.append(
                f"{label(path, doc)}: value {value} already used by {values[value]}"
            )
        values[value] = name
    if len(defaults) > 1:
        errors.append(
            f"more than one globalDefault PriorityClass: {', '.join(sorted(defaults))}"
        )
    return classes, errors


def check_workloads(docs, known):
    errors = []
    for path, doc in docs:
        spec = pod_spec(doc)
        if spec is None:
            continue
        name = spec.get("priorityClassName")
        if not name:
            errors.append(f"{label(path, doc)}: no priorityClassName")
        elif name not in known:
            errors.append(f"{label(path, doc)}: unknown priorityClassName '{name}'")
    return errors


def check_quotas(docs, known):
    errors = []
    for path, doc in docs:
        if doc.get("kind") != "ResourceQuota":
            continue
        selector = (doc.get("spec") or {}).get("scopeSelector") or {}
        for expr in selector.get("matchExpressions") or []:
            if expr.get("scopeName") != "PriorityClass":
                continue
            for name in expr.get("values") or []:
                if name not in known:
                    errors.append(
                        f"{label(path, doc)}: scopes unknown PriorityClass '{name}'"
                    )
    return errors


def run_docs(docs):
    classes, errors = check_classes(docs)
    known = set(classes) | BUILTIN_CLASSES
    errors += check_workloads(docs, known)
    errors += check_quotas(docs, known)
    return errors


def run(paths):
    return run_docs(load_docs(paths))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=sorted(glob.glob("manifests/*.yaml")))
    args = parser.parse_args()
    errors = run(args.paths)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"ok: {len(args.paths)} files checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
