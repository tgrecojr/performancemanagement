"""
Simple script to test the database models.
This creates sample data to verify the models work correctly.
"""
from src.database import init_db, get_db
from src.models import AssociateLevel, PerformanceRating, Associate


def test_models():
    """Test the database models by creating sample data."""
    print("Initializing database...")
    init_db()

    db = get_db()
    try:
        # Create Associate Levels
        print("\nCreating Associate Levels...")
        level1 = AssociateLevel(
            description="Individual Contributor",
            level_indicator=1,
            max_percentage=60.0
        )
        level2 = AssociateLevel(
            description="Team Lead",
            level_indicator=2,
            max_percentage=25.0
        )
        level3 = AssociateLevel(
            description="Manager",
            level_indicator=3,
            max_percentage=15.0
        )

        db.add_all([level1, level2, level3])
        db.commit()
        print(f"  - {level1}")
        print(f"  - {level2}")
        print(f"  - {level3}")

        # Create Performance Ratings
        print("\nCreating Performance Ratings...")
        rating1 = PerformanceRating(
            description="Needs Improvement",
            level_indicator=1
        )
        rating2 = PerformanceRating(
            description="Meets Expectations",
            level_indicator=2
        )
        rating3 = PerformanceRating(
            description="Exceeds Expectations",
            level_indicator=3
        )
        rating4 = PerformanceRating(
            description="Outstanding",
            level_indicator=4
        )

        db.add_all([rating1, rating2, rating3, rating4])
        db.commit()
        print(f"  - {rating1}")
        print(f"  - {rating2}")
        print(f"  - {rating3}")
        print(f"  - {rating4}")

        # Create Associates with hierarchy
        print("\nCreating Associates...")

        # Top-level manager
        ceo = Associate(
            first_name="Jane",
            last_name="Smith",
            associate_level_id=level3.id,
            is_people_manager=True,
            manager_id=None,
            performance_rating_id=rating4.id
        )
        db.add(ceo)
        db.commit()
        print(f"  - {ceo}")

        # Mid-level manager reporting to CEO
        manager = Associate(
            first_name="John",
            last_name="Doe",
            associate_level_id=level2.id,
            is_people_manager=True,
            manager_id=ceo.id,
            performance_rating_id=rating3.id
        )
        db.add(manager)
        db.commit()
        print(f"  - {manager}")

        # Individual contributors reporting to manager
        ic1 = Associate(
            first_name="Alice",
            last_name="Johnson",
            associate_level_id=level1.id,
            is_people_manager=False,
            manager_id=manager.id,
            performance_rating_id=rating2.id
        )
        ic2 = Associate(
            first_name="Bob",
            last_name="Williams",
            associate_level_id=level1.id,
            is_people_manager=False,
            manager_id=manager.id,
            performance_rating_id=None  # Not yet rated
        )

        db.add_all([ic1, ic2])
        db.commit()
        print(f"  - {ic1}")
        print(f"  - {ic2}")

        # Test relationships
        print("\n--- Testing Relationships ---")

        # Refresh to load relationships
        db.refresh(ceo)
        db.refresh(manager)

        print(f"\n{ceo.full_name}'s direct reports:")
        for report in ceo.direct_reports:
            print(f"  - {report.full_name}")

        print(f"\n{manager.full_name}'s direct reports:")
        for report in manager.direct_reports:
            rating_desc = report.performance_rating.description if report.performance_rating else "Not yet rated"
            print(f"  - {report.full_name} ({rating_desc})")

        print(f"\n{manager.full_name}'s manager: {manager.manager.full_name}")

        print("\n--- All Associates by Level ---")
        for level in [level1, level2, level3]:
            db.refresh(level)
            print(f"\n{level.description} (Level {level.level_indicator}):")
            for assoc in level.associates:
                print(f"  - {assoc.full_name}")

        print("\n✓ All tests passed successfully!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_models()
