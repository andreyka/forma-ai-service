"""Renderer utility for STL files.

This module provides a function to render STL files to PNG images using PyVista.
"""

import os
import pyvista as pv
from typing import Optional

def render_stl(stl_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """Renders an STL file to a PNG image using PyVista.

    Args:
        stl_path (str): Path to the STL file.
        output_path (Optional[str]): Path to save the image. If None, uses STL path with .png extension.

    Returns:
        Optional[str]: The path to the generated image, or None if failed.
    """
    if not os.path.exists(stl_path):
        print(f"Error: STL file not found at {stl_path}")
        return None

    if output_path is None:
        output_path = stl_path.replace(".stl", ".png")

    try:
        # Start Xvfb if running on Linux and no display is set
        if os.name == 'posix' and "DISPLAY" not in os.environ:
            try:
                pv.start_xvfb()
            except Exception as e:
                print(f"Warning: Could not start Xvfb: {e}")

        # Configure PyVista for headless rendering
        pv.OFF_SCREEN = True

        # Read the STL file
        mesh = pv.read(stl_path)

        # Create a plotter
        plotter = pv.Plotter(off_screen=True)
        plotter.add_mesh(mesh, color="lightblue", show_edges=True)
        plotter.set_background("white")
        
        # Set camera position (isometric view)
        plotter.view_isometric()
        
        # Save screenshot
        plotter.screenshot(output_path)
        plotter.close()
        
        return output_path
    except Exception as e:
        print(f"Error rendering STL: {e}")
        return None
