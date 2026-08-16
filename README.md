# Self-Reflective RAG

A Self-Reflective / Adaptive Retrieval-Augmented Generation (RAG) system built with **LangChain**, **LangGraph**, **ChromaDB**, and LLM / embedding integrations (Google Gemini, Groq, Ollama, OpenAI).

---

## 📋 Prerequisites

- **Python**: Version `3.13` or higher
- **uv**: A fast Python package installer and resolver.

If you don't have `uv` installed, install it via:

- **Windows (PowerShell)**:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **macOS / Linux**:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Via Pip**:
  ```bash
  pip install uv
  ```

---

## 🚀 Setup & Installation Using `uv`

### 1. Clone the Repository
```bash
git clone https://github.com/harshitkh3/Self-Reflective-RAG.git
cd Self-Reflective-RAG
```

### 2. Create a Virtual Environment (`venv`) with `uv`
Run the following command to create a virtual environment using `uv`:

```bash
uv venv
```

> **Note:** To specify a specific Python version (e.g., Python 3.13):
> ```bash
> uv venv --python 3.13
> ```

### 3. Activate the Virtual Environment

- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **macOS / Linux**:
  ```bash
  source .venv/bin/activate
  ```

### 4. Install Dependencies from `requirements.txt`

To install all dependencies listed in [`requirements.txt`](file:///D:/Self-Reflective-RAG/requirements.txt), run:

```bash
uv pip install -r requirements.txt
```

> **Alternative (Project Sync):**
> Since this project also contains [`pyproject.toml`](file:///D:/Self-Reflective-RAG/pyproject.toml) and [`uv.lock`](file:///D:/Self-Reflective-RAG/uv.lock), you can alternatively sync dependencies in one step:
> ```bash
> uv sync
> ```

---

## 🔑 Environment Configuration

Create a `.env` file in the root directory and add your API keys:

```env
# Google Gemini
GOOGLE_API_KEY="your_google_api_key"

# OpenAI
OPENAI_API_KEY="your_openai_api_key"

# Groq (Optional)
GROQ_API_KEY="your_groq_api_key"

# LangSmith Tracing (Optional)
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_API_KEY="your_langsmith_api_key"
```

---

## 💻 Running the Project

### Running Python Scripts
You can run [`main.py`](file:///D:/Self-Reflective-RAG/main.py) with the active virtual environment or directly using `uv run`:

```bash
uv run main.py
```

### Using with Jupyter Notebooks
If you are working with the notebook [`step1_decide.ipynb`](file:///D:/Self-Reflective-RAG/step1_decide.ipynb):

1. Ensure [`ipykernel`](file:///D:/Self-Reflective-RAG/requirements.txt#L26) is installed in your virtual environment (included in `requirements.txt`).
2. Register the kernel (optional if your IDE auto-detects `.venv`):
   ```bash
   python -m ipykernel install --user --name=self-reflective-rag --display-name="Self-Reflective-RAG (Python 3.13)"
   ```
3. Open [`step1_decide.ipynb`](file:///D:/Self-Reflective-RAG/step1_decide.ipynb) in VS Code or Jupyter and select the `.venv` kernel.

---

## 📁 Project Structure

```text
Self-Reflective-RAG/
├── .env                  # Environment variables & API keys
├── .python-version       # Python version pinned (3.13)
├── main.py               # Main entry point
├── pyproject.toml        # Project configuration & dependencies
├── requirements.txt      # Pinned requirements list
├── step1_decide.ipynb    # Decision Graph notebook
├── uv.lock               # UV lockfile
└── README.md             # Project documentation
```

---

## 🛠️ Quick `uv` Command Reference

| Action | Command |
| :--- | :--- |
| **Create venv** | `uv venv` |
| **Create venv with specific Python** | `uv venv --python 3.13` |
| **Install from requirements.txt** | `uv pip install -r requirements.txt` |
| **Install a new package** | `uv pip install <package_name>` |
| **Add dependency to pyproject.toml** | `uv add <package_name>` |
| **Sync all dependencies** | `uv sync` |
| **Run script inside env** | `uv run <script.py>` |
