# Server Commands

## Start Development Server
To start the Django development server that's accessible from other devices on your network:
```bash
cd server
python manage.py runserver 0.0.0.0:8000
```

The server will be available at:
- Local: http://127.0.0.1:8000
- Network: http://<your-ip-address>:8000

## Database Commands

### Apply Migrations
To apply database migrations:
```bash
cd server
python manage.py migrate
```

### Create New Migrations
After making changes to models, create new migration files:
```bash
cd server
python manage.py makemigrations
```
