# update project

git fetch
git merge origin/main

virtualenv --no-download .venv
source .venv/bin/activate

pip install -r requirements.txt


pytest
