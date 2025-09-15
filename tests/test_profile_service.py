import pytest
from app.application.services.profile_service import ProfileService


class FakeUsers:
    def __init__(self):
        self.calls = []

    def update_profile_fields(self, user_id, name, age, dob):
        self.calls.append((user_id, name, age, dob))


def test_update_profile_validates_and_updates():
    repo = FakeUsers()
    svc = ProfileService(user_repo=repo)
    svc.update_profile("u1", name="John", age=25, date_of_birth="2000-01-01")
    assert repo.calls[0] == ("u1", "John", 25, "2000-01-01")


def test_update_profile_invalid_age():
    repo = FakeUsers()
    svc = ProfileService(user_repo=repo)
    with pytest.raises(Exception):
        svc.update_profile("u1", name=None, age=-1, date_of_birth=None)


