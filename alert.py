"""Open one GitHub issue per failing check and close it when the check recovers.

GitHub emails the repository owner about new issues and comments, which is the
alert. Uses the gh CLI with the workflow's GITHUB_TOKEN.
"""
import json
import subprocess

LABEL = "down"


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def main():
    results = json.load(open("results.json"))
    subprocess.run(["gh", "label", "create", LABEL, "--color", "B42318", "--description", "Site down"],
                   capture_output=True)
    open_issues = json.loads(gh("issue", "list", "--label", LABEL, "--state", "open", "--json", "number,title"))
    by_title = {i["title"]: i["number"] for i in open_issues}
    failing = {f"DOWN: {r['name']}": r for r in results if not r["ok"]}
    for title, r in failing.items():
        if title not in by_title:
            gh("issue", "create", "--label", LABEL, "--title", title, "--body",
               f"{r['url']}\n\n{r['problem']}\n\nChecked from GitHub Actions; this issue closes itself when the check passes again.")
    # Close every open alert that is not failing now: recovered checks, and
    # checks that were removed from checks.json.
    for title, number in by_title.items():
        if title not in failing:
            gh("issue", "close", str(number), "--comment", "Recovered: passing again (or no longer checked).")


if __name__ == "__main__":
    main()
