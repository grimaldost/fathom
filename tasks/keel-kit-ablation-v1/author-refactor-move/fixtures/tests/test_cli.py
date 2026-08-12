import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tinyetl.cli import build_parser, run


class ParserTests(unittest.TestCase):
    def test_config_is_required(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args([])

    def test_limit_defaults_to_zero(self):
        args = build_parser().parse_args(["--config", "run.json"])
        self.assertEqual(args.limit, 0)


class RunTests(unittest.TestCase):
    def test_writes_every_deduped_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            feed = root / "orders.csv"
            feed.write_text(
                "order_id,region,amount,currency\n"
                "a,north,10.00,EUR\n"
                "a,north,10.00,EUR\n"
                "b,south,5.50,GBP\n",
                encoding="utf-8",
            )
            dest = root / "out.jsonl"
            config = root / "run.json"
            config.write_text(
                json.dumps({"source_uri": str(feed), "dest_path": str(dest)}),
                encoding="utf-8",
            )
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run(["--config", str(config)]), 0)
            self.assertEqual(len(dest.read_text(encoding="utf-8").splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
