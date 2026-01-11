from app.services.analytics.pipeline import run_pipeline

res = run_pipeline("user1")
print(res["summary"]["insight"]["title"])
print(res["summary"]["insight"]["body"])
print(res["summary"]["factors"])
