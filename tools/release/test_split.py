#!/usr/bin/env python3
"""Unit tests for the release split: python3 -m unittest tools/release/test_split.py  (standard library only)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import combine  # noqa: E402
import matrix  # noqa: E402


def image(name, verified):
    return {"name": name, "verified_on_hardware": {"verified": verified, "text": "x"}}


class SplitStreams(unittest.TestCase):
    def test_mixed_images_go_to_their_stream(self):
        ok, preview = combine.split_streams([image("a", True), image("b", False), image("c", True)])
        self.assertEqual([i["name"] for i in ok], ["a", "c"])
        self.assertEqual([i["name"] for i in preview], ["b"])

    def test_no_preview_when_everything_is_verified(self):
        ok, preview = combine.split_streams([image("a", True)])
        self.assertEqual(len(ok), 1)
        self.assertEqual(preview, [])
        ok, preview = combine.split_streams([image("a", False)])
        self.assertEqual(ok, [])
        self.assertEqual(len(preview), 1)


class VerifiedFlag(unittest.TestCase):
    CFG = {"boards": {"b": {"dir": "boards/b", "verified_on_hardware": True, "verified_note": "rev 1 on carrier",
                            "variants": {"v1": {"kind": "sdcard", "build": [], "deploy": [], "title": "t"},
                                         "v2": {"kind": "bundle", "build": [], "deploy": [], "title": "t",
                                                "verified_on_hardware": False, "verified_note": "not run"}}}}}

    def test_board_flag_is_inherited_and_a_variant_can_override_it(self):
        self.assertEqual(matrix.merged(self.CFG, "b", "v1")["verified_on_hardware"], {"verified": True, "text": "rev 1 on carrier"})
        self.assertEqual(matrix.merged(self.CFG, "b", "v2")["verified_on_hardware"], {"verified": False, "text": "not run"})

    def test_flag_must_be_a_boolean(self):
        self.CFG["boards"]["b"]["variants"]["v1"]["verified_on_hardware"] = "yes"
        with self.assertRaises(SystemExit):
            matrix.merged(self.CFG, "b", "v1")
        del self.CFG["boards"]["b"]["variants"]["v1"]["verified_on_hardware"]


if __name__ == "__main__":
    unittest.main()
