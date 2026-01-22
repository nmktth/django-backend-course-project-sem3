# Photo Album Designer

## Project Overview

Photo Album Designer is a web application based on Django 6.0 representing a system for managing photo albums, creating collages, and tracking user activity.

The system supports two modes of interaction:

1. **Web Interface (SSR)**: Classic Django templates approach.
2. **REST API**: Fully functional JSON API for external clients (Mobile apps, SPA).

## Key Features

- **User Management**: Registration, Login/Logout, Profile editing, Avatar upload (Cloudinary).
- **Photo Albums**: Create albums, upload multiple photos, **Duplicate** and **Share** functionality.
- **Advanced Search & Filtering**: Find content by dates, tags, and status.
- **Analytics & Recommendations**: User stats and template suggestions.
- **Excel Export**: Detailed reports on albums and bug trackers.
- **Collage Generation**: Automated creation of collages from album photos.
- **Bug Reporting**: Built-in system for users to report issues.
- **API Documentation**: Integrated Swagger/OpenAPI documentation.

## Documentation Contents

- [Setup and Installation](setup.md)
- [System Architecture](architecture.md)
- [API Reference](api.md)
- [User Guide](user_guide.md)
