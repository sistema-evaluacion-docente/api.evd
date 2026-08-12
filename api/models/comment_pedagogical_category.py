"""
CommentPedagogicalCategory model — join row between a comment and one of the
(0 or more) pedagogical categories the AI model assigned to it, each with its
own confidence score.
"""

from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from api.database import Base


class CommentPedagogicalCategoryModel(Base):
    """One (comment, pedagogical_category) assignment with its confidence score."""

    __tablename__ = "comment_pedagogical_categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    comment_id = Column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pedagogical_category_id = Column(
        Integer, ForeignKey("pedagogical_categories.id"), nullable=False, index=True
    )
    score = Column(Float, nullable=True)

    pedagogical_category_rel = relationship(
        "PedagogicalCategoryModel",
        lazy="joined",
        foreign_keys=[pedagogical_category_id],
    )
