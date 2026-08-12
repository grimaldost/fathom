import json
import unittest

from logkit.fields import base_fields, render


class FieldTests(unittest.TestCase):
    def test_base_fields_have_pid(self):
        self.assertIn("pid", base_fields())

    def test_render_sorts_keys(self):
        self.assertEqual(json.loads(render({"b": 1, "a": 2})), {"a": 2, "b": 1})


if __name__ == "__main__":
    unittest.main()
