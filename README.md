# Forma AI Agent Service

![Forma AI Logo](assets/logo.png)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Forma AI is an AI agent which generates parametric 3D CAD models (STEP/STL) from natural language descriptions. It is aiming to produce precise, engineering-grade geometry suitable for manufacturing and 3D printing. 

### Architecture

Forma AI is a multi-agent AI system (service). It implements built  a **Control Flow** architecture that manages the lifecycle of a task from initial prompt to final approved model.

```mermaid
graph TD
    User[User Request] --> ControlFlow[Control Flow Agent]
    ControlFlow --> Designer[Designer Agent]
    Designer -- "1. Specification" --> ControlFlow
    ControlFlow --> Coder[Coder Agent]
    Coder -- "2. Python Code (build123d)" --> ControlFlow
    ControlFlow --> Renderer[Headless Renderer]
    Renderer -- "3. Rendered Image" --> ControlFlow
    ControlFlow --> Designer
    Designer -- "4. Feedback / Approval" --> ControlFlow
    
    subgraph Feedback Loop
    Coder
    Renderer
    Designer
    end

    ControlFlow -- "5. Final Model (STEP/STL)" --> User
```

### Components

1.  **Control Flow Agent**: The central orchestrator. It manages the session, maintains state, and executes the feedback loop. It ensures that the output from one agent (e.g., the spec) is correctly passed to the next (e.g., the coder).

2.  **Designer Agent**: Acts as the product designer.
    *   **Role**: Analyzes user requests and creates detailed technical specifications.
    *   **Capabilities**: Uses **RAG (Retrieval-Augmented Generation)** to access the latest `build123d` documentation and **Google Search** to find reference images or concepts.
    *   **Feedback**: Reviews rendered images of the generated model against the original specification and provides constructive feedback to the Coder Agent.

3.  **Coder Agent**: The software engineer.
    *   **Role**: Translates technical specifications into executable Python code using the `build123d` library.
    *   **Capabilities**: Specialized in CAD geometry logic and Python scripting.

4.  **Headless Renderer**: The visualization engine.
    *   **Role**: Takes the generated STL/STEP files and produces high-quality 2D images.
    *   **Tech**: Uses `PyVista` with EGL/OSMesa for server-side, headless rendering (no GPU/Display required).

5.  **RAG System**: A vector database (ChromaDB) containing the full documentation of the `build123d` library. This ensures the agents use valid, up-to-date syntax and features.

## Features

*   **Text-to-CAD**: Convert simple text prompts into complex 3D geometry.
*   **Iterative Self-Correction**: The system automatically detects errors (syntax or visual) and retries until the model matches the specification.
*   **Visual Feedback**: The Designer agent "sees" the model via rendered images, allowing for visual validation.
*   **Parametric Code**: The output is not just a mesh, but Python code that can be modified and parameterized.
*   **Standard Formats**: Exports to STEP (for CAD software) and STL (for 3D printing).

## Limitations

*   **Stateless Execution**: Each task is fully independent. The agent does not retain context from previous requests. You cannot ask the agent to "modify the previous model" or "make the hole bigger"; you must provide the full specification for the modified model in a new request.

## Getting Started

### Prerequisites

*   Docker
*   Google Cloud API Key (for Gemini models and Google Custom Search)

### Installation

To run the service standalone using Docker:

1.  **Build the image:**
    ```bash
    docker build -t forma-ai-service .
    ```

2.  **Run the container:**
    You need to provide your Google API Key.
    ```bash
    docker run -p 8001:8001 \
      -e GOOGLE_API_KEY=your_key_here \
      forma-ai-service
    ```


### API Usage

The service implements an asynchronous "Agent-to-Agent" (A2A) protocol. It follows the specification at [https://a2a-protocol.org/latest/specification/](https://a2a-protocol.org/latest/specification/), using JSON as the data format.

A reference client implementation is provided in the `example/` directory.

**Running the Example:**

1.  Ensure the service is running (see Installation).
2.  Install `requests`:
    ```bash
    pip install requests
    ```
3.  Run the client script:
    ```bash
    python example/client.py "Design a 10x10x10 cm cube with a 5mm hole in the center."
    ```

The script will submit the prompt, poll for completion, and print the download URLs for the generated files.

## Licenses

This project uses the following open-source libraries:

*   **build123d**: [Apache License 2.0](licenses/BUILD123D_LICENSE)
*   **PyVista**: [MIT License](licenses/PYVISTA_LICENSE)
*   **Google Generative AI**: [Apache License 2.0](licenses/GOOGLE_GENAI_LICENSE)
*   **Playwright**: [Apache License 2.0](licenses/PLAYWRIGHT_LICENSE)
*   **ChromaDB**: [Apache License 2.0](licenses/CHROMADB_LICENSE)
