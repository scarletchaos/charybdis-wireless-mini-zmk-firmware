"""Static regression checks for the personal QWERTY layout and BT roles.

Run: python3 scripts/test_config.py
These checks do not replace firmware builds or on-keyboard hold/tap testing.
"""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return (ROOT / relative).read_text()


def layers(text):
    """Read the simple layer binding lists used by this repository."""
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    keymap = text.split('compatible = "zmk,keymap";', 1)[1]
    result = {}
    for name, body in re.findall(r"(\w+)\s*\{([^{}]*)\};", keymap):
        bindings = re.search(r"bindings\s*=\s*<(.*?)>;", body, re.S)
        if bindings:
            result[name] = [
                " ".join(binding.split())
                for binding in re.findall(r"&[^&]+", bindings[1])
            ]
    return result


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.text = read("config/keymaps/qwerty.keymap")
        self.layers = layers(self.text)

    def test_every_layer_has_41_keys(self):
        for path in (ROOT / "config/keymaps").glob("*.keymap"):
            parsed = layers(path.read_text())
            self.assertTrue(parsed, path.name)
            for name, bindings in parsed.items():
                with self.subTest(keymap=path.name, layer=name):
                    self.assertEqual(len(bindings), 41)

    def test_russian_pc_keys(self):
        self.assertEqual(self.layers["BASE"][0], "&kp ESC")
        self.assertEqual(self.layers["BASE"][11], "&kp LBKT")
        self.assertEqual(self.layers["BASE"][23], "&kp SQT")
        self.assertEqual(self.layers["NUM"][0], "&kp GRAVE")
        self.assertEqual(self.layers["NUM"][11], "&kp RBKT")

    def test_home_row_mods_match_each_hand(self):
        base = self.layers["BASE"]
        self.assertEqual(base[13:17], [
            "&ht_left_tp LCMD A", "&ht_left LALT S",
            "&ht_left LSHFT D", "&ht_left LCTRL F",
        ])
        self.assertEqual(base[19:23], [
            "&ht_right RCTRL J", "&ht_right RSHFT K",
            "&ht_right_tp RALT L", "&ht_right_tp RCMD SEMICOLON",
        ])

    def test_base_thumbs_match_large_keyboard_top_row(self):
        self.assertEqual(self.layers["BASE"][36:], [
            "&kp BACKSPACE", "&lt 3 SPACE", "&mo 1",
            "&mo 2", "&kp ENTER",
        ])

    def test_numpad_is_preserved(self):
        num = self.layers["NUM"]
        for row, start in enumerate([7, 19, 31]):
            first = [7, 4, 1][row]
            self.assertEqual(num[start:start + 3], [
                f"&mm_f{n}" for n in range(first, first + 3)
            ])
        self.assertEqual(num[39], "&kp N0")

    def test_navigation_uses_hjkl(self):
        self.assertEqual(self.layers["NAV"][18:22], [
            "&kp LEFT_ARROW", "&kp DOWN", "&kp UP", "&kp RIGHT_ARROW",
        ])
        self.assertEqual(self.layers["NAV"][22], "&h_split")

    def test_symbol_layer_covers_ascii_punctuation(self):
        codes = (
            "EXCLAMATION AT HASH DLLR PRCNT CARET AMPS ASTRK LPAR RPAR "
            "BSLH FSLH MINUS EQUAL PLUS LBKT RBKT LBRC RBRC SEMICOLON SQT "
            "GRAVE TILDE UNDER LT GT PIPE COMMA DOT COLON DQT QUESTION"
        ).split()
        symbols = self.layers["SYM"]
        self.assertEqual(len(codes), 32)
        self.assertTrue({f"&kp {code}" for code in codes}.issubset(symbols))
        self.assertTrue(all(b.startswith("&kp ") or b == "&trans" for b in symbols))
        self.assertEqual(symbols[36:], [
            "&kp BACKSPACE", "&trans", "&trans", "&kp SPACE", "&kp ENTER",
        ])

    def test_precision_mouse_and_scroll(self):
        self.assertEqual(list(self.layers)[6:8], ["MOUSE", "SCROLL"])
        self.assertEqual(self.layers["BASE"][25:27], ["&lt_mouse 6 Z", "&kp X"])
        self.assertEqual(self.layers["MOUSE"][25:27], ["&trans", "&mo 7"])
        self.assertEqual(self.layers["MOUSE"][39:], ["&mkp RCLK", "&mkp LCLK"])
        self.assertTrue(all(b == "&trans" for b in self.layers["SCROLL"]))
        self.assertIn("/delete-node/ combo_left_click;", self.text)
        pointer = read("config/trackball/charybdis_pointer.dtsi")
        self.assertLess(pointer.index("scroller:"), pointer.index("slow_pointer:"))
        self.assertRegex(pointer, r"scroller:\s*scroller\s*\{\s*layers\s*=\s*<7>")
        self.assertRegex(pointer, r"slow_pointer:\s*slow_pointer\s*\{\s*layers\s*=\s*<6>")

    def test_scroll_direction_without_extra_axis_inversion(self):
        pointer = read("config/trackball/charybdis_pointer.dtsi")
        scroll = pointer.split("scroller: scroller {", 1)[1].split("};", 1)[0]
        self.assertEqual(re.findall(r"&(\w+)", scroll), [
            "zip_xy_scaler", "zip_xy_to_scroll_mapper",
        ])
        self.assertIn("&zip_xy_scaler 1 15", scroll)
        self.assertIn("input-processors = <&zip_xy_scaler 5 5>;", pointer)
        self.assertIn("input-processors = <&zip_xy_scaler 2 6>;", pointer)

    def test_left_central_and_right_sensor(self):
        prefix = "boards/shields/"
        left = read(prefix + "charybdis_left_bt/charybdis_left_bt.conf")
        right = read(prefix + "charybdis_right_bt/charybdis_right_bt.conf")
        self.assertIn("CONFIG_ZMK_SPLIT_ROLE_CENTRAL=y", left)
        self.assertIn("CONFIG_ZMK_STUDIO=y", left)
        self.assertIn("CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING=y", left)
        self.assertIn("CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_PROXY=y", left)
        self.assertNotIn("CONFIG_ZMK_USB=n", left)
        self.assertFalse((ROOT / "config/charybdis/charybdis_left.conf").exists())
        self.assertIn("CONFIG_ZMK_SPLIT_ROLE_CENTRAL=n", right)
        self.assertIn("CONFIG_ZMK_USB=n", right)
        self.assertIn("CONFIG_PMW3610_ALT=y", right)
        self.assertNotIn("CONFIG_PMW3610_ALT=y", left)
        left_overlay = read(prefix + "charybdis_left_bt/charybdis_left_bt.overlay")
        right_overlay = read(prefix + "charybdis_right_bt/charybdis_right_bt.overlay")
        self.assertIn("device = <&trackball_split>;", left_overlay)
        self.assertIn("charybdis_pointer.dtsi", left_overlay)
        self.assertIn("&trackball_split {", right_overlay)
        self.assertIn("device = <&trackball>;", right_overlay)
        self.assertNotIn("charybdis_pointer.dtsi", right_overlay)


if __name__ == "__main__":
    unittest.main()
