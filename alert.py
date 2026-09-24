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
    for r in results:
        title = f"DOWN: {r['name']}"
        if not r["ok"] and title not in by_title:
            gh("issue", "create", "--label", LABEL, "--title", title, "--body",
               f"{r['url']}\n\n{r['problem']}\n\nChecked from GitHub Actions; this issue closes itself when the check passes again.")
        elif r["ok"] and title in by_title:
            gh("issue", "close", str(by_title[title]), "--comment", f"Recovered: {r['url']} answers normally again.")


if __name__ == "__main__":
    main()
