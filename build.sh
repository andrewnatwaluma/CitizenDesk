#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating static directory..."
mkdir -p staticfiles

echo "Collecting static files..."
python manage.py collectstatic --noinput

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

echo "Creating superuser..."
python manage.py shell -c "
from django.contrib.auth.models import User;
if not User.objects.filter(username='andrewnatwaluma').exists():
    User.objects.create_superuser('andrewnatwaluma', 'andrewnatwaluma@gmail.com', 'uganda2026')
    print('Superuser created - Username: andrewnatwaluma, Password: uganda2026')
else:
    print('Superuser already exists')
"

echo "Build complete!"
