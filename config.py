"""Configuration settings for the application."""

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings."""
    APP_NAME: str = "forma-ai-service"
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")
    RAG_PERSIST_DIRECTORY: str = os.getenv("RAG_PERSIST_DIRECTORY", "rag_db")
    MODEL_NAME: str = "all-mpnet-base-v2"
    
    # Build123d Documentation URLs
    BUILD123D_DOCS_URLS: list[str] = [
        "https://build123d.readthedocs.io/en/latest/introduction.html",
        "https://build123d.readthedocs.io/en/latest/key_concepts.html",
        "https://build123d.readthedocs.io/en/latest/key_concepts_builder.html",
        "https://build123d.readthedocs.io/en/latest/key_concepts_algebra.html",
        "https://build123d.readthedocs.io/en/latest/location_arithmetic.html",
        "https://build123d.readthedocs.io/en/latest/moving_objects.html",
        "https://build123d.readthedocs.io/en/latest/introductory_examples.html",
        "https://build123d.readthedocs.io/en/latest/examples_1.html",
        "https://build123d.readthedocs.io/en/latest/tutorials.html",
        "https://build123d.readthedocs.io/en/latest/tutorial_design.html",
        "https://build123d.readthedocs.io/en/latest/tutorial_selectors.html",
        "https://build123d.readthedocs.io/en/latest/tutorial_lego.html",
        "https://build123d.readthedocs.io/en/latest/tutorial_joints.html",
        "https://build123d.readthedocs.io/en/latest/tutorial_surface_modeling.html",
        "https://build123d.readthedocs.io/en/latest/objects.html",
        "https://build123d.readthedocs.io/en/latest/operations.html",
        "https://build123d.readthedocs.io/en/latest/topology_selection.html",
        "https://build123d.readthedocs.io/en/latest/builders.html",
        "https://build123d.readthedocs.io/en/latest/build_line.html",
        "https://build123d.readthedocs.io/en/latest/build_sketch.html",
        "https://build123d.readthedocs.io/en/latest/build_part.html",
        "https://build123d.readthedocs.io/en/latest/joints.html",
        "https://build123d.readthedocs.io/en/latest/assemblies.html",
        "https://build123d.readthedocs.io/en/latest/tips.html",
        "https://build123d.readthedocs.io/en/latest/tttt.html",
        "https://build123d.readthedocs.io/en/latest/tech_drawing_tutorial.html",
        "https://build123d.readthedocs.io/en/latest/OpenSCAD.html",
    ]

settings = Settings()
