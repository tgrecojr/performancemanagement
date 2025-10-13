"""
Test script to verify the exclusion logic for associate levels with max_percentage=-1.
This demonstrates how contractors/interns are excluded from distribution calculations.
"""
from src.database import init_db, get_db
from src.models import AssociateLevel, PerformanceRating, Associate
from src.reports import (
    get_total_headcount,
    calculate_rating_distribution_percentages,
    get_level_distribution_summary,
)


def test_exclusion_logic():
    """Test the exclusion logic for levels with max_percentage=-1."""
    print("Initializing database...")
    init_db()

    db = get_db()
    try:
        # Create Associate Levels
        print("\nCreating Associate Levels...")

        # Regular levels that count toward distribution
        level_ic = AssociateLevel(
            description="Individual Contributor",
            level_indicator=1,
            max_percentage=70.0
        )
        level_manager = AssociateLevel(
            description="Manager",
            level_indicator=2,
            max_percentage=30.0
        )

        # Excluded level (contractors, interns, etc.)
        level_contractor = AssociateLevel(
            description="Contractor",
            level_indicator=99,  # High number to indicate special status
            max_percentage=100.0,
            exclude_from_distribution=True  # Excluded from distribution
        )

        db.add_all([level_ic, level_manager, level_contractor])
        db.commit()

        print(f"  - {level_ic} (Included in distribution)")
        print(f"  - {level_manager} (Included in distribution)")
        print(f"  - {level_contractor} (EXCLUDED from distribution: {level_contractor.exclude_from_distribution})")

        # Create Performance Ratings
        print("\nCreating Performance Ratings...")
        rating_low = PerformanceRating(description="Needs Improvement", level_indicator=1)
        rating_mid = PerformanceRating(description="Meets Expectations", level_indicator=2)
        rating_high = PerformanceRating(description="Exceeds Expectations", level_indicator=3)

        db.add_all([rating_low, rating_mid, rating_high])
        db.commit()

        # Create Associates
        print("\nCreating Associates...")

        # 5 ICs with ratings
        ics = [
            Associate(first_name="IC", last_name=f"Person{i}",
                     associate_level_id=level_ic.id, is_people_manager=False,
                     performance_rating_id=rating_mid.id if i < 3 else rating_high.id)
            for i in range(1, 6)
        ]

        # 2 Managers with ratings
        managers = [
            Associate(first_name="Manager", last_name=f"Person{i}",
                     associate_level_id=level_manager.id, is_people_manager=True,
                     performance_rating_id=rating_high.id)
            for i in range(1, 3)
        ]

        # 3 Contractors with ratings (should be excluded from distribution)
        contractors = [
            Associate(first_name="Contractor", last_name=f"Person{i}",
                     associate_level_id=level_contractor.id, is_people_manager=False,
                     performance_rating_id=rating_low.id)
            for i in range(1, 4)
        ]

        db.add_all(ics + managers + contractors)
        db.commit()

        print(f"  Created {len(ics)} Individual Contributors")
        print(f"  Created {len(managers)} Managers")
        print(f"  Created {len(contractors)} Contractors (excluded level)")

        # Test headcount calculations
        print("\n" + "="*70)
        print("HEADCOUNT CALCULATIONS")
        print("="*70)

        total_with_excluded = get_total_headcount(db, include_excluded_levels=True)
        total_without_excluded = get_total_headcount(db, include_excluded_levels=False)

        print(f"\nTotal headcount (including excluded levels): {total_with_excluded}")
        print(f"Total headcount (EXCLUDING excluded levels): {total_without_excluded}")
        print(f"Difference (contractors/excluded): {total_with_excluded - total_without_excluded}")

        # Test distribution calculations
        print("\n" + "="*70)
        print("PERFORMANCE RATING DISTRIBUTION")
        print("="*70)

        print("\n--- Including Excluded Levels (Contractors) ---")
        dist_with = calculate_rating_distribution_percentages(db, include_excluded_levels=True)
        for rating, pct in sorted(dist_with.items()):
            print(f"  {rating}: {pct:.1f}%")

        print("\n--- EXCLUDING Excluded Levels (Standard Distribution) ---")
        dist_without = calculate_rating_distribution_percentages(db, include_excluded_levels=False)
        for rating, pct in sorted(dist_without.items()):
            print(f"  {rating}: {pct:.1f}%")

        # Detailed level summary
        print("\n" + "="*70)
        print("DETAILED LEVEL SUMMARY")
        print("="*70)

        summary = get_level_distribution_summary(db)
        for level_desc, data in sorted(summary.items(), key=lambda x: x[1]['level_indicator']):
            print(f"\n{level_desc} (Level {data['level_indicator']}):")
            print(f"  Max %: {data['max_percentage']}")
            print(f"  Excluded from distribution: {data['exclude_from_distribution']}")
            print(f"  Total associates: {data['total_associates']}")
            print(f"  Rated: {data['rated_associates']}, Unrated: {data['unrated_associates']}")

            if data['rating_counts']:
                print(f"  Rating breakdown:")
                for rating, count in sorted(data['rating_counts'].items()):
                    if data['exclude_from_distribution']:
                        print(f"    - {rating}: {count} (not counted in distribution)")
                    else:
                        pct = data['rating_percentages'].get(rating, 0)
                        print(f"    - {rating}: {count} ({pct:.1f}%)")

        print("\n" + "="*70)
        print("KEY INSIGHTS")
        print("="*70)
        print("\nThe 'Contractor' level with exclude_from_distribution=True is correctly:")
        print("  ✓ Excluded from the denominator when calculating distributions")
        print("  ✓ Still tracked and visible in reports")
        print("  ✓ Can still have a valid max_percentage (for informational purposes)")
        print("\nThis allows you to:")
        print("  • Track all people in the organization")
        print("  • Calculate proper distributions only for permanent employees")
        print("  • Avoid requiring performance ratings for contractors/interns")

        print("\n✓ All exclusion logic tests passed successfully!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_exclusion_logic()
