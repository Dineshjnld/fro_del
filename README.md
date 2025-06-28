# CCTNS Copilot Engine (AI-Powered Voice Query System)

## 1. Objective

To create an intelligent, voice-enabled system that allows police personnel at all levels to seamlessly access and interact with the CCTNS (Crime and Criminal Tracking Network and Systems) database using natural language voice commands. This solution aims to democratize data access by removing technical barriers such as SQL query formulation, enabling officers—from constables to senior officials—to retrieve accurate and timely crime and investigation data effortlessly. The system will interpret spoken queries, translate them into precise database requests, and generate structured, easy-to-understand reports. By incorporating real-time error detection, step-by-step clarifications, and multi-language support (English, Telugu, Hindi), the system ensures reliable communication and enhances user confidence in accessing critical information, thereby improving decision-making and operational efficiency.

## 2. Scope

The solution encompasses a voice command interface integrated into a web application, supporting English, Telugu, and Hindi. This interface connects to an AI-powered backend that performs the following:
*   **Speech-to-Text (STT)**: Converts spoken queries into text.
*   **Text Processing**: Translates Indic languages (Telugu, Hindi) to English and performs grammar correction on English text.
*   **Natural Language to SQL (NL2SQL)**: Converts the processed English natural language queries into safe SQL statements tailored for the CCTNS Oracle database schema.
*   **Secure Execution**: A middleware layer (FastAPI backend) handles data, sanitizes inputs (basic validation for SELECT queries), and manages database interaction.
*   **Result Presentation**: The frontend displays query results, including the generated SQL and data tables.
*   **Error Handling**: The system provides feedback for errors encountered during processing and suggestions for query refinement.

This project serves as a prototype demonstrating a scalable client-server architecture, aiming to pave the way for comprehensive AI-assisted utilization of CCTNS data.

## 3. Current Architecture

The system follows a client-server architecture:

*   **Frontend (Client)**:
    *   A React application built with TypeScript and Vite, located in the project root.
    *   Provides the user interface for text and voice-based query input.
    *   Manages user interaction and displays results received from the backend.
    *   Uses browser's Web Speech API for initial voice capture, then sends audio to the backend for STT.
    *   Styling is likely managed by a utility CSS framework like Tailwind CSS (inferred from class usage).

*   **Backend (Server)**:
    *   A Python FastAPI application (`api/main.py`).
    *   Exposes RESTful APIs for voice transcription and query processing.
    *   Orchestrates the AI/ML model pipeline.

*   **Database**:
    *   Primary Target: Oracle CCTNS database (connection details via `.env`).
    *   Local Demo/Fallback: SQLite database (`cctns_demo.db`) with a schema mirroring the target Oracle structure, managed by `models/sql_executor.py`.

*   **AI/ML Model Integration**:
    *   Models are loaded and managed by the backend.
    *   Configuration for models and the database schema is primarily driven by `config/models_config.yml`.

### Data Processing Pipeline:

1.  **Input**: User speaks or types a query into the React frontend.
2.  **Voice Capture (if voice)**: The React `VoiceInput` component captures audio using the browser's Web Speech API.
3.  **Speech-to-Text (STT)**:
    *   The captured audio blob is sent to the backend's `/api/voice/transcribe` endpoint.
    *   The `IndianSTTProcessor` (`models/stt_processor.py`) uses:
        *   Primary Model: `ai4bharat/indicconformer` (Wav2Vec2-based) for Indic languages and English.
        *   Fallback Model: `openai/whisper-medium` (Transformer-based).
4.  **Text Processing**:
    *   The transcribed text is processed by `TextProcessor` (`models/text_processor.py`) on the backend (typically within the `/api/voice/transcribe` flow):
        *   **Translation**: If the source language (detected by STT or specified) is Telugu or Hindi, it's translated to English using `ai4bharat/indictrans2` (T5-based).
        *   **Grammar Correction**: The (now) English text is corrected using `google/flan-t5-base`.
5.  **Query Submission to Backend**: The processed English text (from voice or direct text input) is sent from the React app to the `/api/query/process` backend endpoint.
6.  **Natural Language to SQL (NL2SQL)**:
    *   The backend's `NL2SQLProcessor` (`models/nl2sql_processor.py`) receives the processed English query.
    *   It utilizes a pre-trained Transformer model (e.g., `microsoft/CodeT5-base`, as configured in `nl2sql.primary.name` in `config/models_config.yml`) for Text-to-SQL conversion.
    *   The processor serializes the detailed Oracle schema (defined in `cctns_schema` in `config/models_config.yml`) and includes it in the prompt provided to the NL2SQL model to generate schema-aware SQL queries.
    *   Generated SQL is validated to ensure it's a `SELECT` statement and doesn't contain harmful keywords.
7.  **SQL Execution**:
    *   The generated SQL query is passed to the `SQLExecutor` (`models/sql_executor.py`).
    *   `SQLExecutor` connects to the configured database (Oracle target, with SQLite demo fallback).
    *   Executes the `SELECT` query. Basic validation (SELECT only, no dangerous keywords) is performed.
8.  **Results to Frontend**: The backend returns a JSON response containing the original query, generated SQL, execution status, and query results (data, columns, row count).
9.  **Display**: The React frontend (`App.tsx` and `ResultsDisplay.tsx`) parses the response and displays the information to the user, typically showing the SQL and the data in a table.
10. **Reporting (Backend Capability)**:
    *   The `ReportGenerator` (`models/report_generator.py`) can produce summaries (using `google/pegasus-cnn_dailymail`) and charts. This functionality is primarily backend-side and not yet fully integrated for on-demand interactive report generation from the UI based on query results.

## 4. Key Features Implemented

*   **Voice-Enabled Querying**: Users can speak queries in English, Telugu, or Hindi.
*   **Multi-Stage Text Processing**:
    *   Backend Speech-to-Text using robust models (IndicConformer, Whisper).
    *   Translation of Indic languages to English for consistent NL2SQL processing.
    *   Grammar correction for improved query understanding.
*   **Schema-Aware NL2SQL**: Utilizes a Transformer model (e.g., CodeT5) with detailed Oracle schema context to convert natural language to SQL.
*   **Unified Backend API**: A single FastAPI application (`api/main.py`) provides all core services.
*   **Integrated React Frontend**: A responsive UI for voice/text query submission and clear presentation of results.
*   **Dynamic Oracle Schema Configuration**: The system's understanding of the database is driven by a detailed schema definition in `config/models_config.yml`.
*   **SQLite Demo Mode**: Includes a local SQLite database that mirrors the Oracle schema structure for development and testing without a live Oracle DB.
*   **Streamlined Codebase**: Refactored to remove unused components and consolidate frontend and backend logic.

## 5. Tech Stack

*   **Frontend**:
    *   React (v19+)
    *   TypeScript
    *   Vite (build tool)
    *   Utility CSS (likely Tailwind CSS, inferred from class usage)
*   **Backend**:
    *   Python (3.9+)
    *   FastAPI (web framework)
    *   Uvicorn (ASGI server)
*   **AI/ML Models & Libraries**:
    *   PyTorch
    *   Hugging Face Transformers library
    *   **Speech-to-Text (STT)**: `ai4bharat/indicconformer`, `openai/whisper-medium`
    *   **Text Processing**: `google/flan-t5-base` (correction), `ai4bharat/indictrans2` (translation)
    *   **Natural Language to SQL (NL2SQL)**: `microsoft/CodeT5-base` (or as configured)
    *   **Summarization (for ReportGenerator)**: `google/pegasus-cnn_dailymail`
    *   Librosa (audio processing)
*   **Database**:
    *   Oracle (Primary Target) - requires `oracledb` Python driver.
    *   SQLite (for local demo/fallback).
*   **Configuration**:
    *   YAML (`config/models_config.yml`)
    *   Python (`config/settings.py`)
    *   `.env` files for environment-specific variables.

## 6. Local Setup and Running the Project

### Prerequisites:

*   Python 3.9 or higher.
*   Node.js 18.x or higher (which includes npm).
*   A virtual environment tool for Python (like `venv` or `conda`) is highly recommended.
*   Access to an Oracle database instance (if not using the SQLite demo mode).
*   Git for cloning the repository.

### Steps:

1.  **Clone the Repository**:
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Backend Setup**:
    *   **Create and Activate Virtual Environment**:
        ```bash
        python -m venv venv
        # On Windows:
        # venv\Scripts\activate
        # On macOS/Linux:
        # source venv/bin/activate
        ```
    *   **Install Python Dependencies**:
        ```bash
        pip install -r requirements.txt
        ```
        *(Note: If you intend to connect to a live Oracle database, ensure the `oracledb` driver is listed in `requirements.txt` or install it separately: `pip install oracledb`)*
    *   **Configure Environment Variables**:
        Create a `.env` file in the project root directory. Add the following variables, replacing placeholder values with your actual configuration:
        ```env
        # General Settings
        APP_NAME="CCTNS Copilot Engine"
        DEBUG=true # true for development, false for production
        LOG_LEVEL="INFO" # DEBUG, INFO, WARNING, ERROR

        # Server Settings (Defaults are usually fine for local)
        # HOST="0.0.0.0"
        # PORT=8000

        # Database Connection
        # Option 1: For Oracle DB (RECOMMENDED FOR FULL FUNCTIONALITY)
        # Ensure 'oracledb' is installed (pip install oracledb).
        # The SQLExecutor expects the full connection string.
        ORACLE_CONNECTION_STRING="oracle+oracledb://YOUR_USERNAME:YOUR_PASSWORD@YOUR_HOSTNAME:YOUR_PORT/YOUR_SERVICE_NAME"
        # Example: ORACLE_CONNECTION_STRING="oracle+oracledb://cctns_user:yourStrongPassword@db.example.com:1521/cctns_service"

        # Option 2: For Local SQLite Demo (if Oracle is not available or for quick testing)
        # ORACLE_CONNECTION_STRING="sqlite:///./cctns_demo.db"
        # (If using this, comment out or remove the Oracle string above)

        # AI Model Settings
        MODELS_DIR="./models_cache" # Optional: Directory for Hugging Face model caching
        USE_GPU="false" # Set to "true" if you have a compatible GPU and CUDA installed
        ```
        *Replace placeholders like `YOUR_USERNAME`, `YOUR_PASSWORD`, `YOUR_HOSTNAME`, `YOUR_PORT`, `YOUR_SERVICE_NAME` with your actual Oracle credentials if using Oracle.*
    *   **Model Downloads**: Models from Hugging Face are typically downloaded automatically on first use and cached in the directory specified by `MODELS_DIR` (or the default Hugging Face cache path if `MODELS_DIR` is not set or accessible).
    *   **Run the Backend Server**:
        ```bash
        python run.py
        ```
        The backend API should now be running, typically at `http://localhost:8000`.

3.  **Frontend Setup**:
    *   Open a new terminal in the project root directory.
    *   **Install Node.js Dependencies**:
        ```bash
        npm install
        ```
    *   **Run the Frontend Development Server**:
        ```bash
        npm run dev
        ```
        The React application should now be accessible in your browser, typically at `http://localhost:5173` (or another port if 5173 is busy, Vite will indicate this).

4.  **Accessing the Application**:
    *   Open your web browser and navigate to the frontend URL (e.g., `http://localhost:5173`).
    *   The backend API documentation (Swagger UI) should be available at `http://localhost:8000/docs`.
    *   The backend health check is at `http://localhost:8000/health`.

## 7. Potential Future Enhancements

Based on the original project scope and current implementation, potential areas for future development include:

*   **Full Oracle DB Integration**: Implement robust Oracle connection and query execution logic in `SQLExecutor`, including handling of Oracle-specific data types and error codes more comprehensively.
*   **Advanced NL2SQL Capabilities**:
    *   Fine-tune the NL2SQL model (e.g., CodeT5) on domain-specific data or more complex queries.
    *   Improve handling of implicit lookups (e.g., "Guntur" to its district code) and complex clauses (e.g., multi-level aggregations, specific date functions).
*   **Interactive Reporting & Visualization**: Integrate `ReportGenerator` capabilities more directly into the UI, allowing users to generate charts and reports from query results on demand.
*   **Dataset Management**: Implement features for users to name, tag, save, and manage query result sets as described in the "Expected Outcome" in the problem statement.
*   **Conversational Context**: Implement robust conversational follow-up, allowing users to ask refining questions based on previous results without re-stating full context.
*   **Enhanced UI Features**: Add pagination, sorting, and data export (CSV, Excel) options to the results display in the React frontend.
*   **Dynamic Schema Ingestion**: Develop a more dynamic mechanism for the backend to ingest and understand the database schema, potentially refreshing it periodically from a live DB.
*   **Error Handling & Clarification**: Improve interactive error handling with more specific suggestions and potential clarification dialogues for ambiguous queries.
*   **Agentic Framework**: If advanced features like multi-agent coordination or deeper state management become critical, consider re-evaluating an agent-based architecture for specific components.
```
