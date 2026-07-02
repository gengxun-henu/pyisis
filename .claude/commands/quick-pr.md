# Quick PR: Branch → Push → PR → Merge

Automates the workflow of creating a PR from the current working state, especially when working on `main` or `master`.

## Usage

```
/quick-pr [branch-name] [PR title]
```

- `branch-name` (optional): Name for the new branch. Defaults to `feat/quick-pr-<timestamp>`.
- `PR title` (optional): Title for the PR. If omitted, Claude will generate one from the commit messages.

## Instructions

Execute the following steps in order. Stop and report any failure.

### Step 1: Detect current branch

```bash
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"
```

### Step 2: Check for uncommitted changes

```bash
git status --porcelain
```

If there are uncommitted changes, stage and commit them:

```bash
git add -A
git commit -m "<generate a descriptive commit message from the diff summary>"
```

The commit message must end with:
```
Co-Authored-By: gengxun <gengxun@henu.edu.cn> and Claude <noreply@anthropic.com>
```

### Step 3: If on main/master, create a new branch

If `$CURRENT_BRANCH` is `main` or `master`:

```bash
BRANCH_NAME="${1:-feat/quick-pr-$(date +%Y%m%d-%H%M%S)}"
git checkout -b "$BRANCH_NAME"
echo "Created branch: $BRANCH_NAME"
```

If already on a feature branch, use that branch directly.

### Step 4: Push the branch

```bash
git push -u origin "$BRANCH_NAME"
```

### Step 5: Create a Pull Request

List commits for the PR body:

```bash
git log --oneline origin/main..HEAD
```

Create the PR using `gh`:

```bash
gh pr create \
  --base main \
  --title "<PR title from argument or generated from commits>" \
  --body "<PR body with commit list and summary>"
```

The PR body must end with:
```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### Step 6: Merge the PR

Wait for the PR to be mergeable, then merge:

```bash
gh pr merge --merge --delete-branch
```

If merge fails (e.g., requires review), report the PR URL and status.

### Step 7: Clean up

Switch back to main and pull:

```bash
git checkout main
git pull origin main
```

### Step 8: Report

Print a summary:
- Branch name
- PR URL
- Merge status
- Number of commits included
