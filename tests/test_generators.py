import copy
import sys
import xml.dom.minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generators"))

from loop import loop as L  # noqa: E402
from header import header  # noqa: E402
from skyline import skyline  # noqa: E402
import playground  # noqa: E402


def test_parse_title():
    assert playground.parse_title("gesture: peace") == "peace"
    assert playground.parse_title("Gesture:  Love You") == "love-you"
    assert playground.parse_title("gesture: ✌️") == "peace"
    assert playground.parse_title("gesture: rest") == "stop"
    assert playground.parse_title("gesture: $(rm -rf /)") is None
    assert playground.parse_title("hello") is None


def test_place_fills_then_wraps():
    state = {"steps": [None] * L.STEPS, "next": 0, "history": []}
    for i in range(L.STEPS):
        assert L.place(state, "fist", "u") == i
    assert all(s == "fist" for s in state["steps"])
    assert L.place(state, "peace", "u") == 0
    assert state["steps"][0] == "peace"


def test_svgs_are_valid_xml():
    state = copy.deepcopy(L.load_state())
    samples = L.synthesize(state, loops=1)
    for mode in ("dark", "light"):
        xml.dom.minidom.parseString(L.render_roll(state, mode))
        xml.dom.minidom.parseString(header.render(samples, state, mode))
        xml.dom.minidom.parseString(skyline.render(skyline.load(), mode))
