#!/this/is/not/supposed/to/be/called/directly

set -ex

poetry update
if git status --porcelain | grep "M poetry.lock" ; then
    git add poetry.lock
    git commit -m "Updates dependencies"
fi

poetry version minor
git add pyproject.toml
git commit -m "Bumps version to $(poetry version | cut -d ' ' -f 2) (maintenance build)"
