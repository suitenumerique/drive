web: bin/scalingo_run_web
worker: celery -A drive.celery_app worker --concurrency=2 --loglevel=info
postdeploy: python manage.py migrate
