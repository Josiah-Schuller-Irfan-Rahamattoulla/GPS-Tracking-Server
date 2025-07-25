# GPS-Tracking-Server

A FastAPI-based GPS tracking server with PostgreSQL database support for managing devices, users, and GPS location data.

## Local Set-Up Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL database
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd GPS-Tracking-Server
   ```

2. **Install uv** (if not already installed)
   ```bash
   # On macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # On Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Navigate to the API directory**
   ```bash
   cd api
   ```

4. Create virtual environment
   ```bash
   uv venv
   . .venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   # Install production dependencies
   uv pip sync requirements.txt
   
   # Or install with development dependencies
   uv pip sync requirements-dev.txt
   ```

5. **Set up environment variables**
   Create a `.env` file in the `api` directory with your database configuration:
   ```
   DATABASE_URL=postgresql://username:password@server:5432/database_name
   ```

6. **Set up the database (OPTIONAL)**
   - Create a PostgreSQL database
   - Run the SQL schema from `database/gps_tracking_database.sql`

### Running the Application

```bash
python main.py
```

The server will start on `http://localhost:8000` with interactive API documentation available at the root URL.

## API Endpoints

- **GET /** - Interactive API documentation (Swagger UI). You can see all other endpoints documented here.

## Development

### Code Quality

```bash
# Run linting and formatting
ruff check .
ruff format .
```

### Updating Dependencies

```bash
# Update requirements.txt
uv pip compile --output-file requirements.txt pyproject.toml

# Update dev requirements
uv pip compile --output-file requirements-dev.txt --extra dev pyproject.toml
```

