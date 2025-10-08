from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

def make_user(email="u@u.com", password="pass", groups=()):
    user = User.objects.create_user(email=email, password=password)
    for name in groups:
        g, _ = Group.objects.get_or_create(name=name.lower())  # normalize
        user.groups.add(g)
    user.save()  # <- make sure to save after adding groups
    return user