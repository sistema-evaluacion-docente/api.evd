"""
Evaluation question score model
"""

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, UniqueConstraint

from api.database import Base


class EvaluationQuestionScoreModel(Base):
    """
    Evaluation question score model — one row per question (001–022) within an evaluation_score
    """

    __tablename__ = "evaluation_question_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    evaluation_score_id = Column(Integer, ForeignKey("evaluation_scores.id"), nullable=False)
    question_code = Column(String(3), nullable=False)
    score = Column(Numeric(4, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("evaluation_score_id", "question_code", name="uq_score_question"),
    )
