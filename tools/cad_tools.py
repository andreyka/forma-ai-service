import os
import uuid
import logging
import pyvista as pv
from build123d import *

# Configure logging
logger = logging.getLogger(__name__)

import contextvars

# Context variable to track the current task ID
task_id_var = contextvars.ContextVar("task_id", default=None)

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_cad_model(script_code: str) -> dict:
    """
    Executes build123d code and exports STEP/STL.
    Returns dict with 'success', 'error', 'files' (dict of paths).
    """
    local_scope = {}
    
    try:
        # Security warning: exec() is dangerous.
        exec(script_code, {}, local_scope)
    except Exception as e:
        return {
            "success": False, 
            "error": f"Execution failed: {str(e)}"
        }

    # Look for 'result' or 'part'
    result_obj = local_scope.get("result") or local_scope.get("part")
    
    if not result_obj:
        return {
            "success": False, 
            "error": "No 'result' or 'part' variable defined."
        }

    # Use task ID if available, otherwise UUID
    task_id = task_id_var.get()
    if task_id:
        base_name = f"{task_id}_{uuid.uuid4().hex[:8]}"
    else:
        base_name = str(uuid.uuid4())

    step_path = os.path.join(OUTPUT_DIR, f"{base_name}.step")
    stl_path = os.path.join(OUTPUT_DIR, f"{base_name}.stl")

    try:
        export_step(result_obj, step_path)
        export_stl(result_obj, stl_path)
    except Exception as e:
        return {
            "success": False, 
            "error": f"Export failed: {str(e)}"
        }

    return {
        "success": True,
        "files": {
            "step": step_path,
            "stl": stl_path
        }
    }

def render_cad_model(stl_path: str) -> dict:
    """
    Renders an STL file to PNG screenshots (Iso, Top, Front, Right).
    Returns dict with 'success', 'error', 'images' (list of paths).
    """
    if not os.path.exists(stl_path):
        return {"success": False, "error": "STL file not found."}

    image_paths = []
    base_name = os.path.splitext(os.path.basename(stl_path))[0]

    try:
        # Start virtual framebuffer if needed (for headless)
        pv.start_xvfb()
        
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

        for name, view_func in views.items():
            view_func(plotter)
            plotter.camera.zoom(1.2)
            out_path = os.path.join(OUTPUT_DIR, f"{base_name}_{name}.png")
            plotter.screenshot(out_path)
            image_paths.append(out_path)
        
        plotter.close()

    except Exception as e:
        return {"success": False, "error": f"Rendering failed: {str(e)}"}

    return {
        "success": True,
        "images": image_paths
    }
