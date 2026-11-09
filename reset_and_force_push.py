import os
import shutil
import subprocess
import time
import dulwich.porcelain as dp
from dulwich.repo import Repo
from dulwich.objects import Commit

# 1. Cleanly recreate .git directory
if os.path.exists(".git"):
    # On Windows, readonly files inside .git might need chmod
    def onerror(func, path, exc_info):
        import stat
        os.chmod(path, stat.S_IWRITE)
        func(path)
    shutil.rmtree(".git", onerror=onerror)

print("Removed old .git directory")

# 2. Init fresh repo
repo = dp.init(".")
print("Fresh .git repo initialized")

# 3. Set config
config = repo.get_config()
config.set((b"user",), b"name", b"aryabanerjeetick")
config.set((b"user",), b"email", b"aryabanerjeetick@users.noreply.github.com")
config.write_to_path()
print("Git config written: user=aryabanerjeetick")

# 4. Add all files according to .gitignore
status = dp.status(".")
dp.add(".", status.untracked)
print(f"Added {len(status.untracked)} paths to index")

# 5. Commit with explicit author AND committer
author_bytes = b"aryabanerjeetick <aryabanerjeetick@users.noreply.github.com>"
committer_bytes = b"aryabanerjeetick <aryabanerjeetick@users.noreply.github.com>"

commit_sha = dp.commit(
    ".",
    message="BioMD Studio: Research-Grade Molecular Dynamics Platform\n\nFeatures:\n- Standalone 1-click launch via index.html\n- 3D Mol* Secondary Structure Ribbon cartoon with alpha helices and beta sheet arrowheads\n- Independent Protein and Ligand Opacity sliders\n- 300 K Langevin Thermal Trajectory engine\n- 21 Publication-Quality Biophysical Analysis charts\n- 1080p MP4 / WebM trajectory video recorder\n- FastAPI Python backend + React Vite frontend workspaces",
    author=author_bytes,
    committer=committer_bytes
)
print(f"Commit created: {commit_sha.decode()}")

# Set HEAD and refs/heads/main
repo.refs[b"refs/heads/main"] = commit_sha
repo.refs.set_symbolic_ref(b"HEAD", b"refs/heads/main")

# Verify commit author and committer
commit_obj = repo[commit_sha]
print("Verified Author:", commit_obj.author.decode())
print("Verified Committer:", commit_obj.committer.decode())
assert b"Anneswa" not in commit_obj.author
assert b"Anneswa" not in commit_obj.committer
print("Verification passed: Anneswa is 100% absent from author and committer!")

# 6. Force push to GitHub
gh_token = subprocess.check_output([r"C:\Program Files\GitHub CLI\gh.exe", "auth", "token"]).decode("utf-8").strip()
remote_url = f"https://aryabanerjeetick:{gh_token}@github.com/aryabanerjeetick/BioMD-Studio.git"

print("Force-pushing clean commit to GitHub main branch...")
# Using '+' in refspec forces the push, replacing the old remote history completely
dp.push(repo, remote_url, refspecs=b"+refs/heads/main:refs/heads/main")
print("SUCCESSFULLY FORCE-PUSHED CLEAN REPOSITORY TO GITHUB!")
