# devops-k8s-priorityclass-tiers

Three PriorityClass tiers for a small cluster, plus workloads that use them and a
checker that keeps the two in sync.

Under memory pressure the scheduler preempts lower-priority pods first. That only
helps if every workload names a class on purpose. A pod with no `priorityClassName`
silently gets priority 0 (or the `globalDefault` class), and a typo in the name is
rejected only at admission time, after the manifest has already been merged.

## Tiers

| Class | Value | Preemption | Intended for |
|-------|-------|------------|--------------|
| `platform-critical` | 100000 | may preempt | ingress, DNS-like shared services |
| `business-standard` | 10000 | may preempt | user-facing apps (the default) |
| `batch-low` | 100 | never preempts | CronJobs and other restartable work |

`business-standard` is the `globalDefault`, so an unlabelled pod lands in the middle
tier rather than the bottom one. Values stay far below the 1 billion reserved for the
built-in `system-*` classes.

## Layout

- `manifests/` priority classes, a namespace, a quota scoped to the batch tier,
  a web Deployment and a batch CronJob
- `scripts/check_priority.py` cross-checks `priorityClassName` against the classes
  defined in the manifests
- `Makefile` runs everything with `make validate`

## Validate

Needs `kubeconform`, `actionlint` and Python 3 with PyYAML.

    make validate

The checker fails when a workload has no class, names a class that is not defined,
when more than one class is `globalDefault`, or when two classes share a value.
