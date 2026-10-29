import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from flowlog_search import generator, query
from flowlog_search.query import QueryError

ROOT = Path(__file__).resolve().parents[1]


def records(n=120):
    return generator.generate(count=n)


class GeneratorTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(records(), records())

    def test_record_shape(self):
        r = records(1)[0]
        for field in ("time", "src_ip", "dst_ip", "dst_port", "protocol", "action", "bytes"):
            self.assertIn(field, r)
        self.assertIn(r["action"], ("ACCEPT", "REJECT"))

    def test_scanner_mostly_rejected(self):
        rs = [r for r in records(400) if r["src_host"] == "scanner"]
        self.assertGreater(len(rs), 20)
        rejects = [r for r in rs if r["action"] == "REJECT"]
        self.assertGreater(len(rejects) / len(rs), 0.8)


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.src = {"flowlogs": records()}

    def test_where_string_equality(self):
        rows = query.run("search \"flowlogs\" | where action = 'REJECT'", self.src)
        self.assertTrue(rows)
        self.assertTrue(all(r["action"] == "REJECT" for r in rows))

    def test_where_numeric_and_boolean(self):
        rows = query.run("search \"flowlogs\" | where dst_port = 22 and action = 'REJECT'", self.src)
        self.assertTrue(rows)
        self.assertTrue(all(r["dst_port"] == 22 and r["action"] == "REJECT" for r in rows))
        rows2 = query.run("search \"flowlogs\" | where dst_port = 1521 or dst_port = 3389", self.src)
        self.assertTrue(all(r["dst_port"] in (1521, 3389) for r in rows2))

    def test_and_binds_tighter_than_or(self):
        rows = query.run("search \"flowlogs\" | where action = 'REJECT' and dst_port = 22 or dst_port = 3389", self.src)
        for r in rows:
            self.assertTrue((r["action"] == "REJECT" and r["dst_port"] == 22) or r["dst_port"] == 3389)

    def test_comparisons(self):
        rows = query.run("search \"flowlogs\" | where bytes >= 80000", self.src)
        self.assertTrue(all(r["bytes"] >= 80000 for r in rows))
        rows = query.run("search \"flowlogs\" | where dst_port < 100", self.src)
        self.assertTrue(all(r["dst_port"] < 100 for r in rows))

    def test_sort_and_head(self):
        rows = query.run("search \"flowlogs\" | where action = 'ACCEPT' | sort by bytes | head 5", self.src)
        self.assertEqual(len(rows), 5)
        self.assertEqual([r["bytes"] for r in rows], sorted((r["bytes"] for r in rows), reverse=True))
        rows = query.run("search \"flowlogs\" | sort by time asc | head 3", self.src)
        self.assertEqual([r["time"] for r in rows], sorted(r["time"] for r in rows))

    def test_unknown_source(self):
        with self.assertRaises(QueryError):
            query.run("search \"nope\"", self.src)

    def test_bad_syntax_errors(self):
        for bad in ("where action = 'REJECT'",
                    "search \"flowlogs\" | where action ~~ 'REJECT'",
                    "search \"flowlogs\" | where bogus_field = 1",
                    "search \"flowlogs\" | tail 5",
                    "search \"flowlogs\" | sort by bytes sideways",
                    "search \"flowlogs\" | head abc"):
            with self.assertRaises(QueryError, msg=bad):
                query.run(bad, self.src)

    def test_all_example_queries_run(self):
        lines = [l.strip() for l in (ROOT / "examples" / "queries.txt").read_text().splitlines()
                 if l.strip() and not l.startswith("#")]
        self.assertEqual(len(lines), 4)
        for line in lines:
            self.assertTrue(query.run(line, self.src), line)


class DemoTests(unittest.TestCase):
    def test_demo_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            dump = Path(d) / "records.json"
            proc = subprocess.run(
                [sys.executable, "-m", "flowlog_search.demo", "--count", "200", "--dump", str(dump)],
                capture_output=True, text=True, cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("generated 200 synthetic flow-log records", proc.stdout)
            self.assertIn("query> search", proc.stdout)
            self.assertIn("record(s))", proc.stdout)
            dumped = json.loads(dump.read_text())
            self.assertEqual(len(dumped), 200)

    def test_validate_script(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate.py")],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("validate: OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
