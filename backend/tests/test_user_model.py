"""Schema expectations for user lifecycle (soft delete)."""

from models import User


def test_user_table_has_soft_delete_column() -> None:
    assert "deleted_at" in User.__table__.columns
    col = User.__table__.c.deleted_at
    assert col.nullable is True
