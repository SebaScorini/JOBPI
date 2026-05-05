from __future__ import annotations

# ruff: noqa: E402

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import logging
import re
from types import SimpleNamespace

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.ai import (
    build_ai_failure_http_exception,
    dspy_lm_override,
    run_structured_ai_call,
    use_provider_fallback_model,
)
from app.core.config import configure_dspy, get_settings
from app.models import User
from app.models.ai_schemas import InterviewEvaluationAIOutput, InterviewQuestionsAIOutput
from app.repositories import CvLibraryRepository, InterviewRepository, JobRepository
from app.schemas.interview import (
    InterviewAnswerRead,
    InterviewAnswerSubmit,
    InterviewEvaluationRead,
    InterviewFeedbackRead,
    InterviewQuestionRead,
    InterviewSessionCreate,
    InterviewSessionRead,
    InterviewSessionSummaryRead,
)
from app.services.job_preprocessing import build_cv_context, build_job_context
from app.services.response_language import language_instruction, normalize_language


logger = logging.getLogger(__name__)
DEFAULT_INTERVIEW_MAX_TOKENS = 1800


class InterviewQuestionSignature(dspy.Signature):
    """Generate realistic interview practice questions grounded in the job and CV.

    Use only the evidence provided by the job and CV contexts. Shape the mix of questions to the
    requested session type, prioritizing the weakest gaps and the most important proof points.
    Avoid generic screening questions, duplicates, filler, or abstract coaching language.
    Return concise structured items that a candidate can practice immediately.
    """

    job_context: str = dspy.InputField(desc="Markdown job context with the useful posting content")
    cv_context: str = dspy.InputField(desc="Markdown CV context with the candidate's strongest evidence")
    session_type: str = dspy.InputField(desc="Session type: mixed, behavioral, or technical")
    response_language: str = dspy.InputField(desc="Language for all generated question text")
    questions: list[dict[str, str]] = dspy.OutputField(
        desc=(
            "Return 5-7 JSON objects. Each item must include question, category, difficulty, and rationale. "
            "Categories must be behavioral, technical, situational, or culture_fit. Difficulty must be easy, medium, or hard."
        )
    )
    focus_areas: list[str] = dspy.OutputField(
        desc="Return 2-5 concise focus areas that the session targets, based on the job and CV gaps."
    )


class InterviewEvaluationSignature(dspy.Signature):
    """Evaluate a spoken or written interview answer against the job and CV context.

    Score the answer based on alignment, specificity, evidence, and role fit. Keep feedback
    actionable and anchored to the candidate's real background. Do not be generic or punitive;
    give a clear path to a stronger answer. Use the question and answer directly, and adapt tone
    to the requested language.
    """

    question: str = dspy.InputField(desc="The interview question being answered")
    question_category: str = dspy.InputField(desc="Question category such as behavioral or technical")
    difficulty: str = dspy.InputField(desc="Question difficulty such as easy, medium, or hard")
    user_answer: str = dspy.InputField(desc="The candidate's answer")
    cv_context: str = dspy.InputField(desc="Markdown CV context with the candidate's evidence")
    job_context: str = dspy.InputField(desc="Markdown job context with the useful posting content")
    response_language: str = dspy.InputField(desc="Language for all generated feedback")
    score: int = dspy.OutputField(desc="Score from 1 to 10 for how well the answer fits the role")
    feedback: str = dspy.OutputField(desc="2-3 sentences of specific, constructive feedback")
    ideal_answer: str = dspy.OutputField(desc="What a strong answer would cover for this question")
    improvement_tips: list[str] = dspy.OutputField(desc="2-3 concrete tips to improve the answer")


class InterviewQuestionModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(InterviewQuestionSignature)

    def forward(
        self,
        *,
        job_context: str,
        cv_context: str,
        session_type: str,
        response_language: str,
        max_tokens: int | None = None,
        model: str | None = None,
    ):
        if max_tokens is None:
            return self.predict(
                job_context=job_context,
                cv_context=cv_context,
                session_type=session_type,
                response_language=response_language,
            )

        with dspy_lm_override(max_tokens=max_tokens, model=model):
            return self.predict(
                job_context=job_context,
                cv_context=cv_context,
                session_type=session_type,
                response_language=response_language,
            )


class InterviewEvaluationModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(InterviewEvaluationSignature)

    def forward(
        self,
        *,
        question: str,
        question_category: str,
        difficulty: str,
        user_answer: str,
        cv_context: str,
        job_context: str,
        response_language: str,
        max_tokens: int | None = None,
        model: str | None = None,
    ):
        if max_tokens is None:
            return self.predict(
                question=question,
                question_category=question_category,
                difficulty=difficulty,
                user_answer=user_answer,
                cv_context=cv_context,
                job_context=job_context,
                response_language=response_language,
            )

        with dspy_lm_override(max_tokens=max_tokens, model=model):
            return self.predict(
                question=question,
                question_category=question_category,
                difficulty=difficulty,
                user_answer=user_answer,
                cv_context=cv_context,
                job_context=job_context,
                response_language=response_language,
            )


def _user_id(user: User) -> int:
    assert user.id is not None, "User.id must not be None for a persisted user"
    return user.id


class InterviewSessionService:
    def __init__(
        self,
        job_repository: JobRepository | None = None,
        cv_repository: CvLibraryRepository | None = None,
        interview_repository: InterviewRepository | None = None,
    ) -> None:
        settings = get_settings()
        self.question_generator: InterviewQuestionModule | None = None
        self.evaluator: InterviewEvaluationModule | None = None
        self.timeout_seconds = settings.ai_timeout_seconds
        self.max_tokens = min(settings.job_analysis_max_tokens, DEFAULT_INTERVIEW_MAX_TOKENS)
        self.retry_max_tokens = min(settings.job_analysis_retry_max_tokens, DEFAULT_INTERVIEW_MAX_TOKENS)
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._job_repository = job_repository or JobRepository()
        self._cv_repository = cv_repository or CvLibraryRepository()
        self._interview_repository = interview_repository or InterviewRepository()

    def _get_question_generator(self) -> InterviewQuestionModule:
        if self.question_generator is None:
            try:
                configure_dspy()
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI analysis is not configured.",
                ) from exc
            self.question_generator = InterviewQuestionModule()
        return self.question_generator

    def _get_evaluator(self) -> InterviewEvaluationModule:
        if self.evaluator is None:
            try:
                configure_dspy()
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI analysis is not configured.",
                ) from exc
            self.evaluator = InterviewEvaluationModule()
        return self.evaluator

    def start_session(
        self,
        session: Session,
        user: User,
        job_id: int,
        payload: InterviewSessionCreate,
    ) -> InterviewSessionRead:
        job = self._job_repository.get_for_user(session, user_id=_user_id(user), job_id=job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        cv = self._cv_repository.get_cv_for_user(session, _user_id(user), payload.cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        selected_language = normalize_language(payload.language)
        job_context = build_job_context(job.clean_description, title=job.title, company=job.company)
        cv_context = build_cv_context(cv.clean_text, summary=cv.summary, library_summary=cv.library_summary)

        try:
            generator = self._get_question_generator()
            logger.info(
                "ai_call operation=interview_question_generation job_id=%s cv_id=%s session_type=%s",
                job_id,
                payload.cv_id,
                payload.session_type,
            )
            parsed = run_structured_ai_call(
                schema=InterviewQuestionsAIOutput,
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="interview_question_generation",
                logger=logger,
                callable_=generator,
                lm_max_tokens=self.max_tokens,
                retry_lm_max_tokens=self.retry_max_tokens,
                attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
                    "job_context": job_context,
                    "cv_context": cv_context,
                    "session_type": payload.session_type,
                    "response_language": language_instruction(selected_language),
                    "max_tokens": self.max_tokens if attempt == 0 else self.retry_max_tokens,
                    "model": use_provider_fallback_model(attempt, previous_exception),
                },
            )
        except HTTPException as exc:
            logger.warning("ai_call_http_error operation=interview_question_generation status_code=%s", exc.status_code)
            raise
        except Exception as exc:
            raise build_ai_failure_http_exception(
                exc=exc,
                logger=logger,
                operation="interview_question_generation",
                default_detail="Failed to generate interview questions. Please try again.",
            ) from exc

        questions = [self._question_to_dict(question) for question in parsed.payload.questions]
        focus_areas = list(parsed.payload.focus_areas)
        created = self._interview_repository.create_session(
            session,
            user_id=_user_id(user),
            job_id=job_id,
            cv_id=payload.cv_id,
            session_type=payload.session_type,
            language=selected_language,
            questions=questions,
            summary=self._initial_summary(focus_areas),
        )
        return self._serialize_session(created)

    def submit_answer(
        self,
        session: Session,
        user: User,
        job_id: int,
        session_id: int,
        answer_payload: InterviewAnswerSubmit,
    ) -> InterviewFeedbackRead:
        interview_session = self._interview_repository.get_session_for_user(
            session,
            user_id=_user_id(user),
            session_id=session_id,
        )
        if interview_session is None or interview_session.job_id != job_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

        if interview_session.status == "completed":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Interview session is already completed.")

        answers = list(interview_session.answers or [])
        next_question_index = len(answers)
        if answer_payload.question_index != next_question_index:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Answer the next unanswered question in order.",
            )

        questions = list(interview_session.questions or [])
        if next_question_index >= len(questions):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="All interview questions were already answered.")

        job = self._job_repository.get_for_user(session, user_id=_user_id(user), job_id=job_id)
        cv = self._cv_repository.get_cv_for_user(session, _user_id(user), interview_session.cv_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        selected_language = normalize_language(interview_session.language)
        question_data = questions[next_question_index]
        question_text = str(question_data.get("question", "")).strip()
        question_category = str(question_data.get("category", "behavioral")).strip()
        difficulty = str(question_data.get("difficulty", "medium")).strip()
        job_context = build_job_context(job.clean_description, title=job.title, company=job.company)
        cv_context = build_cv_context(cv.clean_text, summary=cv.summary, library_summary=cv.library_summary)

        answer_record = {
            "question_index": answer_payload.question_index,
            "answer_text": answer_payload.answer_text.strip(),
            "answered_at": datetime.now(timezone.utc).isoformat(),
        }

        answers.append(answer_record)
        self._interview_repository.update_answers(session, interview_session=interview_session, answers=answers)

        try:
            evaluator = self._get_evaluator()
            logger.info(
                "ai_call operation=interview_answer_evaluation session_id=%s question_index=%s",
                session_id,
                answer_payload.question_index,
            )
            parsed = run_structured_ai_call(
                schema=InterviewEvaluationAIOutput,
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="interview_answer_evaluation",
                logger=logger,
                callable_=evaluator,
                lm_max_tokens=self.max_tokens,
                retry_lm_max_tokens=self.retry_max_tokens,
                attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
                    "question": question_text,
                    "question_category": question_category,
                    "difficulty": difficulty,
                    "user_answer": answer_payload.answer_text,
                    "cv_context": cv_context,
                    "job_context": job_context,
                    "response_language": language_instruction(selected_language),
                    "max_tokens": self.max_tokens if attempt == 0 else self.retry_max_tokens,
                    "model": use_provider_fallback_model(attempt, previous_exception),
                },
            )
        except HTTPException as exc:
            logger.warning("ai_call_http_error operation=interview_answer_evaluation status_code=%s", exc.status_code)
            parsed = self._build_fallback_evaluation_payload(
                question=question_text,
                question_category=question_category,
                difficulty=difficulty,
                user_answer=answer_payload.answer_text,
                language=selected_language,
            )
        except Exception as exc:
            http_error = build_ai_failure_http_exception(
                exc=exc,
                logger=logger,
                operation="interview_answer_evaluation",
                default_detail="Failed to evaluate the interview answer. Please try again.",
            )
            logger.warning(
                "ai_fallback operation=interview_answer_evaluation reason=%s status_code=%s",
                type(exc).__name__,
                http_error.status_code,
            )
            parsed = self._build_fallback_evaluation_payload(
                question=question_text,
                question_category=question_category,
                difficulty=difficulty,
                user_answer=answer_payload.answer_text,
                language=selected_language,
            )

        evaluation_record = {
            "question_index": answer_payload.question_index,
            "score": parsed.payload.score,
            "feedback": parsed.payload.feedback,
            "ideal_answer": parsed.payload.ideal_answer,
            "improvement_tips": list(parsed.payload.improvement_tips),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

        evaluations = list(interview_session.evaluations or [])
        evaluations.append(evaluation_record)

        self._interview_repository.update_answers(session, interview_session=interview_session, answers=answers)
        self._interview_repository.update_evaluations(
            session,
            interview_session=interview_session,
            evaluations=evaluations,
        )

        is_complete = len(answers) >= len(questions)
        summary_model = self._build_summary(interview_session, evaluations) if is_complete else self._existing_summary(interview_session)
        summary_payload = summary_model.model_dump() if summary_model is not None else None
        updated = self._interview_repository.update_summary(
            session,
            interview_session=interview_session,
            summary=summary_payload,
            overall_score=summary_model.overall_score if summary_model is not None else None,
            status="completed" if is_complete else interview_session.status,
        )
        return self._serialize_feedback(updated, answer_record, evaluation_record)

    def get_session(self, session: Session, user: User, job_id: int, session_id: int) -> InterviewSessionRead:
        interview_session = self._interview_repository.get_session_for_user(
            session,
            user_id=_user_id(user),
            session_id=session_id,
        )
        if interview_session is None or interview_session.job_id != job_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")
        return self._serialize_session(interview_session)

    def list_sessions(self, session: Session, user: User, job_id: int) -> list[InterviewSessionRead]:
        sessions, _ = self._interview_repository.list_sessions_for_user(
            session,
            user_id=_user_id(user),
            job_id=job_id,
            limit=100,
            offset=0,
        )
        return [self._serialize_session(interview_session) for interview_session in sessions]

    def _serialize_session(self, interview_session) -> InterviewSessionRead:
        questions = [
            InterviewQuestionRead.model_validate({"index": index, **question})
            for index, question in enumerate(list(interview_session.questions or []))
        ]
        answers = [InterviewAnswerRead.model_validate(answer) for answer in list(interview_session.answers or [])]
        evaluations = [InterviewEvaluationRead.model_validate(evaluation) for evaluation in list(interview_session.evaluations or [])]
        summary = InterviewSessionSummaryRead.model_validate(interview_session.summary) if interview_session.summary else None
        current_question_index = len(answers)
        next_question_index = None if interview_session.status == "completed" or current_question_index >= len(questions) else current_question_index
        return InterviewSessionRead(
            id=interview_session.id,
            user_id=interview_session.user_id,
            job_id=interview_session.job_id,
            cv_id=interview_session.cv_id,
            session_type=interview_session.session_type,
            language=normalize_language(interview_session.language),
            status=interview_session.status,
            questions=questions,
            answers=answers,
            evaluations=evaluations,
            summary=summary,
            current_question_index=current_question_index,
            next_question_index=next_question_index,
            is_complete=interview_session.status == "completed",
            created_at=interview_session.created_at,
            updated_at=interview_session.updated_at,
        )

    @staticmethod
    def _question_to_dict(question: object) -> dict:
        if hasattr(question, "model_dump"):
            return dict(question.model_dump())  # type: ignore[no-any-return]
        if isinstance(question, dict):
            return dict(question)
        return {
            "question": str(getattr(question, "question", "")).strip(),
            "category": str(getattr(question, "category", "behavioral")).strip() or "behavioral",
            "difficulty": str(getattr(question, "difficulty", "medium")).strip() or "medium",
            "rationale": str(getattr(question, "rationale", "")).strip(),
        }

    def _serialize_feedback(self, interview_session, answer_record: dict, evaluation_record: dict) -> InterviewFeedbackRead:
        summary = InterviewSessionSummaryRead.model_validate(interview_session.summary) if interview_session.summary else None
        current_question_index = len(interview_session.answers or [])
        next_question_index = None if interview_session.status == "completed" or current_question_index >= len(interview_session.questions or []) else current_question_index
        return InterviewFeedbackRead(
            session_id=interview_session.id,
            question_index=int(evaluation_record["question_index"]),
            answer_text=str(answer_record.get("answer_text", "")),
            score=int(evaluation_record["score"]),
            feedback=str(evaluation_record["feedback"]),
            ideal_answer=str(evaluation_record["ideal_answer"]),
            improvement_tips=list(evaluation_record["improvement_tips"]),
            evaluated_at=datetime.fromisoformat(str(evaluation_record["evaluated_at"])),
            is_complete=interview_session.status == "completed",
            next_question_index=next_question_index,
            summary=summary,
        )

    def _initial_summary(self, focus_areas: list[str]) -> dict:
        return {
            "focus_areas": list(focus_areas),
            "overall_score": None,
            "strong_areas": [],
            "weak_areas": [],
            "next_steps": [],
        }

    def _existing_summary(self, interview_session) -> InterviewSessionSummaryRead | None:
        if not interview_session.summary:
            return None
        return InterviewSessionSummaryRead.model_validate(interview_session.summary)

    def _build_summary(self, interview_session, evaluations: list[dict]) -> InterviewSessionSummaryRead:
        summary = self._existing_summary(interview_session) or InterviewSessionSummaryRead()
        overall_score = round(sum(int(item.get("score", 0)) for item in evaluations) / len(evaluations), 1) if evaluations else None
        category_scores: dict[str, list[int]] = defaultdict(list)
        question_map = {index: question for index, question in enumerate(list(interview_session.questions or []))}

        for evaluation in evaluations:
            index = int(evaluation.get("question_index", 0))
            question = question_map.get(index, {})
            category = str(question.get("category", "")).strip().replace("_", " ")
            if category:
                category_scores[category].append(int(evaluation.get("score", 0)))

        ranked_categories = sorted(
            ((category, round(sum(scores) / len(scores), 1)) for category, scores in category_scores.items() if scores),
            key=lambda item: item[1],
            reverse=True,
        )
        strong_areas = [category.title() for category, average in ranked_categories if average >= 7][:3]
        weak_areas = [category.title() for category, average in ranked_categories[::-1] if average <= 6][:3]
        next_steps = self._dedupe_preserve_order(
            [tip for evaluation in evaluations for tip in evaluation.get("improvement_tips", []) if isinstance(tip, str)],
            limit=5,
        )

        if not strong_areas:
            strong_areas = list(summary.focus_areas[:2])
        if not weak_areas and summary.focus_areas:
            weak_areas = list(summary.focus_areas[-2:])

        return InterviewSessionSummaryRead(
            focus_areas=list(summary.focus_areas),
            overall_score=overall_score,
            strong_areas=strong_areas,
            weak_areas=weak_areas,
            next_steps=next_steps,
        )

    @staticmethod
    def _dedupe_preserve_order(values: list[str], *, limit: int) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            cleaned = " ".join(value.split()).strip()
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(cleaned)
            if len(result) >= limit:
                break
        return result

    def _build_fallback_evaluation_payload(
        self,
        *,
        question: str,
        question_category: str,
        difficulty: str,
        user_answer: str,
        language: str,
    ) -> SimpleNamespace:
        answer_text = user_answer.strip()
        word_count = len(re.findall(r"\b\w+\b", answer_text))
        metric_count = len(re.findall(r"\b(?:\d+%?|\$\d+|x\d+|metrics?|impact|result|outcome)\b", answer_text, flags=re.IGNORECASE))
        base_score = 6
        if word_count >= 120:
            base_score += 1
        if metric_count >= 2:
            base_score += 1
        if any(token in answer_text.lower() for token in ("i did", "i built", "i improved", "i reduced", "i led")):
            base_score += 1
        if word_count < 40:
            base_score -= 1
        score = max(4, min(9, base_score))

        category_label = question_category.replace("_", " ").strip() or "this question"
        difficulty_label = difficulty.strip() or "medium"

        feedback = (
            "AI evaluation was unavailable, so this is a local fallback review. "
            f"Your answer for the {category_label} question is a workable draft, but it should be more concrete about the actions, evidence, and outcome."
        )
        ideal_answer = (
            f"A strong {difficulty_label} answer would restate the situation, name the exact actions you took, and quantify the result where possible."
        )
        improvement_tips = [
            "Add one concrete metric or result.",
            f"Tie the example back to the {category_label} competency the question is testing.",
        ]
        if len(answer_text.split()) < 60:
            improvement_tips.insert(0, "Expand the answer with one more step from the situation, action, or result.")

        return SimpleNamespace(
            payload=SimpleNamespace(
                score=score,
                feedback=feedback,
                ideal_answer=ideal_answer,
                improvement_tips=improvement_tips[:3],
            )
        )


_service: InterviewSessionService | None = None


def get_interview_session_service() -> InterviewSessionService:
    global _service
    if _service is None:
        _service = InterviewSessionService()
    return _service