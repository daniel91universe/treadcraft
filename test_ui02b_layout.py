import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

from app import TreadmillApp
from qz_discovery import QzService, SERVICE_TYPE
from qz_discovery_ui import DiscoveryControls
from workout_data import normalize_workout
from qz_xml_export import export_workout


class LayoutBlockGuiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(self.close_root)
        self.enterContext(patch('app.load_qz_endpoint', return_value=None))
        self.enterContext(patch('app.save_qz_endpoint'))
        self.enterContext(patch('app.messagebox.showinfo'))
        self.enterContext(patch.object(DiscoveryControls, 'search'))
        self.app = TreadmillApp(self.root)
        self.workout = normalize_workout(json.loads(
            (Path(__file__).parent/'examples/3x3000mt.json').read_bytes()))
        self.app.blocks = copy.deepcopy(self.workout['blocks'])
        self.app.workout_name.set(self.workout['workout_name'])
        self.app.refresh_tree()
        self.app.update_summary()
        self.root.update()

    def close_root(self):
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()

    def buttons(self, widget):
        found = {}
        for child in widget.winfo_children():
            if child.winfo_class() in ('TButton', 'Button'):
                found[child.cget('text')] = child
            found.update(self.buttons(child))
        return found

    def point(self, iid, after=False):
        x, y, width, height = self.app.tree.bbox(iid)
        return SimpleNamespace(x=x + 40, y=y + (height-2 if after else 2))

    def move_block_above_warmup(self):
        self.app.start_tree_drag(self.point('block_1'))
        point = self.point('standalone_0')
        self.app.show_tree_drag_preview(point)
        self.app.finish_tree_drag(point)
        self.root.update()

    def test_toolbar_exactly_three_columns_two_rows_with_equal_width(self):
        expected = [('Open Workout', 0, 0), ('Save Workout', 1, 0),
                    ('Check Commercial LE', 0, 1), ('Export XML', 1, 1),
                    ('QZ Devices', 0, 2), ('Send to QZ', 1, 2)]
        self.assertEqual(len(self.app.main_actions.winfo_children()), 6)
        for name, row, col in expected:
            b = self.app.main_buttons[name]
            self.assertEqual((b.grid_info()['row'], b.grid_info()['column']), (row, col))
            self.assertGreaterEqual(b.winfo_width(), b.winfo_reqwidth())
        self.assertEqual(len({b.winfo_width() for b in self.app.main_buttons.values()}), 1)

    def test_removed_controls_absent(self):
        texts = self.buttons(self.root)
        for text in ('Move Block Up', 'Move Block Down', 'Manual address…',
                     'Verify manual address', 'Test Connection', 'Reconnect to QZ'):
            self.assertNotIn(text, texts)
        self.assertFalse(hasattr(self.app, 'qz_manual_panel'))

    def test_duplicate_block_immediately_below_update_preserves_state(self):
        buttons = self.buttons(self.root)
        update, duplicate = buttons['Update Block'], buttons['Duplicate Block']
        self.assertIs(update.master, duplicate.master)
        self.assertEqual(duplicate.grid_info()['row'], update.grid_info()['row'] + 1)
        self.assertEqual(duplicate.grid_info()['column'], update.grid_info()['column'])
        self.assertIn('disabled', update.state())
        self.assertNotIn('disabled', duplicate.state())
        self.app.tree.selection_set('block_1')
        self.root.update()
        self.assertNotIn('disabled', update.state())
        duplicate.invoke()
        self.assertEqual(len(self.app.blocks), 4)
        self.assertIsNot(self.app.blocks[1], self.app.blocks[2])

    def test_segment_actions_match_blocks_position_colour_and_titles(self):
        buttons = self.buttons(self.root)
        self.assertEqual(self.app.segment_panel.cget('text'), 'Segments')
        self.assertEqual(self.app.block_panel.cget('text'), 'Blocks')
        self.assertNotIn('Edit Segment', buttons)
        self.assertFalse(self.buttons(self.app.structure_panel))
        for action, row, col in [('Add',0,0), ('Update',0,1), ('Remove',1,0), ('Duplicate',1,1)]:
            segment = buttons[action+' Segment']
            block = buttons[action+' Block']
            self.assertIs(segment.master.master, self.app.segment_panel)
            self.assertEqual((segment.grid_info()['row'], segment.grid_info()['column']), (row,col))
            self.assertEqual(segment.cget('style'), block.cget('style'))

    def test_segment_selection_loads_form_and_update_changes_selected_only(self):
        before = copy.deepcopy(self.app.blocks)
        self.app.tree.selection_set('segment_1_0')
        self.root.update()
        self.assertEqual(self.app.editing_segment, ('block',1,0))
        self.assertEqual(self.app.segment_name.get(), before[1]['segments'][0]['name'])
        self.assertNotIn('disabled', self.app.update_segment_button.state())
        self.app.segment_name.set('Updated repeat')
        self.app.update_segment_button.invoke()
        self.assertEqual(self.app.blocks[1]['segments'][0]['name'], 'Updated repeat')
        self.assertEqual(self.app.blocks[0], before[0])
        self.assertEqual(self.app.blocks[2], before[2])

    def test_repeated_selection_preserves_draft_and_blank_clears_edit_target(self):
        self.app.tree.selection_set('standalone_0')
        self.root.update()
        self.app.segment_name.set('Unsaved draft')
        self.app.on_tree_select()
        self.assertEqual(self.app.segment_name.get(), 'Unsaved draft')
        self.app.tree.selection_set('segment_1_0')
        self.root.update()
        self.assertEqual(self.app.editing_segment, ('block',1,0))
        self.assertEqual(self.app.segment_name.get(), self.app.blocks[1]['segments'][0]['name'])
        self.app.clear_tree_selection()
        self.assertIsNone(self.app.editing_segment)
        self.assertIn('disabled', self.app.update_segment_button.state())

    def test_relocated_duplicate_and_remove_segment_commands(self):
        buttons = self.buttons(self.root)
        before = copy.deepcopy(self.app.blocks[1]['segments'])
        self.app.tree.selection_set('segment_1_0')
        self.root.update()
        buttons['Duplicate Segment'].invoke()
        self.assertEqual(len(self.app.blocks[1]['segments']), len(before)+1)
        self.assertEqual(self.app.blocks[1]['segments'][1]['name'], before[0]['name']+' (Copy)')
        self.app.tree.selection_set('segment_1_1')
        self.root.update()
        buttons['Remove Segment'].invoke()
        self.assertEqual(self.app.blocks[1]['segments'], before)

    def test_commercial_check_still_assesses_snapshot_only(self):
        before = copy.deepcopy(self.app.blocks)
        with patch('app.assess_workout') as assess, patch('app.messagebox.showwarning') as show:
            assess.return_value.has_blockers = False
            self.app.main_buttons['Check Commercial LE'].invoke()
        self.assertEqual(assess.call_args.args[0]['blocks'], before)
        show.assert_called_once()
        self.assertEqual(self.app.blocks, before)

    def test_real_tree_preview_indicator_order_and_selection(self):
        before = copy.deepcopy(self.app.blocks)
        self.app.start_tree_drag(self.point('block_1'))
        point = self.point('standalone_0')
        self.app.show_tree_drag_preview(point)
        self.root.update_idletasks()
        self.assertEqual(self.app.block_drop_indicator.winfo_manager(), 'place')
        self.assertEqual(self.app.tree.get_children()[0], 'block_1')
        self.assertEqual(self.app.blocks, before)
        self.app.finish_tree_drag(point)
        self.root.update()
        self.assertEqual(self.app.blocks, [before[1], before[0], before[2]])
        self.assertEqual(self.app.tree.selection(), ('block_0',))
        self.assertEqual(self.app.editing_block, 0)
        self.assertFalse(self.app.block_drop_indicator.winfo_manager())

    def test_escape_hides_indicator_restores_tree_and_model(self):
        before = copy.deepcopy(self.app.blocks)
        self.app.start_tree_drag(self.point('block_1'))
        self.app.show_tree_drag_preview(self.point('standalone_0'))
        self.app.clear_tree_selection()
        self.assertEqual(self.app.blocks, before)
        self.assertEqual(self.app.tree.get_children(), ('standalone_0', 'block_1', 'standalone_2'))
        self.assertFalse(self.app.block_drop_indicator.winfo_manager())

    def test_saved_json_and_xml_follow_real_reordered_blocks(self):
        original = export_workout(self.workout)
        self.move_block_above_warmup()
        with TemporaryDirectory() as folder:
            target = Path(folder)
            with patch('app.filedialog.asksaveasfilename', return_value=str(target/'workout.json')):
                self.app.save_workout()
            saved = json.loads((target/'workout.json').read_bytes())
            self.assertEqual(saved['blocks'], self.app.blocks)
            with patch('app.filedialog.asksaveasfilename', return_value=str(target/'workout.xml')), \
                 patch.object(self.app, 'confirm_qz_preview', return_value=True):
                self.app.export_qz_xml()
            rows = ET.parse(target/'workout.xml').getroot()
        old_rows = list(ET.fromstring(original.xml))
        self.assertEqual([r.attrib for r in rows],
                         [r.attrib for r in old_rows[1:7]+old_rows[:1]+old_rows[7:]])
        self.assertEqual(len(rows), 8)
        self.assertEqual([i+1 for i,r in enumerate(rows) if r.get('distance')=='3'], [1,3,5])
        self.assertEqual(export_workout(saved).xml, export_workout({'blocks':self.app.blocks}).xml)

    def test_discovery_selection_verifies_without_sending(self):
        service = QzService('TEST.' + SERVICE_TYPE, ('ws://192.168.1.12:12345/',))
        controls = self.app.qz_discovery
        controls.open()
        controls.services = (service,)
        controls.render()
        controls.listbox.selection_set('0')
        self.app.start_qz_operation = Mock()
        self.app.send_to_qz = Mock()
        controls.connect()
        self.assertTrue(self.app.start_qz_operation.call_args.kwargs['verification'])
        self.app.send_to_qz.assert_not_called()
        self.assertEqual(self.app.qz_address.get(), service.endpoints[0])

    def test_qz_devices_caption_does_not_change_during_search(self):
        controls = self.app.qz_discovery
        controls.queue.put((controls.generation, 'done', None))
        controls.poll()
        self.assertEqual(controls.button.cget('text'), 'QZ Devices')

    def test_real_mouse_bindings_move_block_and_cancel_invalid_release(self):
        tree = self.app.tree
        start, end = self.point('block_1'), self.point('standalone_0')
        tree.event_generate('<ButtonPress-1>', x=start.x, y=start.y)
        self.root.update()
        tree.event_generate('<B1-Motion>', x=end.x, y=end.y)
        self.root.update()
        tree.event_generate('<ButtonRelease-1>', x=end.x, y=end.y)
        self.root.update()
        self.assertEqual(self.app.blocks[0]['type'], 'block')
        before = copy.deepcopy(self.app.blocks)
        start, end = self.point('block_0'), self.point('standalone_2', after=True)
        tree.event_generate('<ButtonPress-1>', x=start.x, y=start.y)
        tree.event_generate('<B1-Motion>', x=end.x, y=end.y)
        tree.event_generate('<ButtonRelease-1>', x=-10, y=end.y)
        self.root.update()
        self.assertEqual(self.app.blocks, before)
        self.assertFalse(self.app.block_drop_indicator.winfo_manager())

    def test_minimum_window_keeps_toolbar_visible_and_actions_unclipped(self):
        self.root.geometry('900x600')
        self.root.update()
        for button in self.app.main_buttons.values():
            self.assertGreaterEqual(button.winfo_rootx(), self.root.winfo_rootx())
            self.assertLessEqual(button.winfo_rootx()+button.winfo_width(),
                                 self.root.winfo_rootx()+self.root.winfo_width())
        for button in self.buttons(self.app.editor_panel).values():
            self.assertGreaterEqual(button.winfo_width(), button.winfo_reqwidth())
            self.assertGreaterEqual(button.winfo_rootx(), button.master.winfo_rootx())
            self.assertLessEqual(button.winfo_rootx()+button.winfo_width(),
                                 button.master.winfo_rootx()+button.master.winfo_width())


if __name__ == '__main__':
    unittest.main()
