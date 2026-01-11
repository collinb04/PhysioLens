from app.services.analytics.pipeline import run_pipeline

for user in ["User1", "UserExercise", "UserSleep"]:
    res = run_pipeline(user)

    print("=" * 50)
    print("USER:", user)
    print()

    print("TITLE:")
    print(res["summary"]["insight"]["title"])
    print()

    print("BODY:")
    print(res["summary"]["insight"]["body"])
    print()

    print("FACTORS:")
    for f in res["summary"]["factors"]:
        print(
            f"- {f['key']}: "
            f"{f['percent']:.1f}% | "
            f"occurrences={f['occurrences']} | "
            f"avg_abs_z={f['avg_abs_z']:.2f}"
        )

    print()
    print("DOMINANT FACTOR:", res["summary"]["dominant_key"])
    print("STABLE RECOVERY:", res["summary"]["stable"])
    print("DIP COUNT:", res["summary"]["meta"]["dip_count"])
    print()

