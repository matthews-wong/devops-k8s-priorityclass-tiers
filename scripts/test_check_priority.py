import copy
import unittest

import check_priority as cp

CLASS = {
    "kind": "PriorityClass",
    "metadata": {"name": "standard"},
    "value": 1000,
    "globalDefault": True,
}


def pc(name, value, default=False):
    doc = copy.deepcopy(CLASS)
    doc["metadata"]["name"] = name
    doc["value"] = value
    doc["globalDefault"] = default
    return ("pc.yaml", doc)


def deployment(class_name=None):
    spec = {"containers": []}
    if class_name:
        spec["priorityClassName"] = class_name
    return (
        "app.yaml",
        {
            "kind": "Deployment",
            "metadata": {"name": "app"},
            "spec": {"template": {"spec": spec}},
        },
    )


def cronjob(class_name):
    return (
        "job.yaml",
        {
            "kind": "CronJob",
            "metadata": {"name": "sweep"},
            "spec": {
                "jobTemplate": {
                    "spec": {
                        "template": {"spec": {"priorityClassName": class_name}}
                    }
                }
            },
        },
    )


def quota(*names):
    return (
        "quota.yaml",
        {
            "kind": "ResourceQuota",
            "metadata": {"name": "q"},
            "spec": {
                "scopeSelector": {
                    "matchExpressions": [
                        {"scopeName": "PriorityClass", "operator": "In", "values": list(names)}
                    ]
                }
            },
        },
    )


class ClassTests(unittest.TestCase):
    def test_duplicate_value_is_reported(self):
        _, errors = cp.check_classes([pc("a", 5), pc("b", 5)])
        self.assertEqual(len(errors), 1)
        self.assertIn("value 5", errors[0])

    def test_two_global_defaults_are_reported(self):
        _, errors = cp.check_classes([pc("a", 1, True), pc("b", 2, True)])
        self.assertEqual(len(errors), 1)
        self.assertIn("globalDefault", errors[0])

    def test_valid_classes_pass(self):
        classes, errors = cp.check_classes([pc("a", 1, True), pc("b", 2)])
        self.assertEqual(errors, [])
        self.assertEqual(set(classes), {"a", "b"})


class WorkloadTests(unittest.TestCase):
    def test_missing_class_is_reported(self):
        errors = cp.check_workloads([deployment()], {"standard"})
        self.assertIn("no priorityClassName", errors[0])

    def test_unknown_class_names_the_value(self):
        errors = cp.check_workloads([deployment("standrad")], {"standard"})
        self.assertIn("'standrad'", errors[0])

    def test_cronjob_template_is_checked(self):
        errors = cp.check_workloads([cronjob("nope")], {"standard"})
        self.assertIn("'nope'", errors[0])

    def test_builtin_class_is_accepted(self):
        docs = [deployment("system-cluster-critical")]
        self.assertEqual(cp.run_docs(docs), [])

    def test_non_workloads_are_ignored(self):
        docs = [("svc.yaml", {"kind": "Service", "metadata": {"name": "s"}})]
        self.assertEqual(cp.check_workloads(docs, set()), [])


class QuotaTests(unittest.TestCase):
    def test_unknown_scope_class_is_reported(self):
        errors = cp.check_quotas([quota("ghost")], {"standard"})
        self.assertIn("'ghost'", errors[0])

    def test_known_scope_class_passes(self):
        self.assertEqual(cp.check_quotas([quota("standard")], {"standard"}), [])


if __name__ == "__main__":
    unittest.main()
