import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from app import TreadmillApp


class SegmentSelectionTests(unittest.TestCase):
    def setUp(self):
        self.app = TreadmillApp.__new__(TreadmillApp)
        self.inner = {"name": "Inner"}
        self.block = {"type": "block", "name": "Repeat", "repetitions": 2,
                      "segments": [self.inner]}
        self.outside = {"type": "segment", "segment": {"name": "Outside"}}
        self.app.blocks = [self.outside, self.block]
        self.new = {"name": "New"}
        self.wrapper = {"type": "segment", "segment": self.new}
        self.selected = ()
        tree = self.app.tree = Mock()
        tree.selection.side_effect = lambda: self.selected
        tree.selection_remove.side_effect = self.remove_selection
        tree.parent.side_effect = lambda row: "block" if row == "inner" else ""
        tree.index.side_effect = {"outside": 0, "block": 1, "inner": 0}.__getitem__
        self.app.tree_item_data = {
            "inner": {"kind": "segment", "segment": self.inner,
                      "parent_block": self.block, "wrapper": None},
        }
        self.app.editing_segment = None
        self.app.update_segment_button = Mock()
        self.app.reset_block_editor = Mock()
        self.app.reset_segment_editor = Mock()
        self.app.refresh_tree = Mock()
        self.app.update_summary = Mock()
        self.app.get_segment_values = Mock(return_value=self.new)

    def remove_selection(self, *items):
        self.selected = tuple(item for item in self.selected if item not in items)

    def test_no_selection_appends_at_top_level(self):
        self.app.add_segment()
        self.assertEqual(self.app.blocks, [self.outside, self.block, self.wrapper])

    def test_block_selection_appends_inside_block(self):
        self.selected = ("block",)
        self.app.add_segment()
        self.assertEqual(self.app.blocks, [self.outside, self.block])
        self.assertEqual(self.block["segments"], [self.inner, self.new])

    def test_inner_selection_appends_inside_same_block(self):
        self.selected = ("inner",)
        self.app.add_segment()
        self.assertEqual(self.app.blocks, [self.outside, self.block])
        self.assertEqual(self.block["segments"], [self.inner, self.new])

    def test_outer_selection_inserts_after_selected_segment(self):
        self.selected = ("outside",)
        self.app.add_segment()
        self.assertEqual(self.app.blocks, [self.outside, self.wrapper, self.block])

    def test_escape_clears_selection_and_edit_target(self):
        self.selected = ("inner",)
        self.app.editing_segment = ("block", 1, 0)
        self.app.clear_tree_selection(SimpleNamespace(keysym="Escape"))
        self.assertEqual(self.selected, ())
        self.assertIsNone(self.app.editing_segment)
        self.app.reset_segment_editor.assert_not_called()
        self.app.reset_block_editor.assert_called_once()
        self.app.update_segment_button.config.assert_called_once_with(state="disabled")
        self.app.add_segment()
        self.assertEqual(self.app.blocks[-1], self.wrapper)

    def test_blank_click_returns_insertion_to_top_level(self):
        self.selected = ("block",)
        self.app.tree.identify_row.return_value = ""
        self.app.tree.identify_region.return_value = "nothing"
        event = SimpleNamespace(x=20, y=100)
        self.app.start_tree_drag(event)
        self.app.finish_tree_drag(event)
        self.assertEqual(self.selected, ())
        self.app.add_segment()
        self.assertEqual(self.app.blocks[-1], self.wrapper)
        self.assertEqual(self.block["segments"], [self.inner])

    def test_header_click_preserves_selection(self):
        self.selected = ("block",)
        self.app.tree.identify_row.return_value = ""
        self.app.tree.identify_region.return_value = "heading"
        self.app.start_tree_drag(SimpleNamespace(x=20, y=5))
        self.assertEqual(self.selected, ("block",))

    def test_drag_from_segment_to_empty_area_moves_segment(self):
        self.app.tree.identify_row.side_effect = ["inner", ""]
        self.app.start_tree_drag(SimpleNamespace(x=20, y=30))
        self.app.finish_tree_drag(SimpleNamespace(x=20, y=100))
        self.assertEqual(self.block["segments"], [])
        self.assertEqual(self.app.blocks[-1], {"type": "segment", "segment": self.inner})

    def test_selecting_another_row_invalidates_edit_without_resetting_form(self):
        self.app.editing_segment = ("block", 1, 0)
        self.selected = ("outside",)
        self.app.on_tree_select()
        self.assertIsNone(self.app.editing_segment)
        self.app.reset_segment_editor.assert_not_called()
        self.app.update_segment_button.config.assert_called_once_with(state="disabled")
