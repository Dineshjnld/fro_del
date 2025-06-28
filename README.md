# CCTNS Copilot (FastAPI + Open-Source Model Version)

This project is an AI-powered copilot to query the Crime and Criminal Tracking Network & Systems (CCTNS) database using natural language. This version uses a Python FastAPI backend with an open-source model for Natural Language to SQL conversion and a React-based frontend.

## Project Structure

- **/frontend**: Contains the React single-page application for the user interface.
- **/backend**: Contains the FastAPI server that handles AI processing and mock database queries.

## How to Run

You need to run the backend server and the frontend application separately.

### 1. Running the Backend

The backend server is responsible for processing user queries with an AI model.

**Prerequisites:**
- Python 3.8+
- `pip`

**Setup:**
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```
3. Install the required Python packages. This may take some time as it includes PyTorch and the Transformers library.
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```
The server will start on `http://127.0.0.1:8000`. The first time you run it, it will download the open-source model (`google/flan-t5-base`), which may take several minutes depending on your internet connection.

### 2. Running the Frontend

The frontend is a static web application. You can serve it using any simple HTTP server. One of the easiest ways is using the "Live Server" extension in Visual Studio Code.

**Setup:**
1. Open the `frontend` directory in your code editor (e.g., VS Code).
2. Right-click on the `index.html` file.
3. Select "Open with Live Server" (or your preferred method of serving static files).

This will open the application in your browser, likely at an address like `http://127.0.0.1:5500`. The frontend will automatically connect to the backend server running on port 8000.

## How It Works

1. The user enters a natural language query (e.g., "Show crimes in Guntur") in the React frontend.
2. The frontend sends this query to the FastAPI backend at the `/process-query` endpoint.
3. The backend uses a pre-loaded open-source model from Hugging Face Transformers (`google/flan-t5-base`) to convert the query into an SQL statement and a user-friendly summary.
4. The generated SQL is executed against a mock database within the backend.
5. The backend returns the SQL, summary, and data results to the frontend.
6. The frontend displays the conversation, the generated SQL, and the data in a table with visualizations.
