# Setup and Installation

## Prerequisites

- **Python**: Version 3.10+ (Developed on 3.14)
- **Pip**: Python package manager
- **Cloudinary Account**: Required for user avatar storage

## Installation Steps (Local)

1. **Clone the repository**

   ```bash
   git clone <repository_url>
   cd PHOTO_ALBUM_DESIGNER
   ```

2. **Create a Virtual Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Create a `.env` file in the root directory. You can copy `.env.example`:

   ```bash
   cp .env.example .env
   ```

   Required variables in `.env`:

   ```env
   # Django
   SECRET_KEY=your_secret_key_here
   DEBUG=True  # Set to False in production
   ALLOWED_HOSTS=your_host,127.0.0.1

   # Database (Optional - defaults to SQLite if not set)
   # DATABASE_URL=postgresql://user:password@localhost:5432/dbname

   # Cloudinary (Required for Media Storage)
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret
   ```

5. **Database Setup**
   The project uses SQLite by default. Run migrations to initialize the database:

   ```bash
   python manage.py migrate
   ```

6. **Create Superuser (Admin)**
   To access the admin panel (`/admin/`):

   ```bash
   python manage.py createsuperuser
   ```

7. **Run the Server**
   ```bash
   python manage.py runserver
   ```
   The application will be available at `http://127.0.0.1:8000/`.

## Installation (Docker)

To run the application in a containerized environment (recommended for consistency):

1. **Prerequisites**: Ensure Docker and Docker Compose are installed.
2. **Environment**: Create `.env` file as described above.
3. **Build and Run**:
   ```bash
   docker-compose up --build
   ```
4. **Access**: Open `http://0.0.0.0:8000/`.

## Code Quality & Linting

This project uses **Pylint** to ensure code quality style guidlines are met.

**Running the Linter:**

```bash
# Basic run
pylint albums config

# Run ignoring specific stylistic warnings (using config)
pylint albums config --rcfile=.pylintrc
```

The goal is to maintain a score above **9.0**.

## Running Tests

To run the full test suite (which includes model, view, and integration tests):

```bash
python manage.py test
```

The testing environment is configured to use a temporary file storage system instead of Cloudinary to ensure speed and isolation.

## Static Files

The project uses **WhiteNoise** for serving static files.

- Run `python manage.py collectstatic` to gather static files into the `staticfiles` directory before deployment.
