#!/usr/bin/env python
# coding: utf-8

# Importing all of the necessary modules

# In[2]:


from scripts.embedding import model, MODEL_NAME, BATCH_SIZE, embed, index_embeddings
from scripts.bugsinpy_utils import *

import faiss
import numpy as np
import json, os


# Making sure the directories exist

# In[3]:


os.makedirs(os.path.abspath(f"tmp/ast/results"), exist_ok=True)
K = 60


# Running each eligible bug through the model and embedding them, after then running cosine similarity to determine which files they think it should be changed

# In[ ]:


def compute_average_precision(y_true):
    hits = 0
    sum_precisions = 0.0
    for i, rel in enumerate(y_true):
        if rel:
            hits += 1
            sum_precisions += hits / (i + 1)
    return sum_precisions / max(hits, 1)

def compute_reciprocal_rank(y_true):
    for i, rel in enumerate(y_true, start=1):  # ranks start at 1
        if rel:
            return 1.0 / i
    return 0.0  # no relevant item found in top K


# In[4]:


projects = get_projects()
all_ap = []
all_rr = []

for project in projects:
    bugs = get_bugs(project)
    # embedding_index_path = f"tmp/ast/embeddings/index_{project}.faiss"
    bug_result_path = os.path.abspath(f"tmp/ast/results/bug_results_{project}.json")
    filtered_bugs = []
    error_texts = []

    # First pass: filter bugs and collect error traces
    for bug in bugs:
            
        changed_files = parse_changed_files(project, bug)
        if len(changed_files) > 1:
            continue
        info = get_bug_info(project, bug)
        error = extract_python_tracebacks(project, bug)
        if error:
            filtered_bugs.append(bug)
            error_texts.append(error)

    # Batch encode
    if error_texts:
        error_embeddings = embed(error_texts, batch_size=BATCH_SIZE, show_progress_bar=True)

        output = []

        for bug, emb in zip(filtered_bugs, error_embeddings):
            code_chunks_path = f"dataset/{project}/{bug}/code_chunks.json"
            with open(code_chunks_path, "r") as f:
                code_chunks = json.loads(f.read())
            embedding_path = f"dataset/{project}/{bug}/embedding.npy"
            embeddings = np.load(embedding_path)
            index = index_embeddings(embeddings)
            D, I = index.search(np.array([emb]).astype("float32"), k=K)
            search_results = {"index": bug, "files": []}
            for idx in I[0]:
                result = code_chunks[idx]
                search_results["files"].append(
                    {"file": result["file"], "function": result["name"]}
                )
            output.append(search_results)
            
            changed_file = parse_changed_files(project, bug)[0].split("/")[-1]
            y_true = [1 if code_chunks[idx]["file"] == changed_file else 0 for idx in I[0]]
            ap = compute_average_precision(y_true)
            rr = compute_reciprocal_rank(y_true)

            all_ap.append(ap)
            all_rr.append(rr)

        with open(bug_result_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)


# Using that predictions to calculate success rate and show where each search was successful or not.

# In[9]:





# In[5]:


results_folder = os.path.abspath("tmp/ast/results")
results_files = os.listdir(results_folder)
def analyze(k):
    results = {
        "K": k,
        "model_name": MODEL_NAME,
        "searches_failed": [],  # [{project_name, bug_id, detected_files: list, actual_file}]
        "searches_passed": [],  # [{project_name, bug_id, detected_files: list, actual_files}]
        "success_rate": 0,  # out of 100 (including bugs skipped)
        "MAP": np.mean(all_ap),
        "MRR": np.mean(all_rr),
        "success_projects": {},  # {project_name, success_rate, success_rate_no_skip}
    }
    success_projects_tmp = {}
    count = 0
    maximum_bugs = 0
    for project in results_files:
        project_name = project.replace("bug_results_", "").replace(".json", "")
        bugs = get_bugs(project_name)
        maximum_bugs += len(bugs)
        success_projects_tmp[project_name] = {
            "failed": 0,
            "passed": 0,
            "total": 0,
        }

        with open(f"{results_folder}/{project}", "r", encoding="utf-8") as result_file:
            data = json.loads(result_file.read())
            for search_result in data:
                changed_file = parse_changed_files(project_name, search_result["index"])[0].split("/")[-1]
                files_predicted = [
                    obj["file"].split("/")[-1] for obj in search_result["files"][:k]
                ]
                if changed_file in files_predicted:
                    results["searches_passed"].append(
                        {
                            "project_name": project_name,
                            "bug_id": search_result["index"],
                            "detected_files": files_predicted,
                            "actual_file": changed_file,
                        }
                    )
                    success_projects_tmp[project_name]["passed"] += 1
                    success_projects_tmp[project_name]["total"] += 1
                else:
                    results["searches_failed"].append(
                        {
                            "project_name": project_name,
                            "bug_id": search_result["index"],
                            "detected_files": files_predicted,
                            "actual_file": changed_file,
                        }
                    )
                    success_projects_tmp[project_name]["failed"] += 1
                    success_projects_tmp[project_name]["total"] += 1
                    


        searches_counted = (
            success_projects_tmp[project_name]["passed"]
            + success_projects_tmp[project_name]["failed"]
        )

        results["success_projects"][project_name] = {
            "success_rate": success_projects_tmp[project_name]["passed"] / searches_counted,
        } | success_projects_tmp[project_name]

    results["success_rate"] = len(results["searches_passed"]) / (len(results["searches_failed"]) + len(results["searches_passed"]))
    with open(os.path.abspath(f"results_{k}.json"), "w", encoding="utf-8") as file:
        file.write(json.dumps(results, indent=2))
        
analyze(5)
analyze(10)
analyze(15)
analyze(20)


# In[9]:


import json

# Load your data
with open("results_5.json", "r") as f:
    data = json.load(f)

# Desired project order
ordered_projects = [
    "youtube-dl",
    "keras",
    "matplotlib",
    "black",
    "thefuck",
    "scrapy",
    "pandas",
    "luigi",
]

# Print header
print(f"{'Project':<15} {'Passed':>6} {'Failed':>6} {'Total':>6} {'Success Rate':>13}")
print("=" * 50)

# Print each project in order
for project in ordered_projects:
    stats = data["success_projects"][project]
    passed = stats["passed"]
    failed = stats["failed"]
    total = stats["total"]
    rate = stats["success_rate"]
    print(rate)

# Print overall success rate
print("\nOverall Success Rate:", f"{data['success_rate'] * 100:.2f}%")

