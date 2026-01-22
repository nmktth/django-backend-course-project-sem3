# Photo Album Designer

**Photo Album Designer** is a Django 6.0 based web system for managing photo albums, automatically creating collages, and organizing personal media collections. It features both a server-side rendered web interface and a complete REST API.

## 🚀 Key Features

- **User Profiles**: Custom profiles with Cloudinary-hosted avatars.
- **Albums & Photos**: Upload with drag-and-drop support, extended management of personal photo collections.
- **Automated Collages**: Tools to generate and download PNG collages from album photos.
- **Hybrid Interface**: Full support for both Web UI (Django Templates) and REST API (DRF).
- **Diagnostics**: Built-in bug reporting system.

## 🛠 Tech Stack

- **Backend**: Python 3.10+, Django 6.0, Django Rest Framework
- **Storage**: Cloudinary (Avatars & Photos in Production), Local File System (Dev/Debug)
- **Database**: SQLite (Default)
- **Documentation**: Swagger/OpenAPI

## ✅ Code Quality

The project enforces high code quality standards using **Pylint**.

To check the code quality score:

```bash
# Run pylint with project-specific configuration
pylint albums config --rcfile=.pylintrc
```

Current target score: **> 9.0/10**.

## 📚 Documentation

Full documentation is available in the [`docs/`](docs/) directory:

- [Setup and Installation](docs/setup.md)
- [System Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [User Guide](docs/user_guide.md)

## ⚡ Quick Start

### Option A: Docker (Recommended)

1. **Configure Environment**:
   Create `.env` file (see example below) with your Cloudinary credentials.

2. **Run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```
   The app will be available at `http://0.0.0.0:8000/`.

### Option B: Local Setup

1. **Clone & Setup**:

   ```bash
   git clone <repo_url>
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Create `.env` based on `.env.example` and add your Cloudinary credentials.

3. **Run**:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

Visit `http://127.0.0.1:8000/` to start.
