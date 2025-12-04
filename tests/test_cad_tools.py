import unittest
from unittest.mock import MagicMock, patch
import os
from tools.cad_tools import create_cad_model, render_cad_model, _execute_and_export, _render_worker

class TestCadTools(unittest.TestCase):

    @patch('tools.cad_tools.multiprocessing.Pool')
    @patch('tools.cad_tools.task_id_var')
    @patch('tools.cad_tools.uuid')
    def test_create_cad_model_success(self, mock_uuid, mock_task_id_var, mock_pool):
        """Test successful CAD model creation."""
        mock_task_id_var.get.return_value = "task_123"
        mock_uuid.uuid4.return_value.hex = "abcdef12"
        
        mock_pool_instance = mock_pool.return_value.__enter__.return_value
        mock_async_result = MagicMock()
        mock_async_result.get.return_value = {"success": True, "files": {"stl": "path/to/stl"}}
        mock_pool_instance.apply_async.return_value = mock_async_result

        result = create_cad_model("print('hello')")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["files"]["stl"], "path/to/stl")
        mock_pool_instance.apply_async.assert_called()

    @patch('tools.cad_tools.multiprocessing.Pool')
    def test_create_cad_model_timeout(self, mock_pool):
        """Test CAD model creation timeout."""
        import multiprocessing
        mock_pool_instance = mock_pool.return_value.__enter__.return_value
        mock_async_result = MagicMock()
        mock_async_result.get.side_effect = multiprocessing.TimeoutError
        mock_pool_instance.apply_async.return_value = mock_async_result

        result = create_cad_model("print('hello')")
        
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["error"])

    @patch('tools.cad_tools.validate_code')
    @patch('tools.cad_tools.export_step')
    @patch('tools.cad_tools.export_stl')
    @patch('builtins.exec')
    def test_execute_and_export_success(self, mock_exec, mock_export_stl, mock_export_step, mock_validate):
        """Test _execute_and_export logic."""
        # We need to mock the local_scope population and result extraction
        # Since exec modifies the dict in place, we can't easily mock the side effect of exec adding 'result' to the dict
        # without a more complex side_effect function.
        # Instead, we can mock the 'exec' call and manually populate the scope if we were calling it directly,
        # but _execute_and_export creates the scope internally.
        
        # However, we can use `unittest.mock.patch.dict` if we could access the scope, but we can't.
        # A workaround is to mock `dir(build123d)` and `getattr(build123d)` to control what goes into scope,
        # but `exec` is the critical part.
        
        # Actually, since we are mocking `exec`, it won't execute anything.
        # The code checks `local_scope.get("result")`.
        # Since `local_scope` is created inside the function, we can't pre-populate it easily.
        
        # BUT, `exec` takes the scope as an argument.
        # If we mock `exec`, we can access the arguments passed to it.
        # But we can't modify the dictionary *before* the next lines of code run in the real function
        # unless `exec` side-effect does it.
        
        def exec_side_effect(code, globals_dict, locals_dict):
            locals_dict['result'] = MagicMock()
            
        mock_exec.side_effect = exec_side_effect
        
        result = _execute_and_export("code", "output_dir", "base_name")
        
        self.assertTrue(result["success"])
        mock_validate.assert_called_with("code")
        mock_export_step.assert_called()
        mock_export_stl.assert_called()

    @patch('tools.cad_tools.multiprocessing.Pool')
    @patch('os.path.exists')
    def test_render_cad_model_success(self, mock_exists, mock_pool):
        """Test successful rendering."""
        mock_exists.return_value = True
        
        mock_pool_instance = mock_pool.return_value.__enter__.return_value
        mock_async_result = MagicMock()
        mock_async_result.get.return_value = {"success": True, "images": ["img1.png"]}
        mock_pool_instance.apply_async.return_value = mock_async_result

        result = render_cad_model("test.stl")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["images"], ["img1.png"])

    def test_render_cad_model_file_not_found(self):
        """Test rendering when file does not exist."""
        with patch('os.path.exists', return_value=False):
            result = render_cad_model("nonexistent.stl")
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "STL file not found.")

if __name__ == '__main__':
    unittest.main()
