#!/usr/bin/env python3
import sys
import argparse
from sqlmodel import Session, select
from datetime import datetime, timezone, timedelta

# Avoid path issues when running directly from scripts/
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.db.database import engine
from app.models.entities import User, CV, JobAnalysis, CVJobMatch

def utc_now():
    return datetime.now(timezone.utc)

def main():
    parser = argparse.ArgumentParser(description="Seed database map with demo data")
    parser.add_argument("--email", required=True, help="User email to seed data for")
    args = parser.parse_args()

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == args.email)).first()
        if not user:
            print(f"Error: User {args.email} not found.")
            return

        print(f"Found user {user.email}. Seeding data...")

        # 1. Create CVs
        cv_swe = CV(
            user_id=user.id,
            filename="Alex_Morgan_SWE.pdf",
            display_name="Alex Morgan SWE",
            raw_text="Experienced Software Engineer...",
            clean_text="Experienced Software Engineer...",
            summary="Senior Software Engineer with 5+ years of experience in React, TypeScript, and Python. Proven track record of building performant web applications and scalable APIs.",
            library_summary="Full-stack engineer focusing on React/Node/Python. Top skills: TypeScript, React, PostgreSQL, FastAPI.",
            is_favorite=True,
            tags=["swe", "frontend", "react", "python"],
            created_at=utc_now() - timedelta(days=10)
        )
        
        cv_pm = CV(
            user_id=user.id,
            filename="Alex_Morgan_PM.pdf",
            display_name="Alex Morgan ProdMgr",
            raw_text="Product Manager...",
            clean_text="Product Manager...",
            summary="Data-driven Product Manager specializing in developer tools and B2B SaaS. Strong technical background combined with user empathy and agile methodology expertise.",
            library_summary="Technical Product Manager with 4 years experience leading cross-functional teams in B2B SaaS. Skills: Agile, Jira, SQL, Python.",
            is_favorite=False,
            tags=["pm", "saas", "leadership"],
            created_at=utc_now() - timedelta(days=5)
        )

        session.add(cv_swe)
        session.add(cv_pm)
        session.commit()
        session.refresh(cv_swe)
        session.refresh(cv_pm)
        
        print("Created CVs.")

        # 2. Create Jobs
        job1 = JobAnalysis(
            user_id=user.id,
            title="Senior Frontend Engineer",
            company="Stripe",
            description="We are looking for a Senior Frontend Engineer to join our payments team. You will build user-facing features using React and TypeScript. You should have deep knowledge of performance optimization and state management.",
            clean_description="We are looking for a Senior Frontend Engineer to join our payments team...",
            analysis_result={
                "summary": "Stripe is seeking a Senior Frontend Engineer for their payments team.",
                "required_skills": ["React", "TypeScript", "Performance Optimization", "State Management"],
                "nice_to_have_skills": ["GraphQL", "Next.js"],
                "responsibilities": ["Build user-facing features", "Mentor junior engineers", "Optimize web applications"]
            },
            status="interview",
            is_saved=True,
            applied_date=utc_now() - timedelta(days=7),
            notes="Recruiter screen went well. Technical round scheduled for next Tuesday.",
            created_at=utc_now() - timedelta(days=8)
        )

        job2 = JobAnalysis(
            user_id=user.id,
            title="Full Stack Developer",
            company="Vercel",
            description="Join our core infrastructure team to build the future of the web. Python, Go, and TypeScript required. Experience with cloud platforms is a plus.",
            clean_description="Join our core infrastructure team...",
            analysis_result={
                "summary": "Vercel needs a Full Stack Developer for their core infrastructure team.",
                "required_skills": ["Python", "TypeScript", "Go", "Cloud Platforms"],
                "nice_to_have_skills": ["AWS", "Docker", "Kubernetes"],
                "responsibilities": ["Develop scalable APIs", "Maintain infrastructure", "Collaborate with product teams"]
            },
            status="applied",
            is_saved=True,
            applied_date=utc_now() - timedelta(days=2),
            notes="Applied through their careers page. Need to follow up next week.",
            created_at=utc_now() - timedelta(days=2)
        )

        job3 = JobAnalysis(
            user_id=user.id,
            title="Product Manager",
            company="Supabase",
            description="We are seeking an experienced Product Manager to lead our Database team. You'll build tools that developers love. Must have experience with PostgreSQL and APIs.",
            clean_description="We are seeking an experienced Product Manager...",
            analysis_result={
                "summary": "Supabase is looking for a Product Manager to lead the Database team.",
                "required_skills": ["Product Management", "PostgreSQL", "APIs"],
                "nice_to_have_skills": ["Open Source", "Developer Tools"],
                "responsibilities": ["Define product roadmap", "Work with engineering teams", "Talk to users"]
            },
            status="offer",
            is_saved=True,
            applied_date=utc_now() - timedelta(days=15),
            notes="Received the offer! Comp package is solid. Deadline to sign is Friday.",
            created_at=utc_now() - timedelta(days=20)
        )
        
        job4 = JobAnalysis(
            user_id=user.id,
            title="Software Engineer",
            company="Acme Corp",
            description="Basic web dev job.",
            clean_description="Basic web dev job.",
            analysis_result={
                "summary": "Standard web development position at a local agency.",
                "required_skills": ["HTML", "CSS", "JavaScript", "PHP"],
                "nice_to_have_skills": ["WordPress"],
                "responsibilities": ["Build websites for clients"]
            },
            status="rejected",
            is_saved=False,
            applied_date=utc_now() - timedelta(days=12),
            created_at=utc_now() - timedelta(days=12)
        )

        session.add(job1)
        session.add(job2)
        session.add(job3)
        session.add(job4)
        session.commit()
        session.refresh(job1)
        session.refresh(job2)
        session.refresh(job3)
        
        print("Created Jobs.")

        # 3. Create Matches
        match1 = CVJobMatch(
            user_id=user.id,
            cv_id=cv_swe.id,
            job_id=job1.id,
            fit_level="strong",
            fit_summary="Excellent fit. The candidate has all required skills.",
            strengths=["React", "TypeScript", "5+ years experience"],
            missing_skills=["Next.js"],
            recommended=True,
            created_at=utc_now()
        )
        
        match2 = CVJobMatch(
            user_id=user.id,
            cv_id=cv_swe.id,
            job_id=job2.id,
            fit_level="medium",
            fit_summary="Good fit for the frontend, but lacking some backend/infrastructure experience.",
            strengths=["Python", "TypeScript"],
            missing_skills=["Go", "Cloud Platforms"],
            recommended=True,
            created_at=utc_now()
        )
        
        match3 = CVJobMatch(
            user_id=user.id,
            cv_id=cv_pm.id,
            job_id=job3.id,
            fit_level="strong",
            fit_summary="Strong PM with technical skills aligning perfectly with the role requirements.",
            strengths=["Product Management", "B2B SaaS", "Python", "SQL"],
            missing_skills=["Direct PostgreSQL admin experience"],
            recommended=True,
            created_at=utc_now()
        )

        session.add(match1)
        session.add(match2)
        session.add(match3)
        session.commit()

        print("Created CV Job Matches.")
        print(f"✅ Demo data seeded successfully for {user.email}.")

if __name__ == "__main__":
    main()
