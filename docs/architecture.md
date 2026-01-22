# System Architecture

## Tech Stack

- **Backend Framework**: Django 6.0.1
- **API Framework**: Django Rest Framework (DRF) 3.16.1
- **Filtering**: Django Filter (Advanced query parameters)
- **Database**: SQLite (Default)
- **Image Processing**: Pillow (for collage generation)
- **Cloud Storage**: Cloudinary (for User Profiles), Local FileSystem (for Albums/Photos)
- **Documentation**: drf-spectacular (Swagger UI)

## Data Models (Database Schema)

### Core Models

1. **User (django.contrib.auth)**
   - Standard Django User model.

2. **UserProfile**
   - **OneToOne** relation with `User`.
   - **Fields**: `avatar` (CloudinaryField), `bio`, `location`, `birth_date`.
   - Automatically created via Django Signals (`post_save`) when a User is created.

3. **Album**
   - **ForeignKey** to `User` (Owner).
   - **Fields**: `title`, `description`, `details` (JSON), `is_public` (Boolean), `editors` (ManyToMany User), `created_at`, `updated_at`.
   - Represents a collection of photos. Includes privacy controls (`is_public`) and shared editing (`editors`).

4. **Photo**
   - **ForeignKey** to `Album`.
   - **Fields**: `image` (ImageField -> local media), `is_favorite` (Boolean), `created_at`.
   - Stores individual images linked to an album.

5. **Collage**
   - **ForeignKey** to `Album`.
   - **Fields**: `image` (ImageField), `created_at`.
   - Stores generated collage images resulting from processing Album photos.

### Support Models

6. **BugReport**
   - **ForeignKey** to `User`.
   - **Fields**: `title`, `description`, `status` (open/closed).
   - Allows users to submit feedback/bugs.

## Application Structure

- **`config/`**: Project settings, URL routing, WSGI/ASGI application entry points.
- **`albums/`**: Main application containing:
  - `models.py`: Database definitions.
  - `views.py`: Business logic for both API and Web (hybrid viewsets and function-based views).
  - `forms.py`: Django forms for the Web interface.
  - `serializers.py`: DRF serializers for API data transformation.
  - `utils.py`: Helper functions (e.g., `create_collage_image`).
  - `signals.py`: Event handlers (e.g., Creating Profile on User creation).

## Storage Strategy

The system uses a hybrid storage approach:

- **User Avatars**: Stored in Cloud (Cloudinary) to offload profile asset serving and allow easy transformation.
- **Album Photos**: Stored locally in `media/user_{id}/album_{id}/` directory structure (defined in `models.py` helper functions). This allows for efficient local development or organized file server deployment.
