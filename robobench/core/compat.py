"""Small pure helpers for Isaac Lab 3 compatibility boundaries."""

from __future__ import annotations

from typing import Any


def quat_wxyz_to_xyzw(quat: Any) -> Any:
    """Reorder benchmark/API quaternions for Isaac Lab 3 tensor APIs."""
    if isinstance(quat, (tuple, list)):
        return tuple(quat[i] for i in (1, 2, 3, 0))
    return quat[..., (1, 2, 3, 0)]


def quat_xyzw_to_wxyz(quat: Any) -> Any:
    """Reorder Isaac Lab 3 quaternions to the benchmark/API WXYZ contract."""
    if isinstance(quat, (tuple, list)):
        return tuple(quat[i] for i in (3, 0, 1, 2))
    return quat[..., (3, 0, 1, 2)]


def torch_data(value: Any) -> Any:
    """Return a Lab 3 ProxyArray's explicit torch view, preserving older tensors."""
    return getattr(value, "torch", value)


def write_root_pose_native(asset: Any, pose: Any, env_ids: Any) -> None:
    """Write a partial native XYZW root-link pose with Lab 3's indexed API."""
    asset.write_root_link_pose_to_sim_index(root_pose=pose, env_ids=env_ids)


def write_root_state_native(asset: Any, state: Any, env_ids: Any) -> None:
    """Write native root-link pose plus COM velocity with Lab 3 indexed APIs."""
    write_root_pose_native(asset, state[..., :7], env_ids)
    asset.write_root_com_velocity_to_sim_index(root_velocity=state[..., 7:13], env_ids=env_ids)


def write_joint_state_native(asset: Any, position: Any, velocity: Any, env_ids: Any) -> None:
    """Write partial joint position and velocity with Lab 3's indexed APIs."""
    asset.write_joint_position_to_sim_index(position=position, env_ids=env_ids)
    asset.write_joint_velocity_to_sim_index(velocity=velocity, env_ids=env_ids)

