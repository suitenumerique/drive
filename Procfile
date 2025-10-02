web: bin/scalingo_run_web
worker: celery -A drive.celery_app worker --task-events --beat -l INFO -c $DJANGO_CELERY_CONCURRENCY -Q celery,default
postdeploy: python manage.py migrate
