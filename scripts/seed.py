import asyncio
from datetime import date, datetime, timedelta, timezone
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.core.security import hash_password
from app.db.session import async_session_factory, engine
from app.models.org import Organization, OrgMember
from app.models.project import Project
from app.models.task import ActivityLog, Comment, Label, Task, TaskLabel
from app.models.user import User
from app.models.website import ExpiryAlertLog, TrackedWebsite


async def seed_data():
    async with async_session_factory() as session:
        print("🌱 Seeding database with initial demo data...")

        # 1. Check if user already exists
        res = await session.execute(select(User).where(User.email == "demo@example.com"))
        user = res.scalar_one_or_none()

        if not user:
            user = User(
                email="demo@example.com",
                hashed_password=hash_password("DemoPassword123!"),
                full_name="Alex Mercer",
                notify_on_expiry=True,
            )
            session.add(user)
            await session.flush()
            print(f"Created demo user: demo@example.com (Password: DemoPassword123!)")

        # 2. Check or create organization
        org_res = await session.execute(select(Organization).where(Organization.slug == "acme-corp"))
        org = org_res.scalar_one_or_none()

        if not org:
            org = Organization(
                name="Acme Corporation",
                slug="acme-corp",
                subscription_status="active",
                plan_type="pro",
            )
            session.add(org)
            await session.flush()

            member = OrgMember(org_id=org.id, user_id=user.id, role="owner")
            session.add(member)
            await session.flush()
            print(f"Created demo org: Acme Corporation")

        # 3. Create Labels
        labels = []
        for l_name, l_color in [("Frontend", "#3B82F6"), ("Backend", "#8B5CF6"), ("DevOps", "#10B981")]:
            lbl_res = await session.execute(
                select(Label).where(Label.org_id == org.id, Label.name == l_name)
            )
            lbl = lbl_res.scalar_one_or_none()
            if not lbl:
                lbl = Label(org_id=org.id, name=l_name, color=l_color)
                session.add(lbl)
                await session.flush()
            labels.append(lbl)

        # 4. Create Project
        proj_res = await session.execute(
            select(Project).where(Project.org_id == org.id, Project.name == "SaaS Platform v2")
        )
        project = proj_res.scalar_one_or_none()

        if not project:
            project = Project(
                org_id=org.id,
                name="SaaS Platform v2",
                description="Core platform overhaul including task manager & website expiry tracker module.",
                status="active",
            )
            session.add(project)
            await session.flush()
            print(f"Created project: SaaS Platform v2")

            # 5. Create Tasks
            task1 = Task(
                project_id=project.id,
                org_id=org.id,
                title="Design Website Expiry Dashboard UI",
                description="Create modern Tailwind components for domain & SSL expiry status badges.",
                status="done",
                priority="high",
                due_date=date.today() + timedelta(days=2),
                created_by=user.id,
                assignee_id=user.id,
            )
            task2 = Task(
                project_id=project.id,
                org_id=org.id,
                title="Integrate WHOIS & SSL Checker Service",
                description="Write stdlib ssl socket connection logic and python-whois domain lookup.",
                status="in_progress",
                priority="urgent",
                due_date=date.today() + timedelta(days=5),
                created_by=user.id,
                assignee_id=user.id,
            )
            task3 = Task(
                project_id=project.id,
                org_id=org.id,
                title="Setup Kubernetes CronJob Scheduler",
                description="Configure k8s cronjob.yaml to trigger internal endpoint daily.",
                status="todo",
                priority="medium",
                due_date=date.today() + timedelta(days=10),
                created_by=user.id,
                assignee_id=user.id,
            )
            session.add_all([task1, task2, task3])
            await session.flush()

            # Add Task Labels & Comments
            session.add(TaskLabel(task_id=task1.id, label_id=labels[0].id))
            session.add(TaskLabel(task_id=task2.id, label_id=labels[1].id))
            session.add(TaskLabel(task_id=task3.id, label_id=labels[2].id))

            c1 = Comment(task_id=task1.id, author_id=user.id, content="UI design completed with HTMX interactions.")
            session.add(c1)

            log1 = ActivityLog(task_id=task1.id, user_id=user.id, action="created", details="Task created")
            log2 = ActivityLog(task_id=task1.id, user_id=user.id, action="status_changed", details="Status set to done")
            session.add_all([log1, log2])

        # 6. Create Tracked Websites
        web_res = await session.execute(
            select(TrackedWebsite).where(TrackedWebsite.org_id == org.id)
        )
        if not web_res.scalars().first():
            web1 = TrackedWebsite(
                org_id=org.id,
                added_by=user.id,
                url="https://google.com",
                label="Google Search Engine",
                domain_expiry_date=date.today() + timedelta(days=365),
                ssl_expiry_date=date.today() + timedelta(days=90),
                last_checked_at=datetime.now(timezone.utc),
                last_check_status="ok",
                is_active=True,
            )
            web2 = TrackedWebsite(
                org_id=org.id,
                added_by=user.id,
                url="https://github.com",
                label="GitHub Platform",
                domain_expiry_date=date.today() + timedelta(days=180),
                ssl_expiry_date=date.today() + timedelta(days=15),  # Within alert threshold!
                last_checked_at=datetime.now(timezone.utc),
                last_check_status="ok",
                is_active=True,
            )
            web3 = TrackedWebsite(
                org_id=org.id,
                added_by=user.id,
                url="https://expired-demo-site.invalid",
                label="Legacy Internal Portal",
                domain_expiry_date=date.today() - timedelta(days=10),  # Expired!
                ssl_expiry_date=date.today() - timedelta(days=5),
                last_checked_at=datetime.now(timezone.utc),
                last_check_status="error",
                last_check_error="WHOIS lookup failed | SSL connection timed out",
                is_active=True,
            )
            session.add_all([web1, web2, web3])
            await session.flush()

            # Seed sample alert log
            alert = ExpiryAlertLog(
                tracked_website_id=web2.id,
                alert_type="ssl",
                days_remaining_at_alert=15,
                sent_at=datetime.now(timezone.utc) - timedelta(days=2),
            )
            session.add(alert)

        await session.commit()
        print("✅ Seeding completed successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_data())
