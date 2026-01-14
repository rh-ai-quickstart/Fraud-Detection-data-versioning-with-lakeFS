# 🎬 Fraud Detection with lakeFS on OpenShift AI
## Video Tutorial Script

---

## VIDEO DETAILS
- **Duration:** ~12-15 minutes
- **Target Audience:** Data Scientists, ML Engineers, Platform Engineers
- **Key Technologies:** Red Hat OpenShift AI, lakeFS, MinIO, TensorFlow, Model Serving

---

## 🎬 OPENING SEQUENCE (0:00 - 1:00)

### [INTRO HOOK - Show architecture diagram]

**NARRATOR:**
> "Hey everyone! So here's a question that's probably kept you up at night if you've ever worked in ML—what if you could treat your training data the way developers treat code? You know, branch it, version it, roll it back when things go sideways?

> Well, that's exactly what we're gonna build today. I'm going to walk you through how Red Hat OpenShift AI and lakeFS work together to solve one of the most frustrating problems in machine learning: figuring out what the heck changed when your model suddenly stops working.

> Let's jump in!"

### [TITLE CARD]
```
FRAUD DETECTION WITH lakeFS
Data Versioning on Red Hat OpenShift AI
```

---

## 📋 SECTION 1: THE PROBLEM (1:00 - 2:30)

### [SHOW: Whiteboard or animated diagram]

**NARRATOR:**
> "Okay, so before we get our hands dirty, let me paint a picture that I'm sure a lot of you have lived through.

> You train a model. It's looking great—accuracy is up, stakeholders are happy, you push it to production. And then... something breaks. Maybe predictions start drifting. Maybe accuracy tanks. And now everyone's asking: 'What changed?'

> Was it the data? Did someone update the preprocessing pipeline? Did the model architecture get tweaked? Without proper versioning, you're basically playing detective with no clues. It's a nightmare."

### [SHOW: Four key questions appearing on screen]

**NARRATOR:**
> "So here's the goal. By the time we're done today, you'll be able to answer questions like:

> Which exact version of the data trained the model that's running in production right now? What's different between the data we used for version one versus version two? Can we reproduce last month's results exactly—like, down to the decimal? And if something bad ships, can we roll back immediately?

> Spoiler alert: yes, we can. Let me show you how."

---

## 🏗️ SECTION 2: ARCHITECTURE OVERVIEW (2:30 - 4:00)

### [SHOW: Architecture diagram with animations highlighting each component]

**NARRATOR:**
> "Alright, let's look at what we're building. Here's our architecture running inside an OpenShift cluster. Don't worry—it looks more complicated than it is.

> We've basically got three layers working together:"

### [HIGHLIGHT: MinIO]
> "Down here, we've got MinIO. This is our storage layer—think of it as where all the actual files live. Your datasets, your trained models, all those pickle files... they're all sitting in MinIO, which gives us S3-compatible object storage."

### [HIGHLIGHT: lakeFS]
> "Now here's where things get interesting—lakeFS. This is the secret sauce. It sits on top of MinIO and basically gives you Git superpowers for your data. Branching, commits, merges, reverts—all the stuff you already know from code, but now for datasets. And the cool part? It exposes an S3 API, so your existing tools just work. No code changes needed."

### [HIGHLIGHT: OpenShift AI]
> "And tying it all together is OpenShift AI—that's Red Hat's MLOps platform. It gives us Jupyter notebooks for experimentation, ModelMesh for serving models at scale, pipelines, and even distributed training with Ray. The whole nine yards."

**NARRATOR:**
> "Here's what I love about this setup: OpenShift AI just talks to lakeFS like it's any other S3 bucket. Your data scientists don't have to learn anything new—they just suddenly get version control for free."

---

## 🚀 SECTION 3: DEPLOYMENT (4:00 - 5:30)

### [SHOW: Terminal screen with commands]

**NARRATOR:**
> "Okay, enough talking—let's actually deploy this thing. We've wrapped everything up in a Makefile to keep it simple."

### [TYPE/EXECUTE:]
```bash
# Clone the repository
git clone https://github.com/rh-ai-quickstart/Fraud-Detection-data-versioning-with-lakeFS.git
cd Fraud-Detection-data-versioning-with-lakeFS/deploy

# Login to OpenShift
oc login --token=<your-token> --server=https://api.<cluster>:6443

# Deploy everything with one command
make install
```

**NARRATOR:**
> "So we clone the repo, cd into the deploy folder, log into our cluster, and then just run `make install`. That's it.

> Behind the scenes, the Makefile figures out that we're on OpenShift, creates our namespace, and spins up lakeFS, MinIO, a Postgres database for the model registry, and our Jupyter notebook environment. All in one go.

> Let's check if everything came up okay."

### [TYPE/EXECUTE:]
```bash
make get-pods
```

### [SHOW: Pods running]

**NARRATOR:**
> "Nice—all our pods are running. Let's grab the URLs we'll need to access everything."

### [TYPE/EXECUTE:]
```bash
make get-routes
```

---

## 🌿 SECTION 4: EXPLORING lakeFS (5:30 - 7:00)

### [SHOW: Browser navigating to lakeFS UI]

**NARRATOR:**
> "Alright, let's pop open the lakeFS UI. This is basically your command center for data version control."

### [DEMO: lakeFS UI Navigation]

**NARRATOR:**
> "So here you can see our repositories. If you've used Git before, this should feel pretty familiar—except instead of code, we're versioning data. We've got 'my-storage' where our ML stuff lives, and 'quickstart' with some sample data to play with.

> See how we've got branches here? Just like Git. There's main—that's our production data. And we can create experiment branches off of it whenever we want to try something new."

### [SHOW: S3 path structure]

**NARRATOR:**
> "Here's the trick that makes this all work. LakeFS uses S3 paths that look like this:

> `s3://repository/branch/path/to/object`

> So if I want to read my training data from the main branch, that's:
> `s3://fraud/main/data/transactions.csv`

> But if I'm experimenting on a branch called exp-01, I just change the path:
> `s3://fraud/exp-01/data/transactions.csv`

> Same S3 calls, totally different versions. And here's the kicker—branches don't actually copy the data. They're just pointers. So you're not blowing up your storage every time you create a new experiment."

---

## 🧪 SECTION 5: TRAINING WITH VERSION CONTROL (7:00 - 10:00)

### [SHOW: Jupyter notebook environment in OpenShift AI]

**NARRATOR:**
> "Now for the fun part—let's actually train a model. I'll hop into OpenShift AI and open up our notebook. Everything's already wired up to talk to lakeFS and MinIO."

### [SHOW: Notebook 1 - experiment_train_lakefs.ipynb]

**NARRATOR:**
> "Here's our fraud detection notebook. Let me highlight the key pieces where lakeFS comes into play."

### [HIGHLIGHT: Branch Creation Code]
```python
# Create an isolated training branch
branchTraining = repo.branch("train01").create(
    source_reference="main", 
    exist_ok=True
)
```

**NARRATOR:**
> "First thing we do—create a training branch. This is huge. Now anything I read or write during this experiment is completely isolated. I could totally mess things up, and the production data on main wouldn't be touched. It's like having a sandbox for your data."

### [HIGHLIGHT: Data Loading with Version]
```python
# Load versioned data using S3 paths with branch names
df = pd.read_csv(
    f"s3://{repo_name}/{trainingBranch}/data/train.csv",
    storage_options=lakefs_storage_options
)
```

**NARRATOR:**
> "Then we load our training data—and notice, we're just using regular pandas here. Nothing fancy. But that branch name in the path? That's what pins us to a specific version. No more wondering 'wait, which dataset did I train on again?'"

### [RUN: Training cells - show model building]

**NARRATOR:**
> "Our model's pretty straightforward—it's a neural network with three hidden layers built in Keras. Good enough to catch fraudulent transactions, not so complex that we're waiting around all day. Let me kick off the training..."

### [SHOW: Training progress and metrics]

**NARRATOR:**
> "And we're done! Now watch this—this is where lakeFS really shines."

### [HIGHLIGHT: Saving Artifacts]
```python
# Save preprocessing artifacts to the versioned branch
obj = branchTraining.object(path='artifact/scaler.pkl')
with obj.writer("wb") as handle:
    pickle.dump(scaler, handle)
```

**NARRATOR:**
> "We're saving our preprocessing scaler right to the lakeFS branch. Same goes for our test data and any other artifacts. This means six months from now, when someone asks 'hey, which scaler did you use for that model?'—you've got the answer. It's versioned alongside everything else."

### [SHOW: Notebook 2 - save_model_lakefs.ipynb]

**NARRATOR:**
> "Okay, training's done. Now let's save that model."

### [HIGHLIGHT: Model Upload and Commit]
```python
# Upload model to branch
upload_directory_to_s3("models", f"{trainingBranch}/models")

# Commit the changes - create an immutable snapshot
ref = branchTraining.commit(message='Uploaded data, artifacts and model')
```

**NARRATOR:**
> "We upload the model to our branch, and then—here's the important part—we commit. Just like in Git. This creates an immutable snapshot. From this moment on, we can always come back to exactly this version of the model, the data, the preprocessing, everything. That's what I mean by reproducibility by design. It's baked in."

---

## 🔮 SECTION 6: MODEL SERVING (10:00 - 11:30)

### [SHOW: OpenShift AI Model Serving or REST inference notebook]

**NARRATOR:**
> "So we've got a trained model. Now let's actually use it. OpenShift AI comes with ModelMesh built in, which makes serving models at scale pretty painless."

### [SHOW: REST Inference Demo]

**NARRATOR:**
> "Let's throw some predictions at it. We'll use simple REST calls."

### [RUN: Inference examples]
```python
# Coffee purchase - legitimate transaction
data = [0.0, 1.0, 1.0, 1.0, 0.0]  # nearby, normal price, chip, pin, not online
# Result: "not fraud"

# Suspicious transaction - potential fraud
data = [100, 1.2, 0.0, 0.0, 1.0]  # far away, no chip, no pin, online
# Result: "fraud"
```

**NARRATOR:**
> "So here's a normal transaction—someone buying a coffee nearby, using their chip and PIN. Model says: not fraud. Makes sense.

> But now look at this one—transaction from way far away, no chip, no PIN, it's online. Model flags it as fraud. Working as expected.

> And here's a detail that matters: our inference code pulls the scaler from that same lakeFS branch. So the preprocessing and the model are always guaranteed to match. You'd be surprised how often that breaks in production when people aren't careful."

---

## ⚡ SECTION 7: DISTRIBUTED TRAINING WITH RAY (11:30 - 13:00)

### [SHOW: Distributed training notebook]

**NARRATOR:**
> "Now, our fraud model is pretty small—trains in seconds. But what about when you're dealing with massive models that need multiple GPUs or even multiple machines? That's where Ray and CodeFlare come in. Let me show you how lakeFS fits into distributed training."

### [HIGHLIGHT: Ray Cluster Configuration]
```python
cluster = Cluster(ClusterConfiguration(
    name="raycluster-cpu",
    num_workers=2,
    worker_cpu_limits=4,
    worker_memory_limits=4,
    image="quay.io/modh/ray:2.35.0-py39-cu121"
))
```

**NARRATOR:**
> "We define a Ray cluster—two workers in this case, but you could scale this way up. CodeFlare handles all the Kubernetes stuff under the hood, spinning up pods, managing resources, all that."

### [HIGHLIGHT: Environment Variables with lakeFS]
```python
"env_vars": {
    "TRAIN_DATA": f"{trainingBranch}/data/train.csv",
    "MODEL_OUTPUT_PREFIX": f"{trainingBranch}/models/fraud/1/",
}
```

**NARRATOR:**
> "And look—the training job still reads and writes through lakeFS. So even when you've got multiple workers churning away across different machines, all your artifacts end up in the same versioned branch. The governance stays intact. Pretty slick, right?"

---

## 🔄 SECTION 8: THE POWER OF BRANCHING (13:00 - 14:00)

### [SHOW: lakeFS UI - branch comparison view]

**NARRATOR:**
> "Alright, let me show you why this branching thing is such a big deal in practice.

> Say you want to retrain with updated labels—maybe you fixed some mislabeled data. Here's the workflow:

> Create a new branch off your training branch. Make your changes there. Retrain. Compare results.

> If the new model's better? Merge it to main. If it's worse or something's weird? Just delete the branch and walk away. No rollback scripts, no corrupted data, no panic. It's the same workflow developers use every day with code."

### [SHOW: Merge or Revert options]

**NARRATOR:**
> "This is what controlled promotion looks like. Main is protected—you can't just push whatever you want there. Changes come through validated merges. And if you're feeling fancy, you can add pre-merge hooks that run data quality checks, validate schemas, scan for PII—all before anything touches production."

---

## 🎯 SECTION 9: WRAP-UP (14:00 - 15:00)

### [SHOW: Architecture diagram again]

**NARRATOR:**
> "Okay, let's bring it all together. Here's what we built:

> Red Hat OpenShift gives us that solid enterprise Kubernetes foundation. OpenShift AI adds the ML-specific tools—notebooks, model serving, distributed training. lakeFS brings Git-style version control to our data. And MinIO handles the actual storage.

> Put them together, and you've got a complete AI data control plane. Every model can be traced back to exactly the data it was trained on. Every experiment is isolated. Every change is auditable. That's the dream, right?"

### [SHOW: Call to action]

**NARRATOR:**
> "Wanna try it yourself? Clone the repo, run `make install`, and you'll have this whole stack up and running in just a few minutes.

> The README has all the details, and there are more notebooks in there for multi-model serving, gRPC inference, and other advanced patterns worth exploring.

> Thanks for watching, and happy versioning! I'll catch you in the next one."

---

## 📝 POST-PRODUCTION NOTES

### B-Roll Suggestions:
- Terminal commands executing
- lakeFS UI navigation
- OpenShift console showing pods
- Jupyter notebook cells executing
- Model training progress bars
- Confusion matrix visualization

### Graphics Needed:
- Title card with project logo
- Architecture diagram animation
- S3 path structure visualization
- Branch/merge workflow animation
- "Before/After" reproducibility comparison

### Music:
- Upbeat, tech-focused background music
- Lower during voiceover sections
- Accent sounds for transitions

### Timestamps for Chapters:
```
0:00 - Introduction
1:00 - The Problem
2:30 - Architecture Overview
4:00 - Deployment
5:30 - Exploring lakeFS
7:00 - Training with Version Control
10:00 - Model Serving
11:30 - Distributed Training
13:00 - The Power of Branching
14:00 - Wrap-Up
```

---

## 🎤 SPEAKER NOTES

### Tone Guidelines:
- Keep it conversational—you're explaining this to a colleague over coffee
- Use contractions: "we're", "it's", "don't", "you've"
- Add natural pauses and transitions: "So...", "Now...", "Alright..."
- Share genuine reactions: "Pretty slick, right?", "Here's what I love about this"
- Acknowledge viewer experience: "I'm sure a lot of you have lived through this"

### Key Messages to Emphasize:
1. **Git for Data** - Same workflows developers already know
2. **No Code Changes** - S3 compatibility means existing tools just work
3. **Reproducibility** - Always trace models back to exact data versions
4. **Enterprise Ready** - Built on OpenShift with full RBAC and security

### Common Questions to Address:
- "Does branching duplicate data?" → No, branches are just pointers—metadata only
- "Can I use PyTorch instead?" → Absolutely, any S3-compatible framework works
- "What about GPUs?" → OpenShift AI handles GPU scheduling out of the box

### Pacing Tips:
- Slow down when showing code—give viewers time to read
- Speed up slightly during routine terminal commands
- Pause after key insights to let them sink in
- Keep energy up during transitions between sections

### Demo Tips:
- Pre-run notebooks to avoid waiting during recording
- Have tabs pre-opened for smooth transitions
- Use terminal zoom for readability
- Highlight key code sections with cursor movements
