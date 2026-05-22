#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate --noinput

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

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Build complete!"
