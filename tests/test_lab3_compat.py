import unittest

import torch
import warp as wp
from robobench.core.compat import (
    quat_wxyz_to_xyzw,
    quat_xyzw_to_wxyz,
    torch_data,
    write_joint_state_native,
    write_root_state_native,
)


class RecordingAsset:
    def __init__(self):
        self.calls = []

    def write_root_link_pose_to_sim_index(self, **kwargs):
        self.calls.append(("root_pose", kwargs))

    def write_root_com_velocity_to_sim_index(self, **kwargs):
        self.calls.append(("root_velocity", kwargs))

    def write_joint_position_to_sim_index(self, **kwargs):
        self.calls.append(("joint_position", kwargs))

    def write_joint_velocity_to_sim_index(self, **kwargs):
        self.calls.append(("joint_velocity", kwargs))


class Lab3CompatibilityTests(unittest.TestCase):
    def test_quaternion_boundary_round_trip_is_batched(self):
        benchmark = torch.tensor([[1., 2., 3., 4.], [5., 6., 7., 8.]])
        lab = quat_wxyz_to_xyzw(benchmark)
        torch.testing.assert_close(lab, torch.tensor([[2., 3., 4., 1.], [6., 7., 8., 5.]]))
        torch.testing.assert_close(quat_xyzw_to_wxyz(lab), benchmark)

    def test_config_quaternion(self):
        benchmark = (1., 2., 3., 4.)
        native = quat_wxyz_to_xyzw(benchmark)
        self.assertEqual(native, (2., 3., 4., 1.))
        self.assertEqual(quat_xyzw_to_wxyz(native), benchmark)

    def test_torch_data_preserves_tensor(self):
        value = torch.zeros(2, 4)
        self.assertIs(torch_data(value), value)

    def test_warp_material_view_is_writable(self):
        material = wp.array([[[0.5, 0.4, 0.1]]], dtype=wp.float32, device="cpu")
        wp.to_torch(material)[..., :2] = 0.2
        torch.testing.assert_close(wp.to_torch(material), torch.tensor([[[0.2, 0.2, 0.1]]]))

    def test_native_writes_split_state_without_reordering(self):
        asset = RecordingAsset()
        state = torch.arange(26, dtype=torch.float32).reshape(2, 13)
        position = torch.ones(2, 3)
        velocity = torch.zeros(2, 3)
        env_ids = torch.tensor([1, 3])

        write_root_state_native(asset, state, env_ids)
        write_joint_state_native(asset, position, velocity, env_ids)

        self.assertEqual(
            [name for name, _ in asset.calls],
            ["root_pose", "root_velocity", "joint_position", "joint_velocity"],
        )
        torch.testing.assert_close(asset.calls[0][1]["root_pose"], state[:, :7])
        torch.testing.assert_close(asset.calls[1][1]["root_velocity"], state[:, 7:13])
        self.assertIs(asset.calls[2][1]["position"], position)
        self.assertIs(asset.calls[3][1]["velocity"], velocity)
        self.assertIs(asset.calls[0][1]["env_ids"], env_ids)


if __name__ == '__main__':
    unittest.main()
