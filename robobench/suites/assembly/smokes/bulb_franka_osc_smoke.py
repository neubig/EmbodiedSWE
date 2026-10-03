"""Real Isaac Lab integration smoke for ``assembly.bulb.franka.osc``.

Exercises the registered task with a Franka articulation and OSC controller: reset, non-zero
controller action and physics, full scene/robot/controller snapshot restore, and the native bulb
grader. The final grader-positive placement is deliberate privileged test setup; it validates the
grader boundary, not a claim that the short OSC motion solves bulb assembly.
"""

from __future__ import annotations

import argparse
import os
import threading
import traceback

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(parser)
parser.add_argument("--no-render", action="store_true")
args = parser.parse_args()
app = AppLauncher(args).app

import torch  # noqa: E402

import robobench  # noqa: E402
from robobench.core import ENVS, GradedEnv  # noqa: E402
from robobench.core.compat import write_root_state_native  # noqa: E402
from robobench.suites.assembly.grader.bulb_assembly import (  # noqa: E402
    BulbAssemblyGrader,
)


def _close(env, code: int) -> None:
    watchdog = threading.Timer(10.0, lambda: os._exit(code))
    watchdog.daemon = True
    watchdog.start()
    if env is not None:
        env.close()
    os._exit(code)


def main() -> None:
    robobench.discover()
    env = ENVS.get("assembly.bulb.franka.osc")().build(num_envs=1, device="cuda:0", seed=7)
    try:
        ids = torch.arange(env.num_envs, device=env.device)
        art = env.robot.articulation
        scene = env.scene
        env.reset(seed=7)

        assert env.robot.action_dim == 8
        assert not scene.seated().any(), "reset unexpectedly satisfies bulb goal"
        root_quat = art.data.root_quat_w.torch[0]
        torch.testing.assert_close(root_quat, torch.tensor([0.0, 0.0, 0.0, 1.0], device=env.device))

        ee_idx = art.body_names.index(env.robot.EE_BODY)
        grip_ids = env.robot.controller.controllers[-1].joint_ids
        grips = art.data.joint_pos.torch[:, grip_ids].clone()
        hold = torch.cat((torch.zeros(1, 6, device=env.device), grips), dim=1)
        ee_before = art.data.body_pos_w.torch[:, ee_idx].clone()

        grader = BulbAssemblyGrader(env)
        graded = GradedEnv(env, grader)
        graded.step(hold, render=not args.no_render)
        move = hold.clone()
        move[:, 2] = 0.5
        for _ in range(10):
            graded.step(move, render=not args.no_render)

        ee_after = art.data.body_pos_w.torch[:, ee_idx].clone()
        displacement = float((ee_after - ee_before).norm())
        effort = float(art.data.joint_effort_target.torch[:, :7].abs().max())
        assert torch.isfinite(art.data.joint_pos.torch).all()
        assert 0.002 < displacement < 0.30, f"OSC did not produce bounded motion: {displacement}"
        assert effort > 0.1, f"OSC did not write arm effort: {effort}"

        snapshot = env.get_states()
        for _ in range(4):
            graded.step(hold, render=False)
        assert float((art.data.joint_pos.torch - snapshot["robot"]["joint_pos"]).abs().max()) > 1e-6
        env.set_states(snapshot)
        restored = env.get_states()
        torch.testing.assert_close(restored["scene"]["bulbs"], snapshot["scene"]["bulbs"])
        torch.testing.assert_close(restored["robot"]["root"], snapshot["robot"]["root"])
        torch.testing.assert_close(restored["robot"]["joint_pos"], snapshot["robot"]["joint_pos"])
        torch.testing.assert_close(
            restored["robot"]["controller"]["0"]["prev_action"],
            snapshot["robot"]["controller"]["0"]["prev_action"],
        )

        socket_pos = scene.sockets[0].data.root_pos_w.torch.clone()
        seated_state = torch.zeros(env.num_envs, 13, device=env.device)
        seated_state[:, :3] = socket_pos
        seated_state[:, 2] += scene.cfg.seat_z - 0.002
        seated_state[:, 6] = 1.0  # native Lab 3 XYZW identity
        write_root_state_native(scene.bulbs[0], seated_state, ids)
        assert scene.seated().all()
        graded.step(hold, render=False)
        verdict = grader.verdict()
        assert verdict[0]["success"] and verdict[0]["score"] == 1.0, verdict

        env.reset(seed=7)
        assert not scene.seated().any(), "reset did not restore the unassembled task"
        print(
            "BULB_FRANKA_OSC_SMOKE_PASS "
            f"ee_displacement_m={displacement:.6f} max_effort_nm={effort:.3f} "
            f"snapshot=roundtrip grader={verdict} "
            f"scene_cameras={sorted(scene.CAMERAS)} robot_cameras={sorted(env.robot.CAMERAS)} "
            "grader_camera_required=false",
            flush=True,
        )
    except BaseException:
        traceback.print_exc()
        _close(env, 1)
    _close(env, 0)


if __name__ == "__main__":
    main()
