"""Public research state access on a live Arena environment."""


def as_torch(value):
    import torch
    import warp as wp

    if isinstance(value, torch.Tensor):
        return value
    if isinstance(value, wp.array):
        return wp.to_torch(value)
    return value.torch


class ResearchState:
    def __init__(self, env, robot_configuration):
        self.env = env.unwrapped
        self.robot = self.env.scene["robot"]
        self.object = self.env.scene["object"]
        self.configuration = robot_configuration

    def joint_state(self):
        """Return physical joint names, positions [rad] and velocities [rad/s]."""
        return {
            "names": list(self.robot.joint_names),
            "positions": as_torch(self.robot.data.joint_pos),
            "velocities": as_torch(self.robot.data.joint_vel),
        }

    def palm_pose(self):
        """Return T_W_H as [x,y,z,qx,qy,qz,qw], where H is configured palm_frame."""
        palm_name = self.configuration["palm_frame"]
        if palm_name not in self.robot.body_names:
            raise ValueError(f"Palm body {palm_name!r} was not loaded")
        return as_torch(self.robot.data.body_pose_w)[:, self.robot.body_names.index(palm_name)]

    def object_pose(self):
        """Return T_W_O as [x,y,z,qx,qy,qz,qw]."""
        return as_torch(self.object.data.root_pose_w)

    def contacts(self):
        """Return measured object-to-robot normal force and average contact positions.

        Contact positions are aggregate averages per filter body, not a full
        contact manifold. No-contact positions can be NaN and are masked out.
        """
        import torch

        data = self.env.scene.sensors["dexlab_object_contact"].data
        forces = as_torch(data.normal_force_matrix_w)
        points = as_torch(data.contact_pos_w)
        if not torch.isfinite(forces).all().item():
            raise RuntimeError("Contact sensor produced non-finite forces")
        active = torch.linalg.vector_norm(forces, dim=-1) > 1e-6
        if (active & ~torch.isfinite(points).all(dim=-1)).any().item():
            raise RuntimeError("Active contact has no finite measured average position")
        valid = active & torch.isfinite(points).all(dim=-1)
        return {
            "normal_forces_W": forces,
            "average_points_W": points,
            "valid_points": valid,
            "active_contacts": active,
            "scope": "object versus configured fingertip bodies",
        }

    def snapshot(self, step):
        joints = self.joint_state()
        contacts = self.contacts()
        points_by_environment = []
        for points, valid in zip(contacts["average_points_W"], contacts["valid_points"], strict=True):
            points_by_environment.append(points[valid].detach().cpu().tolist())
        return {
            "step": step, "frame": "W", "quaternion_order": "xyzw", "length_unit": "m", "joint_unit": "rad",
            "joint_names": joints["names"], "joint_positions": joints["positions"].detach().cpu().tolist(),
            "joint_velocities": joints["velocities"].detach().cpu().tolist(),
            "hand_root_frame": self.configuration["palm_frame"],
            "hand_root_pose": self.palm_pose().detach().cpu().tolist(),
            "robot_base_pose": as_torch(self.robot.data.root_pose_w).detach().cpu().tolist(),
            "object_pose": self.object_pose().detach().cpu().tolist(),
            "contact_points": points_by_environment,
            "contact_normal_forces_W": contacts["normal_forces_W"].detach().cpu().tolist(),
            "contact_filter_body_names": self.configuration["fingertip_names"],
            "contact_points_semantics": "average position per filtered body, not full manifold",
            "contact_scope": contacts["scope"], "collision": None, "stability": None, "success": None,
        }
