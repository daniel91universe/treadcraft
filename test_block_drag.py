import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from app import TreadmillApp


class WorkoutTree:
    """Treeview subset with real parent/index changes during previews."""

    def __init__(self, app):
        self.app = app
        self.reset()

    def reset(self):
        self.roots = []
        self.parents = {}
        self.children = {}
        self.open = {}
        self.app.tree_item_data = {}
        for index, entry in enumerate(self.app.blocks):
            iid = f"block_{index}" if entry["type"] == "block" else f"standalone_{index}"
            self.roots.append(iid)
            self.parents[iid] = ""
            if entry["type"] == "block":
                self.app.tree_item_data[iid] = {"kind": "block", "block": entry}
                self.open[iid] = True
                self.children[iid] = []
                for offset, segment in enumerate(entry["segments"]):
                    child = f"segment_{index}_{offset}"
                    self.parents[child] = iid
                    self.children[iid].append(child)
                    self.app.tree_item_data[child] = {
                        "kind": "segment", "segment": segment, "parent_block": entry,
                        "wrapper": None,
                    }
            else:
                self.app.tree_item_data[iid] = {
                    "kind": "segment", "segment": entry["segment"],
                    "parent_block": None, "wrapper": entry,
                }

    def visible(self):
        rows = []
        for iid in self.roots:
            rows.append(iid)
            if self.open.get(iid):
                rows.extend(self.children[iid])
        return rows

    def bbox(self, iid):
        return (0, 20 + self.visible().index(iid) * 20, 300, 20)

    def identify_row(self, y):
        offset = (y - 20) // 20
        rows = self.visible()
        return rows[offset] if 0 <= offset < len(rows) else ""

    def identify_region(self, x, y):
        return "heading" if y < 20 else "tree"

    def winfo_width(self):
        return 300

    def winfo_height(self):
        return 500

    def parent(self, iid):
        return self.parents[iid]

    def index(self, iid):
        parent = self.parents[iid]
        return (self.children[parent] if parent else self.roots).index(iid)

    def move(self, iid, parent, index):
        old_parent = self.parents[iid]
        old = self.children[old_parent] if old_parent else self.roots
        old.remove(iid)
        rows = self.children[parent] if parent else self.roots
        rows.insert(len(rows) if index == "end" else index, iid)
        self.parents[iid] = parent

    def item(self, iid, option=None, **kwargs):
        if option == "open":
            return self.open[iid]
        self.open.update({iid: kwargs["open"]})

    def selection_set(self, iid):
        self.selected = iid

    def selection(self):
        return (self.selected,) if getattr(self, "selected", "") else ()

    def selection_remove(self, *items):
        self.selected = ""

    def focus(self, iid):
        self.focused = iid

    def see(self, iid):
        self.seen = iid


class BlockDragTests(unittest.TestCase):
    def setUp(self):
        self.first = {"type": "block", "name": "A", "repetitions": 3,
                      "segments": [{"name": "Run"}, {"name": "Recovery"}]}
        self.second = {"type": "block", "name": "B", "repetitions": 2,
                       "segments": [{"name": "Other"}]}
        self.outside = {"type": "segment", "segment": {"name": "Outside"}}
        self.app = TreadmillApp.__new__(TreadmillApp)
        self.app.blocks = [self.first, self.outside, self.second]
        self.tree = self.app.tree = WorkoutTree(self.app)
        self.app.refresh_tree = Mock(side_effect=self.tree.reset)
        self.app.reset_block_editor = Mock()
        self.app.reset_segment_editor = Mock()
        self.app.update_summary = Mock()
        self.app.on_tree_select = Mock()

    def point(self, iid, after=False):
        _, y, _, height = self.tree.bbox(iid)
        return SimpleNamespace(x=40, y=y + (height - 2 if after else 2))

    def start(self, iid):
        self.app.start_tree_drag(self.point(iid))

    def drop(self, event):
        self.app.show_tree_drag_preview(event)
        self.app.finish_tree_drag(event)

    def test_preview_moves_original_subtree_without_changing_data(self):
        before = copy.deepcopy(self.app.blocks)
        self.start("block_0")
        self.app.show_tree_drag_preview(self.point("block_2", after=True))
        self.assertEqual(self.app.blocks, before)
        self.assertEqual(self.tree.roots[-1], "block_0")
        self.assertEqual(self.tree.children["block_0"], ["segment_0_0", "segment_0_1"])

    def test_block_moves_down_and_remains_selected(self):
        self.start("block_0")
        self.drop(self.point("block_2", after=True))
        self.assertEqual(self.app.blocks, [self.outside, self.second, self.first])
        self.assertEqual(self.tree.selected, "block_2")
        self.assertEqual(self.first["repetitions"], 3)
        self.assertEqual([s["name"] for s in self.first["segments"]], ["Run", "Recovery"])

    def test_block_moves_up(self):
        self.start("block_2")
        self.drop(self.point("block_0"))
        self.assertIs(self.app.blocks[0], self.second)

    def test_drop_on_external_segment_inserts_before_or_after(self):
        for after in (False, True):
            with self.subTest(after=after):
                self.setUp()
                self.start("block_2")
                self.drop(self.point("standalone_1", after))
                self.assertEqual(self.app.blocks.index(self.second), 1 if not after else 2)

    def test_target_child_maps_to_whole_parent_block(self):
        for after in (False, True):
            with self.subTest(after=after):
                self.setUp()
                self.start("block_2")
                self.drop(self.point("segment_0_0", after))
                self.assertIs(self.app.blocks[1 if after else 0], self.second)
                self.assertEqual(len(self.first["segments"]), 2)

    def test_drop_on_own_child_does_nothing(self):
        self.start("block_0")
        self.drop(self.point("segment_0_1"))
        self.assertIs(self.app.blocks[0], self.first)
        self.app.refresh_tree.assert_not_called()

    def test_empty_area_moves_block_to_end(self):
        self.start("block_0")
        self.drop(SimpleNamespace(x=40, y=400))
        self.assertIs(self.app.blocks[-1], self.first)

    def test_closed_block_remains_closed_after_move(self):
        self.tree.open["block_0"] = False
        self.start("block_0")
        self.drop(self.point("block_2", after=True))
        self.assertFalse(self.tree.open["block_2"])

    def test_escape_restores_preview_and_leaves_model_unchanged(self):
        before = copy.deepcopy(self.app.blocks)
        self.start("block_0")
        self.app.show_tree_drag_preview(self.point("block_2", after=True))
        self.app.clear_tree_selection()
        self.app.finish_tree_drag(SimpleNamespace(x=40, y=400))
        self.assertEqual(self.app.blocks, before)
        self.assertEqual(self.tree.roots, ["block_0", "standalone_1", "block_2"])

    def test_invalid_release_cancels_even_after_valid_preview(self):
        for x, y in ((-1, 100), (301, 100), (40, 501), (40, 5)):
            with self.subTest(x=x, y=y):
                self.setUp()
                self.start("block_0")
                self.app.show_tree_drag_preview(self.point("block_2", after=True))
                self.app.finish_tree_drag(SimpleNamespace(x=x, y=y))
                self.assertIs(self.app.blocks[0], self.first)
                self.assertEqual(self.tree.roots[0], "block_0")

    def test_click_below_threshold_does_not_move_block(self):
        event = self.point("block_0")
        self.start("block_0")
        self.drop(SimpleNamespace(x=event.x + 2, y=event.y + 2))
        self.app.refresh_tree.assert_not_called()

    def test_identical_empty_blocks_move_by_identity(self):
        empty = {"type": "block", "name": "Empty", "repetitions": 2, "segments": []}
        other = copy.deepcopy(empty)
        self.app.blocks = [empty, self.outside, other]
        self.tree.reset()
        self.start("block_2")
        self.drop(self.point("block_0"))
        self.assertIs(self.app.blocks[0], other)
        self.assertIs(self.app.blocks[1], empty)

    def test_live_preview_under_pointer_keeps_destination(self):
        self.start("block_0")
        self.app.show_tree_drag_preview(self.point("block_2", after=True))
        self.app.show_tree_drag_preview(self.point("segment_0_0"))
        self.app.finish_tree_drag(self.point("segment_0_0"))
        self.assertEqual(self.app.blocks, [self.outside, self.second, self.first])

    def test_changed_release_target_uses_visible_preview_order(self):
        self.start("block_0")
        self.app.show_tree_drag_preview(self.point("block_2", after=True))
        self.app.finish_tree_drag(self.point("block_2"))
        self.assertEqual(self.app.blocks, [self.outside, self.first, self.second])

    def test_repeated_moves_preserve_all_objects(self):
        for _ in range(3):
            self.start("block_0")
            self.drop(SimpleNamespace(x=40, y=400))
            self.start("block_2")
            self.drop(self.point("standalone_0"))
        self.assertEqual(len(self.app.blocks), 3)
        self.assertEqual({id(b) for b in self.app.blocks},
                         {id(self.first), id(self.second), id(self.outside)})
