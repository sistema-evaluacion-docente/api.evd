"""Tests for the SPA routes the notifications and the emails point at."""

from api.utils import plan_links
from api.utils.plan_links import absolute, manager_plan_path, teacher_plan_path


class TestPaths:
    """The two views of a plan are two different screens."""

    def test_the_teacher_reads_their_own_plan(self):
        assert teacher_plan_path(7) == "/mis-planes/7"

    def test_the_director_manages_it_somewhere_else(self):
        assert manager_plan_path(7) == "/planes/7"

    def test_the_two_never_collapse_into_one(self):
        """Test the whole point: a teacher sent to /planes/{id} lands nowhere."""

        assert teacher_plan_path(7) != manager_plan_path(7)


class TestAbsolute:
    """Outside the app there is no router to resolve a path against."""

    def test_prefixes_the_deployments_own_base(self, monkeypatch):
        monkeypatch.setattr(plan_links.config, "FRONTEND_URL", "https://evd.ufps.edu.co")

        assert absolute("/mis-planes/7") == "https://evd.ufps.edu.co/mis-planes/7"
