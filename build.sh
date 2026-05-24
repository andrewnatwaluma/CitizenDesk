#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating static directory..."
mkdir -p staticfiles

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Creating initial ministries..."
python manage.py shell -c "
from desk.models import Ministry;
ministries = ['Ministry of Agriculture', 'Ministry of Water and Environment', 'Ministry of Health', 'Ministry of Works', 'Ministry of Education'];
for name in ministries:
    m, created = Ministry.objects.get_or_create(name=name)
    if created:
        print(f'Created: {name}')
print('Ministries created successfully')
"

echo "Creating superuser from environment variables..."
python manage.py shell -c "
import os
from django.contrib.auth.models import User;
username = os.environ['SUPERUSER_NAME']
email = os.environ['SUPERUSER_EMAIL']
password = os.environ['SUPERUSER_PASSWORD']
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'Superuser created - Username: {username}')
else:
    print('Superuser already exists')
"

echo "Build complete!"
