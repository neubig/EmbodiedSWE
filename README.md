# EmbodiedSWE: Coding Agents for Long-Horizon Dexterous Robotics

## About this migration fork

This is [neubig/EmbodiedSWE](https://github.com/neubig/EmbodiedSWE), a fork of
[EmbodiedSWE/EmbodiedSWE](https://github.com/EmbodiedSWE/EmbodiedSWE).
Its `main` branch targets **Isaac Sim 6.1 / Isaac Lab 3.0 Early Access**,
not the upstream reference runtime. The original benchmark description and
broader workflows below are retained; their full migration is not validated.

Validated: clean native bulb/Franka/OSC environment build and a real 20-step
controller through the native grader and unmodified Harbor, with valid zero
rewards and no exceptions. This demonstrates execution, not task-solving success
or full-suite/cross-version parity. Newton/deformable and multi-stage Harbor
workflows are not qualified by this validation.

For portable dataset generation followed by standard `harbor run`, use
[llm-for-robotics-benchmark](https://github.com/neulab/llm-for-robotics-benchmark#embodiedswe-when-a-gpu-is-available).
Use its pinned source revision for reproducibility. On Babel, NHC kills the
grader's subordinate host UID as unauthorized when a run overlaps a health check;
see the integration repository's remediation guidance before unattended runs.
This requires administrator-approved cluster compatibility, not a Harbor patch.

*Migration implementation and this fork-specific guidance were authored by
OpenHands, an AI agent, on behalf of Graham Neubig.*


<p align="center">
  <img src="docs/media/overview.jpg" width="100%" alt="EmbodiedSWE overview">
</p>

<p align="center">
  <a href="https://arxiv.org/abs/2609.27308"><img src="https://img.shields.io/badge/arXiv-2609.27308-b31b1b?style=for-the-badge&logo=arxiv&logoColor=white" alt="arXiv"></a>
  <a href="https://embodiedswe.github.io"><img src="https://img.shields.io/badge/Project%20Page-4c8eda?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Project page"></a>
  <a href="#"><img src="https://img.shields.io/badge/Blog-coming%20soon-6f42c1?style=for-the-badge&logo=rss&logoColor=white" alt="Blog"></a>
</p>

EmbodiedSWE studies how frontier coding agents can help robotics. It has four parts:

- **EmbodiedSWE-Bench**, an agent-native benchmark of long-horizon, dexterous everyday tasks, built on Isaac Lab.
- **Evaluation** of frontier coding agents on these tasks: task performance, completion time, and inference cost.
- **EmbodiedSWE-Gen**, which diversifies one verified agent solution into a large trajectory dataset for training general robot policies.
- **Agent improvement**, which generates new tasks from existing ones and improves the coding agent with RL on verified outcomes.

See the [paper](https://arxiv.org/abs/2609.27308) for the full benchmark, evaluation, and data-generation details.

> **Note:** this repository is under active development. Folder layouts, interfaces, and settings
> may change as the codebase evolves.

## Installation

Requirements: Linux, an NVIDIA GPU with a CUDA 12.x driver, Apptainer, and
[`uv`](https://docs.astral.sh/uv/). Obtain the gated official Isaac Sim 6.1.0 container and
`IsaacLab-3.0.0-EA` source archive from NVIDIA. The bootstrap verifies the exact artifacts used for
this migration and creates a repository-local runtime; it does not modify a shared environment.

```bash
git clone https://github.com/neubig/EmbodiedSWE.git
cd EmbodiedSWE
export ISAAC_SIM_SIF=/path/to/isaac-sim-6.1.0.sif
export ISAACLAB_ARCHIVE=/path/to/IsaacLab-3.0.0-EA.tar.gz
./scripts/bootstrap_isaaclab_6_1.sh
export OMNI_KIT_ACCEPT_EULA=YES
# The script prints ready-to-run unit-test and Franka/OSC smoke commands.
```

The validated reference artifacts have SHA-256
`e1c36e8b837c956d2d4216258c6af42b2b049bfc159e05963a30353c2c337187` (Sim SIF) and
`66d645d626d9714fb4a33594e4de94ded4b9991fb563185809b6ff1f02142d64` (Lab EA archive).
Set `ISAAC_SIM_SHA256` or `ISAACLAB_SHA256` only when intentionally testing a different official
build. Task assets are fetched on first build; use `python -m robobench.scripts.fetch_assets` inside
the container to prefetch all of them.

Task assets and shared rooms live in the Hugging Face dataset `EmbodiedSWE/robobench-assets`.
Building an environment automatically downloads its required asset groups and verifies their SHA-256
checksums against `robobench/assets_manifest.json`. Verified local copies are reused, including offline.
Listing tasks does not download anything. `fetch_assets --check` verifies the whole local collection.

Every built-in registered task configuration declares its default room in its suite's
`configs/envs.py`, including alternate robots and control modes. Shared loading code lives in
`robobench/core/rooms.py`; downloaded rooms live in the ignored `robobench/assets/rooms/` directory.
Use `--room none` with the smoke launcher or `cfg.build(room=None)` to disable scenery explicitly.
Set `COSIGEN_ASSET_DIR` before starting Python to use a writable cache outside the checkout.
See [task rooms and asset downloads](docs/rooms.md) for the room assignments and maintainer commands.

The `deformable` suite runs on the Newton physics backend and needs a separate venv; see
[`robobench/suites/deformable/README.md`](robobench/suites/deformable/README.md).

## Quick start

Preview a task:

```bash
python -m robobench.scripts.smoke --list                                          # all registered tasks
python -m robobench.scripts.smoke --env assembly.bulb.franka.osc --livestream 2   # random actions, live view
```

Tasks are named `suite.scene[.robot[.control_mode]]`. The environment API and design are described
in [`robobench/README.md`](robobench/README.md).

### Isaac Sim 6.1 / Isaac Lab 3 migration status

The defensible migrated vertical slice is `assembly.bulb.franka.osc`: the real Franka articulation
resets, the OSC controller writes effort and advances physics, native XYZW simulator state snapshots
round-trip, and `BulbAssemblyGrader` records/verdicts correctly. Run
`robobench.suites.assembly.smokes.bulb_franka_osc_smoke` using the command printed by the bootstrap.
The grader is privileged-state based and does **not** consume camera pixels; the task still declares
`front` and Franka `wrist` cameras for observation/data-generation pipelines.

The real environment-builder boot check and grading entrypoint use Lab 3's non-headless Kit
visualizer experience, even on a displayless compute node. The EA headless experience omits viewport
extensions required by this visualizer and can feed `ProxyArray` wrappers to Warp COM-pose kernels.
The builder's validation subprocess also retains the container-injected `LD_LIBRARY_PATH` so NVIDIA
libraries remain discoverable without modifying the image's global loader cache.

A separate `assembly.nut_thread` scene-physics smoke has also passed. These results do not validate
every registered task or embodiment. In particular, the remaining assembly variants, packing,
puzzle, cutting, locomanip, deformable/Newton, multi-environment batches, non-Franka robots,
`diff_ik`/`pink_ik`/joint modes, camera recording, and policy/data-generation pipelines have not been
runtime-qualified on Sim 6.1/Lab 3 EA. Their config quaternions and raw PhysX array/write boundaries
must be audited at each external-WXYZ/native-XYZW interface before claiming support.

**A few examples from EmbodiedSWE-Bench:**

<table align="center">
  <tr>
    <td align="center"><img src="docs/media/bulb.gif" width="100%"><br><sub><code>assembly.bulb</code></sub></td>
    <td align="center"><img src="docs/media/ikea_table.gif" width="100%"><br><sub><code>assembly.ikea_table</code></sub></td>
    <td align="center"><img src="docs/media/so101.gif" width="100%"><br><sub><code>assembly.so101</code></sub></td>
    <td align="center"><img src="docs/media/pc_motherboard.gif" width="100%"><br><sub><code>assembly.pc_motherboard</code></sub></td>
    <td align="center"><img src="docs/media/tool_packing.gif" width="100%"><br><sub><code>packing.tool_packing</code></sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/media/egg_carton.gif" width="100%"><br><sub><code>packing.egg_carton</code></sub></td>
    <td align="center"><img src="docs/media/tshirt.gif" width="100%"><br><sub><code>deformable.tshirt</code></sub></td>
    <td align="center"><img src="docs/media/latte.gif" width="100%"><br><sub><code>deformable.latte</code></sub></td>
    <td align="center"><img src="docs/media/slice_banana.gif" width="100%"><br><sub><code>cutting.slice</code></sub></td>
    <td align="center"><img src="docs/media/fruit_delivery.gif" width="100%"><br><sub><code>locomanip.fruit_delivery</code></sub></td>
  </tr>
</table>

## Solving a task

The easy way: open the repo in a coding agent such as Claude Code or Codex, point it at
`robobench/README.md`, and ask it to solve a task, e.g. `assembly.bulb.franka.osc`. A solution is a
Python program exposing `solve(env)`; the contract the agents see is
[`eval/prompts/_contract.md`](eval/prompts/_contract.md).

For rigorous, large-scale evaluation, `eval/` runs the agent in an isolated Docker container under a
time budget and grades its solutions afterwards in fresh containers on independently randomized episodes.

```bash
python eval/scripts/build_env.py --name bulb_e2e --stage bulb:franka    # build the world once
python eval/scripts/run_agent.py experiments/bulb_e2e --agent claude    # one agent run in Docker
python eval/scripts/run_grade.py experiments/bulb_e2e --run <run>       # grade the delivery
```

Prompt conditions (hints, rules, blocked features) are authored yaml files in `eval/configs/` and
`eval/prompts/`. Docker images and the container contract are documented in
[`eval/docker/README.md`](eval/docker/README.md).

## Data engine

Once a task is solved, `data_engine/` turns that one verified solution into a large, diverse,
per-episode-verified demonstration dataset. Coding agents author the diversity at five independent
levels: scene, strategy, phase, dynamics, and visual.

A generic launcher then mass-produces batched episodes, the scene's grader stamps a verdict on each
one, and the verified episodes are rendered and baked into a LeRobot dataset for policy training.

```bash
python data_engine/scripts/init_gen.py experiments/bulb_e2e/runs/<run>                  # start a campaign from a solved run
python data_engine/scripts/diversify.py <gen_root> data_engine/configs/scene_default.yaml # agent session that adds diversity
python data_engine/scripts/generate.py --headless <gen_root> --scene scene_1 --num_envs 8 # generate + verify a batch
python data_engine/scripts/render.py --headless <gen_root> --batches <batch>              # render episodes to video
.venv-lerobot/bin/python vla/convert/convert.py <gen_root> --repo-id <name>               # bake a LeRobot dataset
```

Training and closed-loop evaluation of VLA policies live in [`vla/`](vla/README.md).

## Repository layout

```
robobench/            EmbodiedSWE-Bench: the benchmark package
  core/               BaseEnv, BaseScene, BaseRobot, controller and grader contracts, registries
  suites/             task suites: assembly, packing, puzzle, deformable, cutting, locomanip
  robots/             embodiments: franka, xarm7, attached (Kinova Gen3 + panda hand), g1, multi (bimanual), ...
  controllers/        joint, diff_ik, task_space (OSC / impedance), pink_ik, composite, loco_policy
  scripts/smoke.py    build and step any registered env
eval/                 dockerized agent evaluation
data_engine/          EmbodiedSWE-Gen: expands one solution into diverse trajectories
vla/                  bake episodes into LeRobot datasets, train and evaluate VLA policies
rl/                   RL baselines (not agent improvement)
sim_gen/              generates new simulation tasks from seed tasks (agent improvement)
real_to_sim/          real scenes and objects to sim: splat backgrounds, photos to sim-ready assets
scripts/              bootstrap installers, record_video.py, asset vendoring
```

## Citation

If you use EmbodiedSWE in your research, please cite our [paper](https://arxiv.org/abs/2609.27308):

```bibtex
@misc{embodiedswe2026,
  title         = {EmbodiedSWE: Coding Agents for Long Horizon Dexterous Robotics},
  author        = {Shen, Zeyu and You, Haoxiang and Liu, Yilang and Zheng, Zhicheng and Zha, Lihan and
                   Yamazaki, Kashu and Zhang, Mingtong and Huang, Suning and Sun, Jiankai and
                   Chen, Qianzhong and He, Lucy and Liu, Kaiyuan and Chang, Haoran and Fragkiadaki, Katerina and
                   Shah, Dhruv and Schwager, Mac and Henderson, Peter and Abraham, Ian and Xu, Canwen},
  year          = {2026},
  eprint        = {2609.27308},
  archivePrefix = {arXiv},
  primaryClass  = {cs.RO},
  url           = {https://arxiv.org/abs/2609.27308},
}
```

## License

Apache 2.0. See [LICENSE](LICENSE).

Built on [Isaac Lab](https://github.com/isaac-sim/IsaacLab), [Newton](https://github.com/newton-physics/newton),
and [LeRobot](https://github.com/huggingface/lerobot).
