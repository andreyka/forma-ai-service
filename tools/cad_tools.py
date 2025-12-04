"""CAD tools for generating and rendering 3D models.

This module provides functions to execute build123d scripts in a sandboxed process
and render the resulting STL files to images.
"""

import os
import uuid
import logging
import contextvars
import multiprocessing
import traceback
import pyvista as pv
from build123d import *
from config import settings
from tools.security import validate_code

# Configure logging
logger = logging.getLogger(__name__)

# Context variable to track the current task ID
task_id_var = contextvars.ContextVar("task_id", default=None)

OUTPUT_DIR = settings.OUTPUT_DIR
os.makedirs(OUTPUT_DIR, exist_ok=True)

def _execute_and_export(script_code: str, output_dir: str, base_name: str) -> dict:
    """Execute code and export files in a separate process.

    Args:
        script_code (str): The Python script to execute.
        output_dir (str): Directory to save output files.
        base_name (str): Base name for output files.

    Returns:
        dict: Result dictionary with success status and file paths.
    """
    try:
        # Validate code before execution
        validate_code(script_code)

        # Dynamically populate the execution scope with build123d symbols
        # This avoids verbose explicit imports while ensuring a clean state
        import build123d
        local_scope = {name: getattr(build123d, name) for name in dir(build123d) if not name.startswith("_")}
        
        # Execute the script
        exec(script_code, {}, local_scope)
        
        # Look for 'result' or 'part'
        result_obj = local_scope.get("result") or local_scope.get("part")
        
        if not result_obj:
            return {
                "success": False, 
                "error": "No 'result' or 'part' variable defined."
            }

        step_path = os.path.join(output_dir, f"{base_name}.step")
        stl_path = os.path.join(output_dir, f"{base_name}.stl")

        export_step(result_obj, step_path)
        export_stl(result_obj, stl_path)
        
        return {
            "success": True,
            "files": {
                "step": step_path,
                "stl": stl_path
            }
        }
    except Exception as e:
        return {
            "success": False, 
            "error": f"Execution failed: {str(e)}\n{traceback.format_exc()}"
        }

def create_cad_model(script_code: str) -> dict:
    """Executes build123d code and exports STEP/STL.

    Runs in a separate process with a timeout.

    Args:
        script_code (str): The build123d script to execute.

    Returns:
        dict: A dictionary containing 'success', 'error', and 'files' (dict of paths).
    """
    # Use task ID if available, otherwise UUID
    task_id = task_id_var.get()
    if task_id:
        base_name = f"{task_id}_{uuid.uuid4().hex[:8]}"
    else:
        base_name = str(uuid.uuid4())

    # Run in a separate process to allow timeout and isolation
    with multiprocessing.Pool(processes=1) as pool:
        async_result = pool.apply_async(_execute_and_export, (script_code, OUTPUT_DIR, base_name))
        try:
            # 120 second timeout
            result = async_result.get(timeout=120)
            return result
        except multiprocessing.TimeoutError:
            return {
                "success": False, 
                "error": "Execution timed out (120s limit). The model might be too complex."
            }
        except Exception as e:
            return {
                "success": False, 
                "error": f"Process error: {str(e)}"
            }

def _render_worker(stl_path: str, output_dir: str, base_name: str) -> dict:
    """Render the STL in a separate process.

    Args:
        stl_path (str): Path to the STL file.
        output_dir (str): Directory to save images.
        base_name (str): Base name for output images.

    Returns:
        dict: Result dictionary with success status and image paths.
    """
    try:
        # Configure PyVista for headless rendering with EGL/OSMesa
        pv.OFF_SCREEN = True
        
        # Force EGL or OSMesa if available (avoids X server requirement)
        # Note: This requires libosmesa6-dev in Dockerfile
        try:
            pv.start_xvfb() # No-op if not needed, but safe to remove if using pure EGL
        except:
            pass
            
        plotter = pv.Plotter(off_screen=True)
        mesh = pv.read(stl_path)
        plotter.add_mesh(mesh, color="lightblue", show_edges=True)
        plotter.set_background("white")

        # Views to generate
        views = {
            "iso": lambda p: p.view_isometric(),
            "top": lambda p: p.view_xy(),
            "front": lambda p: p.view_xz(), # Assuming Y-up or Z-up, adjust as needed
            "right": lambda p: p.view_yz()
        }

        image_paths = []
        for name, view_func in views.items():
            view_func(plotter)
            plotter.camera.zoom(1.2)
            out_path = os.path.join(output_dir, f"{base_name}_{name}.png")
            plotter.screenshot(out_path)
            image_paths.append(out_path)
        
        plotter.close()
        return {"success": True, "images": image_paths}

    except Exception as e:
        return {"success": False, "error": f"Rendering failed: {str(e)}\n{traceback.format_exc()}"}

def render_cad_model(stl_path: str) -> dict:
    """Renders an STL file to PNG screenshots (Iso, Top, Front, Right).

    Runs in a separate process to ensure VTK/OpenGL isolation.

    Args:
        stl_path (str): Path to the STL file.

    Returns:
        dict: A dictionary containing 'success', 'error', and 'images' (list of paths).
    """
    if not os.path.exists(stl_path):
        return {"success": False, "error": "STL file not found."}

    base_name = os.path.splitext(os.path.basename(stl_path))[0]

    # Run in a separate process
    with multiprocessing.Pool(processes=1) as pool:
        async_result = pool.apply_async(_render_worker, (stl_path, OUTPUT_DIR, base_name))
        try:
            # 30 second timeout for rendering
            result = async_result.get(timeout=30)
            return result
        except multiprocessing.TimeoutError:
            return {
                "success": False, 
                "error": "Rendering timed out (30s limit)."
            }
        except Exception as e:
            return {
                "success": False, 
                "error": f"Render process error: {str(e)}"
            }
