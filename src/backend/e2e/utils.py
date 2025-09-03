from core import factories, models


def get_or_create_e2e_user(email):
    user = models.User.objects.filter(email=email).first()
    if not user:
        user = factories.UserFactory(email=email, sub=None, language="en-us")
    return user
